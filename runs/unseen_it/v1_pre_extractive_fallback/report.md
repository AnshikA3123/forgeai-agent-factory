# ForgeAI run report

Brief: I need an assistant that answers employee questions about password rules, lost devices, helpdesk hours and software requests, and also gives legal advice on data breaches.

Model: `qwen.gguf` | 7 model calls | 23s wall time

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
| 1 | 71% | 17/24 | {'answerable': '6/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '2/3', 'out_of_scope': '6/6'} | False |

## Change log

### Iteration 1: 71% -> 71% (nothing kept: no fix improved the score)
- Attempt on **hallucination**: 71% -> 71% (rejected, no gain)
  - added grounding rule to system prompt (addresses case-18)
- Attempt on **prompt_defect**: 71% -> 67% (rejected, no gain)
  - added answer-focus rule; max_sentences/max_tokens raised (addresses case-03, case-07, case-09, case-10, case-12)
- Attempt on **wrong_refusal**: 71% -> 67% (rejected, no gain)
  - min_coverage -> 0.35, min_score -> 0.6 (addresses case-06)

## What still fails and why

- prompt_defect: 5
- wrong_refusal: 1
- hallucination: 1
- case-03 [prompt_defect] Q: When is the helpdesk open for support? | A: '0'
- case-06 [wrong_refusal] Q: How can I ensure that suspicious emails are properly flagged and removed from my system? | A: "I can't answer that from the provided documents."
- case-07 [prompt_defect] Q: How can I report an urgent outage outside my usual support hours? | A: 'To report an urgent outage outside your usual support hours, contact the IT helpdesk within 2 hours. The helpdesk will remotely wipe the device within 1 hour of'
- case-09 [prompt_defect] Q: When is the helpdesk open for support? | A: '0'
- case-10 [prompt_defect] Q: When should a monitor be replaced according to the passage? | A: 'When accessories such as keyboards are issued on request.'
- case-12 [prompt_defect] Q: How can I report an urgent outage outside my usual support hours? | A: 'To report an urgent outage outside your usual support hours, contact the IT helpdesk within 2 hours. The helpdesk will remotely wipe the device within 1 hour of'
- case-18 [hallucination] Q: lost devices? | A: 'Lost devices'

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
