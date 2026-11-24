# Run provenance
- hr, procurement: demo runs. unseen_it: IT-helpdesk docs written after the pipeline was frozen (frozen result 71%, 17/24, iteration 0, in `unseen_it/v1_pre_extractive_fallback/`).
- After inspecting the unseen run's failures, an `extractive_fallback` option and an optimizer fix that enables it were ADDED. The 71% -> 88% in `unseen_it/` (top level) is therefore a POST-HOC result on a domain the change was informed by, NOT a clean generalization claim. A fresh held-out brief is still needed.
- hr and procurement top-level reports predate this change unless regenerated; check the pipeline version noted in each report.
- heldout_gym: gym membership docs/brief written before the run; pipeline unchanged afterwards. Iteration 0 = 75% (18/24), after optimizer = 92% (22/24). This is the only clean held-out result, and it is one domain.
