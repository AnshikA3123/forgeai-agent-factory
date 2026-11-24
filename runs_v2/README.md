# v2 (model-driven) runs: provenance

v1 = rule-based generator/optimizer (git tag `v1-rule-based`, folders `runs/`). v2 = stages driven by the 0.5B Qwen model with JSON/text validation, logged fallbacks and deterministic safety checks. Every v2 report has a section listing per-stage model calls, invalid outputs and case origins.

| Folder | Pipeline | What it is | Result (24 cases) |
|---|---|---|---|
| hr_a_generator_fallback | v2a: one-JSON generator | HR. Generator JSON failed twice, template used (labelled) | 75% -> 83% |
| hr_b_json_generator_fallback | v2b: same | HR. Generator fell back again | 75% -> 83% |
| hr | v2c: small-call generator | HR demo, all stages model-driven, generator OK | 79% -> 92% |
| procurement_v2c_tool_underattach | v2c | DEVELOPMENT evidence: model said NO to both tools the brief needs (csv_lookup, calculator) so none were attached | 71% -> 71% |
| procurement | v2d: tool-need prompt shows the document kinds | procurement demo, attaches csv_lookup + calculator (model said YES to both) | 71% -> 71% |
| heldout_library | v2c | HELD-OUT: docs in heldout_v2/ written before any v2 run on them, no pipeline change after seeing it | 75% -> 75% (optimizer found no gain) |

Notes and weaknesses (real):
- The held-out library result was produced by v2c. After it I changed only the tool-need prompt (v2d, tested on procurement). The library run was NOT re-run, so its result is untouched by tuning.
- Groundability (lexical) missed one of the two unsupported asks in the library brief: it flagged "reading lists for children" but not "book recommendations" (the word "book" appears in the documents). The agent therefore has no refusal rule for that ask.
- Model-written "adjacent" out-of-scope questions were all filtered out for the library run (they overlapped supported topics), so 5 of 6 out-of-scope cases came from the fixed generic list (template-fallback, labelled per case).
- Model-written style instructions are weak (for example "Use 'Annual leave' as the document section"). The optimizer's model-written rules were used where kept.
- The model says YES too often in yes/no checks (an advisory offer-check flagged harmless instructions). The model can only remove rule-allowed tools; with HR having no candidates, its ability to correctly say NO is untested.
- The same 0.5B model judges support votes; results are optimistic (eval sets from the same documents, fixes tuned on them).
- v1 numbers and v2 numbers are different pipelines; do not compare them as an improvement claim.
