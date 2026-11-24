# ForgeAI run report

Brief: I need an assistant that answers employee questions about password rules, lost devices, helpdesk hours and software requests, and also gives legal advice on data breaches.

Model: `qwen.gguf` | 4 model calls | 16s wall time

## Requirements and groundability

- Scope: Answer questions grounded in: it_helpdesk.md, it_security.md.
- Audience: staff of the organisation that owns the documents
- Tone: clear, professional, concise
- Must answer: password rules, lost devices, helpdesk hours, software requests
- Must refuse: legal advice, questions about individual people, anything not in the documents, legal advice on data breaches
- WARNING: Brief asks for 'legal advice on data breaches' but the documents do not support it; the agent will refuse it.

Interview (max 5 questions):
- Who will use this assistant (role, seniority)? -> staff of the organisation that owns the documents (assumed default (unattended))
- What tone should it use (formal, friendly, terse)? -> clear, professional, concise (assumed default (unattended))
- Anything it must refuse or hand off to a human (legal, medical, personal data)? -> legal advice; questions about individual people; anything not in the documents (assumed default (unattended))
- Which topics must it answer well? ->  (assumed default (unattended))
- Who should users contact when it cannot answer? -> the relevant department (assumed default (unattended))

## Agent definition

- Tools attached: none
- Tools deliberately not attached: csv_lookup, calculator, http_api, current_date
- Retrieval: `{"chunk_chars": 600, "top_k": 2, "k1": 1.5, "b": 0.75, "min_coverage": 0.5, "min_score": 1.0}`, 0 query expansions

## Scorecard (pass = right docs retrieved, grounded, key facts present, or correct refusal)

| Iteration | Pass rate | Passed | By case type | Accepted |
|---|---|---|---|---|
| 0 | 71% | 17/24 | {'answerable': '6/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '2/3', 'out_of_scope': '6/6'} | baseline |
| 1 | 88% | 21/24 | {'answerable': '10/12', 'edge_cross_doc': '2/3', 'edge_ambiguous': '3/3', 'out_of_scope': '6/6'} | True |
| 2 | 88% | 21/24 | {'answerable': '10/12', 'edge_cross_doc': '2/3', 'edge_ambiguous': '3/3', 'out_of_scope': '6/6'} | False |

## Change log

### Iteration 1: 71% -> 88% (kept)
- Attempt on **hallucination**: 71% -> 79% (kept)
  - added grounding rule to system prompt + extractive fallback when the answer drifts from context (addresses case-18)
- Attempt on **prompt_defect**: 79% -> 88% (kept)
  - added answer-focus rule; max_sentences/max_tokens raised (addresses case-10)
- Attempt on **wrong_refusal**: 88% -> 83% (rejected, no gain)
  - min_coverage -> 0.35, min_score -> 0.6 (addresses case-06)

### Iteration 2: 88% -> 88% (nothing kept: no fix improved the score)
- Attempt on **wrong_refusal**: 88% -> 83% (rejected, no gain)
  - min_coverage -> 0.35, min_score -> 0.6 (addresses case-06)

## What still fails and why

- hallucination: 1
- wrong_refusal: 1
- prompt_defect: 1
- case-05 [hallucination] Q: How often are laptops typically replaced in the hardware refresh process? | A: 'Laptops are typically replaced every 4 years.'
- case-06 [wrong_refusal] Q: How can I ensure that suspicious emails are properly flagged and removed from my system? | A: "I can't answer that from the provided documents."
- case-13 [prompt_defect] Q: How long should a lost laptop or phone be reported to the IT helpdesk, and also: how long does it typically take to review new software requests? | A: 'A lost laptop or phone must be reported to the IT helpdesk within 2 hours. [it_security.md#1]'

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
