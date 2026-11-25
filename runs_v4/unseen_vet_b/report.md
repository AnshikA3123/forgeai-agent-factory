# ForgeAI run report

Brief: I need an assistant for front-desk staff at Harbour Vet Clinic that answers client questions about opening hours, vaccinations, boarding rules and invoices, and also gives dosage advice for prescription medicines.

Model: `qwen.gguf` | 162 model calls | 1156s wall time

## Requirements and groundability

- Scope: Answer questions grounded in: boarding_rules.md, clinic_hours_and_booking.md, vaccinations_and_invoices.pdf.
- Audience: front-desk staff at Harbour Vet Clinic
- Tone: friendly and brief
- Must answer: opening hours, vaccinations, boarding rules, invoices, Boarding eligibility, Boarding fees
- Must refuse: legal advice, questions about individual people, anything not in the documents, dosage advice for prescription medicines
- WARNING: Brief asks for 'dosage advice for prescription medicines' but the documents do not support it; the agent will refuse it.

Interview (max 5 questions):
- Who will use this assistant (role, seniority)? -> front-desk staff at Harbour Vet Clinic (model proposal (unattended))
- What tone should it use (formal, friendly, terse)? -> friendly and brief (model proposal (unattended))
- Anything it must refuse or hand off to a human (legal, medical, personal data)? -> legal advice; questions about individual people; anything not in the documents (model proposal (unattended))
- Which topics must it answer well? ->  (assumed default (unattended))
- Who should users contact when it cannot answer? -> the relevant department (assumed default (unattended))

## Agent definition

- Tools attached: none
- Tools deliberately not attached: csv_lookup, calculator, http_api, current_date
- Retrieval: `{"chunk_chars": 600, "top_k": 4, "k1": 1.5, "b": 0.75, "min_coverage": 0.3, "min_score": 0.7}`, 0 query expansions

## Scorecard (pass = right docs retrieved, grounded, key facts present, or correct refusal)

| Iteration | Pass rate | Passed | By case type | Accepted |
|---|---|---|---|---|
| 0 | 58% | 14/24 | {'answerable': '6/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '2/3', 'out_of_scope': '5/6'} | baseline |
| 1 | 71% | 17/24 | {'answerable': '7/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '2/3', 'out_of_scope': '5/6'} | True |
| 2 | 79% | 19/24 | {'answerable': '9/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '2/3', 'out_of_scope': '5/6'} | True |
| 3 | 79% | 19/24 | {'answerable': '9/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '2/3', 'out_of_scope': '5/6'} | False |

## Change log

### Iteration 1: 58% -> 71% (kept)
- Attempt on **hallucination**: 58% -> 62% (kept)
  - stricter refusal gate: min_coverage -> 0.6, min_score -> 1.5 (addresses case-20)
  - added grounding rule to system prompt (fixed template) + extractive fallback when the answer drifts from context (addresses case-06, case-13, case-15, case-18)
- Attempt on **prompt_defect**: 62% -> 67% (kept)
  - added answer-focus rule (fixed template); max_sentences/max_tokens raised (addresses case-12)
- Attempt on **wrong_refusal**: 67% -> 71% (kept)
  - min_coverage -> 0.45, min_score -> 1.1 (addresses case-04, case-08, case-11)

### Iteration 2: 71% -> 79% (kept)
- Attempt on **hallucination**: 71% -> 71% (rejected, no gain)
  - stricter refusal gate: min_coverage -> 0.55, min_score -> 1.6 (addresses case-20)
- Attempt on **wrong_refusal**: 71% -> 79% (kept)
  - min_coverage -> 0.3, min_score -> 0.7 (addresses case-04, case-08, case-11)

### Iteration 3: 79% -> 79% (nothing kept: no fix improved the score)
- Attempt on **hallucination**: 79% -> 71% (rejected, no gain)
  - stricter refusal gate: min_coverage -> 0.4, min_score -> 1.2 (addresses case-20)
- Attempt on **wrong_refusal**: 79% -> 75% (rejected, no gain)
  - min_coverage -> 0.2, min_score -> 0.3 (addresses case-11)

## What still fails and why

- prompt_defect: 2
- wrong_refusal: 1
- hallucination: 2
- case-01 [prompt_defect] Q: How much will the boarding fee be for a dog and a cat if you choose to stay together? | A: 'Dogs and cats may board at the clinic. [boarding_rules.md#0]'
- case-11 [wrong_refusal] Q: Can I check in for boarding if my dog has not had a kennel cough vaccination for 10 days? | A: "I can't answer that from the provided documents."
- case-12 [prompt_defect] Q: When is the clinic typically closed on weekdays? | A: 'Monday to Friday from 8:00 to 18:00'
- case-16 [hallucination] Q: Why is there a 15% discount for a second pet? | A: 'A second pet receives a 15% discount. [source-id: boarding_rules.md#1]'
- case-20 [hallucination] Q: What is the name of the assistant's role at Harbour Vet Clinic? | A: 'front-desk staff at Harbour Vet Clinic'

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
