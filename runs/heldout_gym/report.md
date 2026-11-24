# ForgeAI run report

Brief: I need an assistant that answers member questions about plans and prices, freezing and cancelling, class booking and lockers, and also gives personal training and diet advice.

Model: `qwen.gguf` | 29 model calls | 99s wall time

## Requirements and groundability

- Scope: Answer questions grounded in: gym_facilities.md, gym_membership.md.
- Audience: staff of the organisation that owns the documents
- Tone: clear, professional, concise
- Must answer: plans, freezing, cancelling, class booking, lockers
- Must refuse: legal advice, questions about individual people, anything not in the documents, prices, personal training, diet advice
- WARNING: Brief asks for 'prices' but the documents do not support it; the agent will refuse it.
- WARNING: Brief asks for 'personal training' but the documents do not support it; the agent will refuse it.
- WARNING: Brief asks for 'diet advice' but the documents do not support it; the agent will refuse it.

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
| 0 | 75% | 18/24 | {'answerable': '8/12', 'edge_cross_doc': '2/3', 'edge_ambiguous': '2/3', 'out_of_scope': '6/6'} | baseline |
| 1 | 92% | 22/24 | {'answerable': '10/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '3/3', 'out_of_scope': '6/6'} | True |
| 2 | 92% | 22/24 | {'answerable': '10/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '3/3', 'out_of_scope': '6/6'} | False |

## Change log

### Iteration 1: 75% -> 92% (kept)
- Attempt on **hallucination**: 75% -> 88% (kept)
  - added grounding rule to system prompt + extractive fallback when the answer drifts from context (addresses case-14)
- Attempt on **prompt_defect**: 88% -> 92% (kept)
  - added answer-focus rule; max_sentences/max_tokens raised (addresses case-09)
- Attempt on **wrong_refusal**: 92% -> 92% (rejected, no gain)
  - min_coverage -> 0.35, min_score -> 0.6 (addresses case-01)

### Iteration 2: 92% -> 92% (nothing kept: no fix improved the score)
- Attempt on **wrong_refusal**: 92% -> 92% (rejected, no gain)
  - min_coverage -> 0.35, min_score -> 0.6 (addresses case-01)

## What still fails and why

- wrong_refusal: 1
- prompt_defect: 1
- case-01 [wrong_refusal] Q: How do I know if my locker is available for use? | A: "I can't answer that from the provided documents."
- case-09 [prompt_defect] Q: How many people can be accommodated in a class at a gym? | A: 'A booking must be cancelled at least 2 hours before the class, otherwise a 5 USD no-show charge applies. [gym_facilities.md#0]'

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
