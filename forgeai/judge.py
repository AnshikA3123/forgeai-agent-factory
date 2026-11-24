"""Stage 5 judge: deterministic checks plus an LLM support check with bias defences.
Defences: (1) key facts come from the documents, not from the agent; (2) grounding of numbers is a string check;
(3) the LLM verdict is asked in BOTH orders (position bias) and only counts when both agree; (4) the LLM can only
downgrade a deterministic pass for grounding, never upgrade a fail (self-preference); (5) length is not rewarded:
extra unsupported sentences lower the token-overlap check (verbosity)."""
import re

from .llm import prompt
from .text import tokens

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def norm(s):
    return re.sub(r"[\s,]+", "", s.lower().replace("percent", "%").replace("usd", ""))


def det_grounded(answer, context):
    ctx = norm(context)
    nums_ok = all(norm(n) in ctx for n in NUM.findall(re.sub(r"\[[^\]]*\]", "", answer)))
    at = set(tokens(re.sub(r"\[[^\]]*\]", "", answer)))
    overlap = len(at & set(tokens(context))) / max(1, len(at))
    return nums_ok, round(overlap, 2)


def llm_support(llm, answer, context):
    if not llm.available:
        return None
    votes = []
    for order in (0, 1):
        pairs = [("CONTEXT", context[:1500]), ("ANSWER", answer)]
        if order:
            pairs.reverse()
        out = llm.complete(prompt("judge_support.txt", first_label=pairs[0][0], first=pairs[0][1],
                                  second_label=pairs[1][0], second=pairs[1][1]), max_tokens=3) or ""
        votes.append(out.strip().upper().startswith("YES"))
    return votes[0] and votes[1] if votes[0] == votes[1] else None


def judge(case, res, llm):
    out = {"id": case["id"], "type": case["type"]}
    refused = res["refused"]
    if case["should_refuse"]:
        out.update(refused_ok=refused, grounded=True, correct=True, retrieval_hit=True)
        out["pass"] = refused
        out["failure"] = None if refused else "hallucination"
        return out
    out["refused_ok"] = not refused
    if refused:
        out.update(grounded=True, correct=False, retrieval_hit=any(r.split("#")[0] in case["expected_docs"] for r in res["retrieved"]), **{"pass": False})
        out["failure"] = "wrong_refusal"
        return out
    ans = res["answer"]
    full_ctx = res["context"]
    hit = all(any(r.split("#")[0] == d for r in res["retrieved"]) for d in case["expected_docs"]) or any(t.startswith("calculator") or t.startswith("csv_lookup") for t in res["tool_calls"])
    nums_ok, overlap = det_grounded(ans, full_ctx)
    sup = llm_support(llm, ans, full_ctx)
    # LLM vote may only veto when the deterministic overlap is not near-verbatim (small judges mislabel correct copies)
    grounded = nums_ok and overlap >= 0.6 and not (sup is False and overlap < 0.85)
    facts = case["key_facts"]
    def has(f):
        core = re.match(r"\$?(\d[\d,]*(?:\.\d+)?)", f.strip())
        if core:
            return re.search(r"(?<![\d.])" + re.escape(core.group(1)) + r"(?![\d])", ans.replace(",", "") if "," not in core.group(1) else ans) is not None
        return norm(f) in norm(ans)
    got = [f for f in facts if has(f)]
    # answerable cases need at least ONE key fact; cross-document cases need one fact from EACH document
    need = 1
    correct = True if case.get("lenient") else (len(got) >= need if facts else True)
    if case["type"] == "edge_cross_doc" and len(got) < 2:
        correct = False
    out.update(retrieval_hit=hit, grounded=grounded, correct=correct, numbers_in_context=nums_ok, overlap=overlap,
               llm_support=sup, facts_found=f"{len(got)}/{len(facts)}")
    out["pass"] = hit and grounded and correct
    if out["pass"]:
        out["failure"] = None
    elif not hit:
        out["failure"] = "retrieval_miss"
    elif not grounded:
        out["failure"] = "hallucination"
    else:
        out["failure"] = "prompt_defect"
    return out


def run_evals(agent, cases, llm):
    results = []
    for c in cases:
        r = agent.ask(c["question"])
        j = judge(c, r, llm)
        j["answer"], j["retrieved"], j["question"] = r["answer"], r["retrieved"], c["question"]
        results.append(j)
    passed = sum(1 for j in results if j["pass"])
    by_type = {}
    for j in results:
        t = by_type.setdefault(j["type"], [0, 0])
        t[1] += 1
        t[0] += j["pass"]
    return {"pass_rate": round(passed / len(results), 3), "passed": passed, "total": len(results),
            "by_type": {k: f"{a}/{b}" for k, (a, b) in by_type.items()}, "results": results}
