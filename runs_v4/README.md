# v4: first truly unseen-brief run and what it found

Unseen brief and documents (written before running, `unseen_v4/`): front-desk assistant for a veterinary clinic, 2 markdown docs + 1 PDF, with one request the documents cannot support (dosage advice).

| Folder | Code | Result | Notes |
|---|---|---|---|
| unseen_vet_attempt1_v3_code | v3 | intake only (stopped) | FAILED the groundability guard: the model returned document headings as "topics", so the guard flagged "introduction" and MISSED the real gap (dosage advice). |
| unseen_vet | v4a (guard fix) | 58% -> 79% (19/24), fresh model calls, no cache | Guard now flags dosage advice; the dosage question is refused and boarding / hours questions are answered. |

Fix v4a (`intake.merge_topics`, test `test_guard_uses_brief_topics_not_model_headings`): topics from the brief are always checked; model topics count only if they share a content word with the brief.

Known defects in the `unseen_vet` (v4a) agent, kept as evidence, not edited:
- Its `prompt_rules` hold a narrated eval failure ("The assistant retrieved documents that were not relevant...") that the v3 filter did not catch, and a useless generator rule ("Use 'vaccinations' instead of 'vaccinations'"). Same class as the v3 defect.
- The refusal pattern needs all four topic words, so it does not fire; the dosage refusal comes from the coverage gate.
The optimizer filter now rejects narrated rules (v4b, `test_narrative_rule_rejected`).

## unseen_vet_b (v4b, final): 58% -> 79% (19/24)
Same unseen documents, rebuilt with the v4b filter (10 tests pass). Per-iteration: 58% -> 71% -> 79% -> 79% (iteration 3 kept nothing). The narrated rule is gone; the applied optimizer rules are the two labelled fixed templates (every model diagnosis was rejected as invalid, field `diagnosis_source`). Checked by hand: a dosage question ("how much ivermectin for my cat") is refused; "how much does boarding cost for a dog per night" is answered with the right figure and citation.
Still weak: prompt rule 1 from the generator step ("Use 'vaccinations' instead of 'vaccinations'") is a useless model-written rule. Edge case: ambiguous questions 2/3. Cases still failing are listed in `report.md`.
This build used the llm cache only to resume after a sandbox restart; the iteration scores equal the earlier fresh v4a run because the sampling is seeded.
The unseen documents are no longer unseen after this run; the 79% is a development result on same-document evals.

Repository note: the unseen brief's PDF (`vaccinations_and_invoices.pdf`) is stored as `unseen_v4/docs/vaccinations_and_invoices.pdf.b64` because GitHub web upload cannot carry binaries. Run `bash unseen_v4/restore_pdf.sh` once after cloning; it recreates the PDF in `unseen_v4/docs` and `runs_v4/unseen_vet_b/docs`. `unseen_vet` (v4a) and the attempt-1 folder used the same documents and do not repeat them.
