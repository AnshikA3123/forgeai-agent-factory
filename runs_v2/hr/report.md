# ForgeAI run report

Brief: I need an assistant that answers HR policy questions about annual leave, sick leave, remote work and expense claims for shore staff, and also gives payroll tax advice and visa sponsorship guidance.

Model: `qwen.gguf` | 108 model calls | 310s wall time

## Requirements and groundability

- Scope: Answer questions grounded in: expense_policy.md, leave_policy.md, remote_work_policy.md.
- Audience: HR staff
- Tone: informal and professional
- Must answer: Annual leave, Sick leave, Remote work, Expense claims for shore staff
- Must refuse: legal advice, questions about individual people, anything not in the documents, Payroll tax advice, Visa sponsorship guidance
- WARNING: Brief asks for 'Payroll tax advice' but the documents do not support it; the agent will refuse it.
- WARNING: Brief asks for 'Visa sponsorship guidance' but the documents do not support it; the agent will refuse it.

Interview (max 5 questions):
- Who will use this assistant (role, seniority)? -> HR staff (model proposal (unattended))
- What tone should it use (formal, friendly, terse)? -> informal and professional (model proposal (unattended))
- Anything it must refuse or hand off to a human (legal, medical, personal data)? -> legal advice; questions about individual people; anything not in the documents (model proposal (unattended))
- Which topics must it answer well? ->  (assumed default (unattended))
- Who should users contact when it cannot answer? -> the relevant department (assumed default (unattended))

## Agent definition

- Tools attached: none
- Tools deliberately not attached: csv_lookup, calculator, http_api, current_date
- Retrieval: `{"chunk_chars": 600, "top_k": 4, "k1": 1.5, "b": 0.75, "min_coverage": 0.5, "min_score": 1.0}`, 0 query expansions

## Scorecard (pass = right docs retrieved, grounded, key facts present, or correct refusal)

| Iteration | Pass rate | Passed | By case type | Accepted |
|---|---|---|---|---|
| 0 | 79% | 19/24 | {'answerable': '11/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '1/3', 'out_of_scope': '6/6'} | baseline |
| 1 | 88% | 21/24 | {'answerable': '12/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '2/3', 'out_of_scope': '6/6'} | True |
| 2 | 92% | 22/24 | {'answerable': '12/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '3/3', 'out_of_scope': '6/6'} | True |
| 3 | 92% | 22/24 | {'answerable': '12/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '3/3', 'out_of_scope': '6/6'} | False |

## Change log

### Iteration 1: 79% -> 88% (kept)
- Attempt on **prompt_defect**: 79% -> 88% (kept)
  - added answer-focus rule (model-written); max_sentences/max_tokens raised (addresses case-14, case-15)

### Iteration 2: 88% -> 92% (kept)
- Attempt on **prompt_defect**: 88% -> 92% (kept)
  - added answer-focus rule (model-written); max_sentences/max_tokens raised (addresses case-14, case-15)

### Iteration 3: 92% -> 92% (nothing kept: no fix improved the score)

## What still fails and why

- prompt_defect: 2
- case-14 [prompt_defect] Q: How long does a primary caregiver receive for parental leave, and also: can I work from another country for up to 20 working days per year with written manager approval? | A: 'Working from another country is allowed for up to 20 working days per year with written manager approval. [remote_work_policy.md#3]'
- case-15 [prompt_defect] Q: How much is the daily meal allowance for business travel in USD, and also: could you provide information on the eligibility requirements for shore staff to work remotely after completing their 3-month probation period? | A: 'Daily meal allowance during business travel is 45 USD.'

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
