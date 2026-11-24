"""Stage 7 honest reporting."""
import json
from collections import Counter


def write_report(out, req, initial, cases, history, best, meta):
    L = [f"# ForgeAI run report", "", f"Brief: {req['brief']}", "",
         f"Model: `{meta['model']}` | {meta['llm_calls']} model calls | {meta['seconds']}s wall time", "",
         "## Requirements and groundability", ""]
    L += [f"- Scope: {req['scope']}", f"- Audience: {req['audience']}", f"- Tone: {req['tone']}",
          f"- Must answer: {', '.join(req['must_answer_topics'])}", f"- Must refuse: {', '.join(req['must_refuse_topics'])}"]
    L += [f"- WARNING: {w}" for w in req["warnings"]]
    L += ["", "Interview (max 5 questions):"] + [f"- {i['q']} -> {i['a']} ({i['source']})" for i in req["interview"]]
    L += ["", "## Agent definition", "", f"- Tools attached: {', '.join(best['definition']['tools']) or 'none'}",
          f"- Tools deliberately not attached: {', '.join(best['definition']['tools_not_attached'])}",
          f"- Retrieval: `{json.dumps({k: v for k, v in best['definition']['retrieval'].items() if k != 'expansions'})}`, "
          f"{len(best['definition']['retrieval']['expansions'])} query expansions"]
    L += ["", "## Scorecard (pass = right docs retrieved, grounded, key facts present, or correct refusal)", "",
          "| Iteration | Pass rate | Passed | By case type | Accepted |", "|---|---|---|---|---|"]
    for h in history:
        L.append(f"| {h['iteration']} | {h['score']:.0%} | {h['passed']}/{h['total']} | {h['by_type']} | {h.get('accepted', 'baseline')} |")
    L += ["", "## Change log", ""]
    for h in history[1:]:
        L.append(f"### Iteration {h['iteration']}: {h['score_before']:.0%} -> {h['score']:.0%} ({'kept' if h['accepted'] else 'nothing kept: no fix improved the score'})")
        for a in h.get("attempts", []):
            L.append(f"- Attempt on **{a['category']}**: {a['score_before']:.0%} -> {a['score_after']:.0%} ({'kept' if a['kept'] else 'rejected, no gain'})")
            for c in a["changes"]:
                L.append(f"  - {c['fix']} (addresses {', '.join(c['addresses'])})")
        L.append("")
    final = best
    L += ["## What still fails and why", ""]
    fails = [r for r in final["results"] if not r["pass"]]
    if not fails:
        L.append("No eval failures on this set. That does not mean the agent is perfect: the set was generated from the same documents, and the fixes were tuned on it (see Limits).")
    cnt = Counter(r["failure"] for r in fails)
    L += [f"- {k}: {v}" for k, v in cnt.items()]
    for r in fails:
        L.append(f"- {r['id']} [{r['failure']}] Q: {r['question']} | A: {r['answer'][:160]!r}")
    L += ["", "## Limits of this evidence", "",
          "- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.",
          "- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.",
          "- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.",
          f"- Small model used: {meta['model']}. Quality depends heavily on it; results with another model will differ."]
    (out / "report.md").write_text("\n".join(L) + "\n")
    (out / "scorecard.md").write_text("\n".join(L[L.index("## Scorecard (pass = right docs retrieved, grounded, key facts present, or correct refusal)"):L.index("## Change log")]) + "\n")
