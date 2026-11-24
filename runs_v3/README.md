# v3 runs: fixes for two review defects (and what changed)

v3 = v2 pipeline + three code fixes. Old runs (`runs/`, `runs_v2/`, `runs_v3a_example_copied/`) are kept unedited as historical evidence.

Defects found in review of v2:
1. Procurement: intake flagged the brief's own domain label ("ship-spares procurement") as an unsupported topic. The generator then made the refusal pattern `\bship` (first 5 letters of the first topic word), which refused real warranty and supplier questions that contained "shipping"/"ship".
2. HR: the optimizer's model-written "rule" text was copied into `prompt_rules` even when it described the failing eval case (for example an expected answer), so the agent prompt held eval-specific text.

Fixes (code level, with regression tests in `tests/test_core.py`):
- `intake.groundability`: words in the brief's framing clause (before about/covering/including/regarding/on) name the domain and are not flagged. Limitation: a truly unsupported topic named only in the framing clause would not be flagged.
- `generator`: refusal pattern now needs ALL topic words as whole words.
- `optimizer.generic_rule_problem`: a model-written rule is rejected (and the model re-asked, then the labelled fixed-template rule is used) if it has digits, quotes, case words, failure-description wording, or copies the prompt example. `prompts/optimizer_diagnose.txt` no longer contains a worked example rule.

| Folder | Pipeline | What it is | Result (24 cases) |
|---|---|---|---|
| runs_v3a_example_copied/{hr,procurement} | v3a (first fix attempt) | DEVELOPMENT evidence. Model copied the prompt's example rule ("state the exact number of days...") verbatim, so the example was removed (v3b). HR 79->88, procurement 71->83 | see scorecards |
| runs_v3/hr | v3b | HR demo, rebuilt with caches of unchanged calls (intake, generator, eval-gen) and new optimizer calls | 79% -> 92% |
| runs_v3/procurement | v3b | Procurement demo. Domain no longer flagged; refusal pattern list empty. Optimizer found no gain | 71% -> 71% |

Facts to keep honest:
- In v3b all procurement diagnoses and 6 of 7 HR diagnoses were rejected by the new filter or invalid, so labelled fixed-template rules were used (see `iterations.json`, field `diagnosis_source`). HR's applied rules are the fixed templates. One HR iteration-2 model rule ("The assistant failed to retrieve...") passed the filter then; it was tried in an iteration-2 attempt and rejected for no score gain, so it is not in the final agent. I tightened the filter afterwards to catch that wording (test added); that final tightening was not followed by a rerun.
- HR `prompt_rules` 1-2 ("Use 'Annual leave'...") come from the generator's instruction step (derived from the brief's topics), not from the optimizer or eval cases. They are weak instructions.
- Cached runs: the v3 builds reused `llm_cache.json` entries for unchanged prompts; only changed prompts were new model calls.
- The held-out library result (75% -> 75%, `runs_v2/heldout_library`) belongs to pipeline v2c only. It was NOT re-run under v3 and is not evidence for v3. Its refusal patterns were built with the old prefix rule.
- Eval sets come from the same documents; scores are optimistic. Procurement remains 71%.

## Residual limits (found in review of v3)
- Natural domain phrasing that uses words absent from the documents can still be wrongly refused by the retrieval coverage gate. Example: a procurement warranty question phrased with "ship-spares" wording was refused at coverage 0.33, while "warranty period" wording is answered.
- Refusal patterns now require all topic words, so they miss short paraphrases of an unsupported topic. Refusal then depends on the lexical coverage gate, not on any semantic safety check.
- The held-out library result is v2c only; HR and procurement results are v3; see `runs_v3/README.md`.
