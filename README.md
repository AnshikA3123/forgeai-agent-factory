# ForgeAI: the agent that builds agents

Takes a one-paragraph brief plus a folder of documents and produces a tested agent definition and an honest quality report, unattended.

Pipeline (`forgeai/`): `intake.py` (interviewer, max 5 questions, groundability guard) -> `generator.py` (declarative agent JSON, tool selection from `tools_registry.py`) -> `evalgen.py` (>=20 generated cases) -> `judge.py` -> `optimizer.py` (critic loop, max 3 iterations, every change logged) -> `report.py`. `agent.py` + `cli.py chat` is the generic runner for any produced definition.

## Run
```
./setup.sh   # installs llama-cpp-python + downloads the 0.5B model (free)
export FORGE_MODEL=$PWD/models/qwen.gguf
python -m forgeai build --brief "..." --docs path/to/docs --out runs/mine --unattended   # omit --unattended to answer the 5 questions
python -m forgeai chat --agent runs/mine/agent.json -q "your question"
python -m pytest tests
```
Without `FORGE_MODEL` it falls back to a deterministic extractive baseline (no model).

## Versions
`runs/` = v1 (rule-based generator and optimizer, tag `v1-rule-based`). `runs_v2/` = v2 (model-driven intake, generator, eval generator and failure diagnosis with validation and logged fallbacks); see `runs_v2/README.md` for provenance, weaknesses and the clean held-out result (library brief, 75% -> 75%).

## Demo runs (committed in `runs/`, v1)
- `runs/hr`: HR policy assistant (3 policy docs; brief also asks for payroll tax and visa advice, which the guard flags and refuses).
- `runs/heldout_gym`: gym membership assistant; documents written before running it, no code change afterwards (the clean generalization check).
- `runs/unseen_it`: IT helpdesk; see `runs/README.md` for the post-hoc caveat.
- `runs/procurement`: ship-spares assistant (catalogue CSV + supplier terms + procedure; attaches csv_lookup and calculator only).
Each folder has requirements.json, agent_initial.json, agent.json (best), evalset.json, iterations.json, scorecard.md, report.md.
Prompts: `prompts/` (eval generation, judge, runtime, doc synthesis). Documents are fictional and AI-written.

## Demo video
`forgeai-demo-v3.mp4` (NOT in this repo: the GitHub web upload failed for binary files, so it is delivered separately; silent, 1280x720) is a real screen capture of live command output with on-screen captions (Xvfb + Chrome, ffmpeg x11grab). It shows pytest, the HR brief, a rebuild from CACHED model outputs (0 new model calls, labelled on screen; a fresh no-cache build takes about 15 minutes and is not shown), requirements and provenance, eval case origins, scorecards (HR v3 79% -> 92%, procurement v3 71% -> 71%, held-out library v2c 75% -> 75%), chats, and the limits. Older videos (`forgeai-demo-v2.mp4`) show earlier pipeline versions and are superseded.

## Input formats and how each stage uses the model
Documents: .md, .txt, .csv, and .pdf (PDF needs `pdftotext` from poppler-utils installed; `apt install poppler-utils`; checked here by loading a real PDF, but no demo run uses PDFs). No .docx.
(v1 description) Qwen2.5-0.5B is called for: the intake summary, eval question wording (with a template fallback), adjacent out-of-scope questions, the answers of the generated agent, and a swapped-order support vote in the judge. In v1, NOT model-driven: groundability (lexical vocabulary coverage of brief topics), tool selection (keyword triggers), the system prompt and retrieval parameters (templated from requirements), ambiguous-case wording (heading keywords), expected key facts (extracted from the source sentence), the failure classifier and the fixes (rule-based). Some out-of-scope cases come from a fixed generic list.

## Honest limits
Model is Qwen2.5-0.5B on one CPU, so scores are modest and the report says why. Eval sets come from the same documents the agent reads and fixes are tuned on them. Stretch goals are not implemented. Not yet run on an unseen brief by the author.

See `EXPLANATION.md` for a plain-language walkthrough and `runs/README.md` for score provenance. Every `runs/*/` folder contains its own `docs/`, so `chat --agent runs/<x>/agent.json` works from a fresh clone.

v2 changes: the model now writes intake requirements, generator style instructions, top_k, tool-need verdicts, ambiguous and out-of-scope eval questions, and optimizer diagnoses plus rules. Still rule-based in v2: groundability coverage check (lexical, with the model supplying the topic list), the judge's deterministic checks, tool preconditions (a veto), and bounded fix application. Every model stage logs invalid outputs and fallbacks into the run report.


## Residual limits (found in review of v3)
- Natural domain phrasing that uses words absent from the documents can still be wrongly refused by the retrieval coverage gate. Example: a procurement warranty question phrased with "ship-spares" wording was refused at coverage 0.33, while "warranty period" wording is answered.
- Refusal patterns now require all topic words, so they miss short paraphrases of an unsupported topic. Refusal then depends on the lexical coverage gate, not on any semantic safety check.
- The held-out library result is v2c only; HR and procurement results are v3; see `runs_v3/README.md`.
