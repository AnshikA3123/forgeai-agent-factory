"""Stage 6 critic-optimizer: classify failures, apply one targeted fix per category, re-run. Max 3 iterations."""
import copy
import re

from .generator import build_system_prompt
from .judge import run_evals
from .agent import Agent
from .text import tokens, chunk_docs, BM25

RULES = {
    "hallucination": "State only facts that appear verbatim in the context; copy figures exactly and add nothing else.",
    "prompt_defect": "Answer EVERY part of the question in complete sentences, stating the exact figure, limit or condition from the context, with a [source-id] citation after each part.",
}


def apply_fixes(defn, failures, agent, req, cases_by_id):
    """Returns (new_definition, change_log)."""
    d = copy.deepcopy(defn)
    log = []
    cats = {}
    for f in failures:
        cats.setdefault(f["failure"], []).append(f)
    r = d["retrieval"]
    if "retrieval_miss" in cats:
        ids = [f["id"] for f in cats["retrieval_miss"]]
        added = {}
        for f in cats["retrieval_miss"]:
            c = cases_by_id[f["id"]]
            exp = [ch for ch in agent.chunks if ch["id"] in (c["source_chunk"] if isinstance(c["source_chunk"], list) else [c["source_chunk"]])]
            exp_toks = set(t for ch in exp for t in tokens(ch["heading"] + " " + ch["text"]))
            head_toks = [t for ch in exp for t in tokens(ch["heading"])]
            for qt in tokens(c["question"]):
                if qt not in exp_toks and qt not in agent.index.vocab - set() and head_toks:
                    added.setdefault(qt, head_toks[:3])
                elif qt not in exp_toks and head_toks and agent.index.df.get(qt, 0) <= 1:
                    added.setdefault(qt, head_toks[:3])
        if added:
            r["expansions"].update(added)
            log.append({"category": "retrieval_miss", "fix": f"added {len(added)} query expansions (question words absent from the expected chunk -> its heading words)",
                        "detail": added, "addresses": ids})
        if r["top_k"] < 4:
            r["top_k"] += 1
            log.append({"category": "retrieval_miss", "fix": f"top_k -> {r['top_k']}", "addresses": ids})
    if "wrong_refusal" in cats:
        r["min_coverage"] = round(max(0.2, r["min_coverage"] - 0.15), 2)
        r["min_score"] = round(max(0.3, r["min_score"] - 0.4), 2)
        log.append({"category": "wrong_refusal", "fix": f"min_coverage -> {r['min_coverage']}, min_score -> {r['min_score']}",
                    "addresses": [f["id"] for f in cats["wrong_refusal"]]})
    if "hallucination" in cats:
        oos = [f for f in cats["hallucination"] if cases_by_id[f["id"]]["should_refuse"]]
        ung = [f for f in cats["hallucination"] if not cases_by_id[f["id"]]["should_refuse"]]
        if oos:
            r["min_coverage"] = round(min(0.95, r["min_coverage"] + 0.1), 2)
            r["min_score"] = round(r["min_score"] + 0.5, 2)
            log.append({"category": "hallucination", "fix": f"stricter refusal gate: min_coverage -> {r['min_coverage']}, min_score -> {r['min_score']}",
                        "addresses": [f["id"] for f in oos]})
        if ung and RULES["hallucination"] not in d["prompt_rules"]:
            d["prompt_rules"].append(RULES["hallucination"])
            d["output_contract"]["extractive_fallback"] = True
            log.append({"category": "hallucination", "fix": "added grounding rule to system prompt + extractive fallback when the answer drifts from context", "addresses": [f["id"] for f in ung]})
    if "prompt_defect" in cats and RULES["prompt_defect"] not in d["prompt_rules"]:
        d["prompt_rules"].append(RULES["prompt_defect"])
        d["output_contract"]["max_sentences"] = d["output_contract"]["max_sentences"] + 1
        d["output_contract"]["max_tokens"] += 60
        d["output_contract"]["extractive_fallback"] = True
        log.append({"category": "prompt_defect", "fix": "added answer-focus rule; max_sentences/max_tokens raised",
                    "addresses": [f["id"] for f in cats["prompt_defect"]]})
    d["system_prompt"] = build_system_prompt(req, d["prompt_rules"])
    return d, log


def optimize(defn, docs_dir, cases, req, llm, max_iter=3, on_iter=None):
    cases_by_id = {c["id"]: c for c in cases}
    history = []
    agent = Agent(defn, docs_dir, llm)
    score = run_evals(agent, cases, llm)
    history.append({"iteration": 0, "score": score["pass_rate"], "passed": score["passed"], "total": score["total"],
                    "by_type": score["by_type"], "changes": [], "results": score["results"], "definition": copy.deepcopy(defn)})
    if on_iter:
        on_iter(history[-1])
    best = history[0]
    for it in range(1, max_iter + 1):
        failures = [x for x in best["results"] if not x["pass"]]
        if not failures:
            break
        cats = sorted({f["failure"] for f in failures})
        start = best
        attempts, accepted_changes, log_all = [], [], []
        for cat in cats:
            cur_fail = [x for x in best["results"] if not x["pass"] and x["failure"] == cat]
            if not cur_fail:
                continue
            new_def, log = apply_fixes(best["definition"], cur_fail, Agent(best["definition"], docs_dir, llm), req, cases_by_id)
            if not log:
                continue
            s = run_evals(Agent(new_def, docs_dir, llm), cases, llm)
            ok = s["pass_rate"] > best["score"]
            attempts.append({"category": cat, "score_before": best["score"], "score_after": s["pass_rate"], "kept": ok, "changes": log})
            if ok:
                best = {"score": s["pass_rate"], "passed": s["passed"], "total": s["total"], "by_type": s["by_type"],
                        "results": s["results"], "definition": new_def}
                accepted_changes += log
        rec = {"iteration": it, "score_before": start["score"], "score": best["score"], "passed": best["passed"],
               "total": best["total"], "by_type": best["by_type"], "changes": accepted_changes, "attempts": attempts,
               "results": best["results"], "definition": best["definition"],
               "failures_before": [{"id": f["id"], "category": f["failure"]} for f in failures],
               "accepted": bool(accepted_changes)}
        history.append(rec)
        if on_iter:
            on_iter(rec)
        if not accepted_changes:
            break
    return history, best
