# ForgeAI: the agent that builds agents

Takes a one-paragraph brief plus a folder of documents and produces a tested agent definition and an honest quality report, unattended.

Pipeline (`forgeai/`): `intake.py` (interviewer, max 5 questions, groundability guard) -> `generator.py` (declarative agent JSON, tool selection from `tools_registry.py`) -> `evalgen.py` (>=20 generated cases) -> `judge.py` -> `optimizer.py` (critic loop, max 3 iterations, every change logged) -> `report.py`. `agent.py` + `cli.py chat` is the generic runner for any produced definition.

## Run
```
pip install llama-cpp-python pytest
# free small model (491 MB):
curl -L -o qwen.gguf https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
export FORGE_MODEL=$PWD/qwen.gguf
python -m forgeai build --brief "..." --docs path/to/docs --out runs/mine --unattended   # omit --unattended to answer the 5 questions
python -m forgeai chat --agent runs/mine/agent.json -q "your question"
python -m pytest tests
```
Without `FORGE_MODEL` it falls back to a deterministic extractive baseline (no model).

## Demo runs (committed in `runs/`)
- `runs/hr`: HR policy assistant (3 policy docs; brief also asks for payroll tax and visa advice, which the guard flags and refuses).
- `runs/procurement`: ship-spares assistant (catalogue CSV + supplier terms + procedure; attaches csv_lookup and calculator only).
Each folder has requirements.json, agent_initial.json, agent.json (best), evalset.json, iterations.json, scorecard.md, report.md.
Prompts: `prompts/` (eval generation, judge, runtime, doc synthesis). Documents are fictional and AI-written.

## Honest limits
Model is Qwen2.5-0.5B on one CPU, so scores are modest and the report says why. Eval sets come from the same documents the agent reads and fixes are tuned on them. Stretch goals are not implemented. Not yet run on an unseen brief by the author.
