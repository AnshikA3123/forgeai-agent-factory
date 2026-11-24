# ForgeAI run report

Brief: I need an assistant that answers HR policy questions about annual leave, sick leave, remote work and expense claims for shore staff, and also gives payroll tax advice and visa sponsorship guidance.

Model: `qwen.gguf` | 22 model calls | 42s wall time

## Requirements and groundability

- Scope: Answer questions grounded in: expense_policy.md, leave_policy.md, remote_work_policy.md.
- Audience: staff of the organisation that owns the documents
- Tone: clear, professional, concise
- Must answer: annual leave, sick leave, remote work, expense claims for shore staff
- Must refuse: legal advice, questions about individual people, anything not in the documents, payroll tax advice, visa sponsorship guidance
- WARNING: Brief asks for 'payroll tax advice' but the documents do not support it; the agent will refuse it.
- WARNING: Brief asks for 'visa sponsorship guidance' but the documents do not support it; the agent will refuse it.

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
| 0 | 79% | 19/24 | {'answerable': '10/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '3/3', 'out_of_scope': '5/6'} | baseline |
| 1 | 88% | 21/24 | {'answerable': '12/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '3/3', 'out_of_scope': '5/6'} | True |
| 2 | 88% | 21/24 | {'answerable': '12/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '3/3', 'out_of_scope': '5/6'} | False |

## Change log

### Iteration 1: 79% -> 88% (kept)
- Attempt on **hallucination**: 79% -> 79% (rejected, no gain)
  - stricter refusal gate: min_coverage -> 0.6, min_score -> 1.5 (addresses case-21)
  - added grounding rule to system prompt + extractive fallback when the answer drifts from context (addresses case-02)
- Attempt on **prompt_defect**: 79% -> 88% (kept)
  - added answer-focus rule; max_sentences/max_tokens raised (addresses case-05, case-14, case-15)

### Iteration 2: 88% -> 88% (nothing kept: no fix improved the score)
- Attempt on **hallucination**: 88% -> 83% (rejected, no gain)
  - stricter refusal gate: min_coverage -> 0.6, min_score -> 1.5 (addresses case-21)

## What still fails and why

- prompt_defect: 2
- hallucination: 1
- case-14 [prompt_defect] Q: How long does a primary caregiver receive for parental leave, and also: can I work from another country for up to 20 working days per year with written manager approval? | A: 'Working from another country is allowed for up to 20 working days per year with written manager approval. [remote_work_policy.md#3]'
- case-15 [prompt_defect] Q: How much is the daily meal allowance for business travel in USD, and also: could you provide information on the eligibility requirements for shore staff to work remotely after completing their 3-month probation period? | A: 'Shore staff may work remotely after completing their 3-month probation period. [remote_work_policy.md#0]'
- case-21 [hallucination] Q: What is the company's stance on remote work policies? | A: "The company's stance on remote work policies is that remote workers receive a home-office allowance of 40 USD per month, paid with the monthly salary."

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
