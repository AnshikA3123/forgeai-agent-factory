"""Stage 6 critic-optimizer: classify failures, apply one targeted fix per category, re-run. Max 3 iterations."""
import copy
import re

from .generator import build_system_prompt
from .llm import prompt, ask_json
from .judge import run_evals
from .agent import Agent
from .text import tokens, chunk_docs, BM25

RULES = {
    "hallucination": "State only facts that appear verbatim in the context; copy figures exactly and add nothing else.",
    "prompt_defect": "Answer EVERY part of the question in complete sentences, stating the exact figure, limit or condition from the context, with a [source-id] citation after each part.",
}


CATS = ("retrieval_miss", "prompt_defect", "hallucination", "wrong_refusal")


def generic_rule_problem(rule, case):
    """v3: a prompt rule must be a reusable instruction, not a description of one eval case. Returns a reason string or None."""
    if rule.strip().lower().startswith("always state the exact number of days"):
        return "copy of the v3a prompt example"
    if re.search(r"\d", rule):
        return "contains a digit (case-specific figure)"
    if '"' in rule or "'" in rule:
        return "contains a quoted phrase"
    if re.search(r"\bshould have\b|\bthe assistant should\b|\bretrieval hit\b|\bthe answer should\b|\bfailed to\b|\bthe assistant (?:failed|did not)\b", rule, re.I):
        return "describes a failure instead of instructing"
    if re.match(r"\s*(?:the|this)\s+(?:assistant|answer|model|agent|response|system|retrieved|documents?)\b", rule, re.I) or re.search(r"\b(?:test question|scenario|was not|were not|did not|not relevant)\b", rule, re.I):
        return "narrates what happened in an eval case instead of instructing (v4)"
    facts = {t for f in case.get("key_facts", []) for t in tokens(f) if len(t) >= 4}
    q = {t for t in tokens(case.get("question", "")) if len(t) >= 5}
    leak = [t for t in tokens(rule) if t in facts or t in q]
    if leak:
        return "mentions eval-case words: " + ", ".join(sorted(set(leak))[:4])
    return None


def diagnose(llm, case, res, rule_cat, result_row):
    """Model diagnoses one failure. Returns (category, rule_text, source). The deterministic judge verdict is shown as evidence;
    if the model output is invalid the rule-based category is used and labelled as such."""
    def val(o):
        if o.get("category") not in CATS:
            raise ValueError("category not in menu")
        r = o.get("rule")
        if not isinstance(r, str) or not 15 <= len(r) <= 250:
            raise ValueError("rule must be 15-250 chars")
        why = generic_rule_problem(r, case)
        if why:
            raise ValueError("rule is not reusable: " + why)
        return o
    o = ask_json(llm, "optimizer_diagnose", prompt("optimizer_diagnose.txt", question=case["question"], expected=", ".join(case["expected_docs"]) or "none (should refuse)",
                 facts="; ".join(case["key_facts"]) or "n/a", should_refuse=case["should_refuse"], retrieved=", ".join(result_row["retrieved"]) or "none",
                 answer=result_row["answer"][:200], verdict=f"refused_ok={result_row.get('refused_ok')}, retrieval_hit={result_row.get('retrieval_hit')}, grounded={result_row.get('grounded')}, correct={result_row.get('correct')}"), val, 140)
    if o:
        return o["category"], o["rule"], "model"
    return rule_cat, None, "rule-fallback (model diagnosis invalid)"


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
        hr = next((f.get("model_rule") for f in ung if f.get("model_rule")), None)
        if ung and (hr or RULES["hallucination"]) not in d["prompt_rules"]:
            d["prompt_rules"].append(hr or RULES["hallucination"])
            d["output_contract"]["extractive_fallback"] = True
            log.append({"category": "hallucination", "fix": "added grounding rule to system prompt (%s) + extractive fallback when the answer drifts from context" % ("model-written" if hr else "fixed template"), "addresses": [f["id"] for f in ung]})
    pr = next((f.get("model_rule") for f in cats.get("prompt_defect", []) if f.get("model_rule")), None)
    if "prompt_defect" in cats and (pr or RULES["prompt_defect"]) not in d["prompt_rules"]:
        d["prompt_rules"].append(pr or RULES["prompt_defect"])
        d["output_contract"]["max_sentences"] = d["output_contract"]["max_sentences"] + 1
        d["output_contract"]["max_tokens"] += 60
        d["output_contract"]["extractive_fallback"] = True
        log.append({"category": "prompt_defect", "fix": "added answer-focus rule (%s); max_sentences/max_tokens raised" % ("model-written" if pr else "fixed template"),
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
        failures = [dict(x) for x in best["results"] if not x["pass"]]
        if not failures:
            break
        for f in failures:  # model diagnosis replaces the rule category; the rule category is kept for cross-checking
            case = cases_by_id[f["id"]]
            f["rule_category"] = f["failure"]
            cat, rule, src = diagnose(llm, case, None, f["failure"], f)
            f["failure"], f["model_rule"], f["diagnosis_source"] = cat, rule, src
        cats = sorted({f["failure"] for f in failures})
        start = best
        attempts, accepted_changes, log_all = [], [], []
        for cat in cats:
            cur_fail = [f for f in failures if f["failure"] == cat and any(x["id"] == f["id"] and not x["pass"] for x in best["results"])]
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
               "failures_before": [{"id": f["id"], "category": f["failure"], "rule_category": f["rule_category"], "diagnosis_source": f["diagnosis_source"], "model_rule": f["model_rule"]} for f in failures],
               "accepted": bool(accepted_changes)}
        history.append(rec)
        if on_iter:
            on_iter(rec)
        if not accepted_changes:
            break
    return history, best
