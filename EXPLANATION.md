# ForgeAI in plain language (for the review)

**What it is.** You give it one paragraph ("I need an assistant that answers HR questions...") and a folder of documents. It builds a small AI assistant, tests it, fixes what it can, and tells you honestly how good it is. All by itself.

**The stages, in order**
1. Intake: reads the brief and documents, asks up to 5 questions (or uses sensible defaults when unattended) and writes a requirements file.
2. Groundability guard: checks every topic in the brief against the documents. If the brief asks for something the documents cannot support (for example "visa advice"), it warns you and tells the assistant to refuse that topic instead of making things up.
3. Generator: writes the assistant's definition: system prompt, how documents are split and searched, which tools it may use (calculator, CSV lookup, weather API, date), and the answer format. It only attaches tools the brief needs.
4. Eval generator: makes at least 20 test cases from the documents themselves: real questions with expected facts, questions that must be refused, and tricky ones (vague, or needing two documents). The prompts used are in `prompts/`.
5. Judge: scores every case. Facts come from the documents, not from the assistant. It checks: right document found, numbers present in the source, key facts in the answer, refusal when needed. A small-model "is this supported?" vote is asked twice with the order swapped and can only lower a grade, which guards against position and self-preference bias.
6. Critic/optimizer: groups failures (retrieval miss, prompt defect, hallucination, wrong refusal), applies ONE targeted fix per group, re-runs, and keeps a fix only if the score improves. Max 3 rounds. Every change is logged with before/after scores.
7. Report: the final agent, the per-round scorecard, and a plain list of what still fails and why. No score is claimed as perfect.
8. Runner: `python -m forgeai chat --agent runs/hr/agent.json` loads any produced definition.

**Why the scores are modest.** The model is Qwen2.5-0.5B, the biggest free model that fits a 1 GB machine. It often drops words or answers a nearby question. The factory is built to catch that, not hide it.

**Honest numbers** (24 generated cases each, see `runs/README.md`): HR 79 -> 88%; procurement 67% (no fix helped, refusals weak); IT helpdesk 71% frozen, 88% after a fix made while looking at that domain (not a clean claim); gym held-out brief 75 -> 92% using only the optimizer, no code change after the documents were written.

**Likely review questions**
- Why not just use a big model? Brief says small imperfect open model; the system must still be trustworthy through checks.
- How do you stop fixes overfitting? You do not fully: fixes are tuned on the same eval set. The report says so. The held-out brief is the check.
- What if the unseen brief has a CSV? The CSV is split into one chunk per row and csv_lookup is attached when the brief mentions prices, parts or catalogues.
- What does not work yet? Stretch goals, a bigger model, and live hosting.


## Demo video and run variance
The current video (`forgeai-demo-v3-extended.mp4`, silent, delivered separately, not in the repo) is a screen capture of real commands; the rebuild step uses cached model outputs and says so on screen. Earlier videos show earlier versions. Scores: HR v3 79% -> 92%, procurement v3 71% -> 71% (no gain found), held-out library v2c 75% -> 75% (v2c only, not re-run under v3). See `runs_v3/README.md` for the review defects (domain label flagged as unsupported, prefix refusal pattern, eval-specific optimizer rules), their fixes and tests, and the disclosure that earlier v2 runs had them.


## v2 (model-driven) summary for the review
The first version used the model only for question wording and answers; the generator and optimizer were rule-based. v2 lets the 0.5B model write requirements, style instructions, tool verdicts, eval questions and failure diagnoses, with validation and visible fallbacks. Honest results: HR 79% -> 92%, procurement 71% -> 71%, a fresh held-out library brief 75% -> 75%. Be ready to say: the small model writes weak instructions, says YES too often, and the lexical groundability check missed "book recommendations" on the held-out brief. The video shows v1 build runs; a v2 recording is pending.


## v4: the unseen-brief test (what to say if asked "did you test an unseen brief?")
Yes, once, honestly. A vet-clinic brief with one unsupported request (dosage advice) was run through v3. The groundability guard failed: the small model listed document headings as topics, the guard flagged a junk topic and missed the real gap. Fix: always check topics taken directly from the brief; keep model topics only if they share a word with the brief. The same run also showed the optimizer keeping a narrated failure as a prompt rule, so the rule filter was tightened. Final unseen run: 58% -> 79% (19/24), dosage questions refused. The video covers HR and procurement v3 only; it does not show this run. See `runs_v4/README.md`.
