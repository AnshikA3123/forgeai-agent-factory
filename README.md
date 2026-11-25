# ForgeAI: the agent that builds agents

ForgeAI takes a one-paragraph brief plus a folder of documents and, unattended, produces a tested agent definition (system prompt, retrieval settings, tools, output contract), a generated eval set, a per-iteration scorecard and an honest report. All stages run on a small free open model (Qwen2.5-0.5B via llama.cpp, one CPU). No paid API, no key.

## Quickstart
```
./setup.sh                                   # deps + 0.5B model (~490 MB)
export FORGE_MODEL=$PWD/models/qwen.gguf
python3 -m pytest -q tests                   # 10 tests
bash unseen_v4/restore_pdf.sh                # recreates the unseen PDF from base64 (GitHub upload cannot carry binaries)
python3 -m forgeai build --brief "$(cat unseen_v4/brief.txt)" --docs unseen_v4/docs --out runs/mine --unattended
python3 -m forgeai chat --agent runs/mine/agent.json -q "your question"
```
Omit `--unattended` to answer the (max 5) interview questions. A build takes about 20 minutes on one CPU. Documents: .md .txt .csv .pdf (PDF needs `pdftotext`, poppler-utils).

## The nine requirements, and where they live
| # | Requirement | Code | Evidence |
|---|---|---|---|
| 1 | Intake interviewer, max 5 questions, requirements doc | `forgeai/intake.py` | `*/requirements.json` |
| 2 | Groundability guard | `intake.groundability`, `intake.merge_topics` | `requirements.json` -> `groundability`; report warnings |
| 3 | Agent generator, only needed tools | `forgeai/generator.py`, `tools_registry.py` | `agent_initial.json`, `agent.json` |
| 4 | Generated eval set (>=20 cases) | `forgeai/evalgen.py`, `prompts/` | `evalset.json` (24 cases, origin logged per case) |
| 5 | Judge with bias defences | `forgeai/judge.py` | deterministic checks + order-swapped LLM vote; see docstring |
| 6 | Critic-optimizer, max 3 iterations, logged | `forgeai/optimizer.py` | `iterations.json`, report change log |
| 7 | Honest reporting | `forgeai/report.py` | `report.md`, `scorecard.md` |
| 8 | Runnable generic chat runner | `forgeai/cli.py chat`, `agent.py` | `python3 -m forgeai chat --agent <agent.json>` |
| 9 | Two full demos committed | | `runs_v3/hr`, `runs_v3/procurement` (final), earlier versions in `runs/`, `runs_v2/` |

Tools registry (4): csv_lookup, calculator, keyless HTTP API (open-meteo), current date. The HR runs attach none; procurement attaches csv_lookup and calculator.

## Results (24 generated cases per run, same-document evals, so optimistic)
| Run | Pipeline | Score |
|---|---|---|
| HR policy | v3 | 79% -> 92% (22/24) |
| Ship-spares procurement | v3 | 71% -> 71% (17/24) |
| Unseen vet-clinic brief (md + PDF), `runs_v4/unseen_vet_b` | v4 | 58% -> 79% (19/24); first attempt on v3 code missed the real gap, see `runs_v4/README.md` |
| Held-out library (earlier pipeline only) | v2c | 75% -> 75%; not re-run on later versions |

## Versions
v1 rule-based (rejected). v2 model-driven stages with validation and logged fallbacks. v3 fixed over-refusal from a prefix refusal pattern and eval-specific text leaking into prompt rules. v4 fixed the groundability guard on a brand-new brief (the model returned document headings as topics and the real gap was missed) and tightened the optimizer rule filter against narrated failures. Old run folders are kept unedited as evidence; each folder's README states what it is.

## Honest limits
- Qwen2.5-0.5B is small. Scores are modest; the optimizer often falls back to labelled fixed-template rules because the model's rules fail validation.
- Eval sets are generated from the same documents the agent reads, and fixes are tuned on them. Scores are optimistic. Only one genuinely held-out check exists, and on an older version.
- The lexical coverage gate wrongly refuses natural phrasing that uses words absent from the documents.
- Refusal patterns need all topic words, so short paraphrases of an unsupported topic are caught only by the coverage gate, not by semantic understanding.
- Not implemented: stretch goals (prompt tournament, budget enforcement beyond stop-when-no-gain, human checkpoint, baseline, regression mode, UI/hosting).
- The v4 unseen documents were written before the run but are no longer unseen; that 79% is a development result.
- A useless model-written rule can still enter the prompt from the generator step.
- Documents in all demos are fictional and AI-written (`prompts/doc_synthesis.md`).

See `EXPLANATION.md` for a plain-language walkthrough.
