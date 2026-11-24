# ForgeAI run report

Brief: I need an assistant for ship engineers that answers ship-spares procurement questions about part prices from the catalogue, supplier payment terms, warranty and approval limits, and can calculate order totals.

Model: `qwen.gguf` | 0 model calls | 0s wall time

## Requirements and groundability

- Scope: Answer questions grounded in: parts_catalogue.csv, procurement_procedure.md, supplier_terms.md.
- Audience: staff of the organisation that owns the documents
- Tone: clear, professional, concise
- Must answer: part prices from the catalogue, supplier payment terms, warranty, approval limits
- Must refuse: legal advice, questions about individual people, anything not in the documents

Interview (max 5 questions):
- Who will use this assistant (role, seniority)? -> staff of the organisation that owns the documents (assumed default (unattended))
- What tone should it use (formal, friendly, terse)? -> clear, professional, concise (assumed default (unattended))
- Anything it must refuse or hand off to a human (legal, medical, personal data)? -> legal advice; questions about individual people; anything not in the documents (assumed default (unattended))
- Which topics must it answer well? ->  (assumed default (unattended))
- Who should users contact when it cannot answer? -> the relevant department (assumed default (unattended))

## Agent definition

- Tools attached: csv_lookup, calculator
- Tools deliberately not attached: http_api, current_date
- Retrieval: `{"chunk_chars": 600, "top_k": 2, "k1": 1.5, "b": 0.75, "min_coverage": 0.5, "min_score": 1.0}`, 0 query expansions

## Scorecard (pass = right docs retrieved, grounded, key facts present, or correct refusal)

| Iteration | Pass rate | Passed | By case type | Accepted |
|---|---|---|---|---|
| 0 | 67% | 16/24 | {'answerable': '9/12', 'edge_cross_doc': '2/3', 'edge_ambiguous': '2/3', 'out_of_scope': '3/6'} | baseline |
| 1 | 67% | 16/24 | {'answerable': '9/12', 'edge_cross_doc': '2/3', 'edge_ambiguous': '2/3', 'out_of_scope': '3/6'} | False |

## Change log

### Iteration 1: 67% -> 67% (nothing kept: no fix improved the score)
- Attempt on **hallucination**: 67% -> 62% (rejected, no gain)
  - stricter refusal gate: min_coverage -> 0.6, min_score -> 1.5 (addresses case-20, case-21, case-22)
- Attempt on **wrong_refusal**: 67% -> 67% (rejected, no gain)
  - min_coverage -> 0.35, min_score -> 0.6 (addresses case-04, case-08, case-10, case-14, case-17)

## What still fails and why

- wrong_refusal: 5
- hallucination: 3
- case-04 [wrong_refusal] Q: How much does it cost to purchase a Lube oil filter element from Aquila Filters, and how long does it take to receive the order? | A: "I can't answer that from the provided documents."
- case-08 [wrong_refusal] Q: Do you need at least 3 written quotes for orders above 5,000 USD? | A: "I can't answer that from the provided documents."
- case-10 [wrong_refusal] Q: Could you please provide more details about the parts catalogue, such as the lead time, the supplier, and the minimum order quantity? | A: "I can't answer that from the provided documents."
- case-14 [wrong_refusal] Q: Could you please specify the amount of the orders that require Superintendent approval, and also: how much does an Emergency escape breathing device cost, and how long does it take to order? | A: "I can't answer that from the provided documents."
- case-17 [wrong_refusal] Q: receiving goods? | A: "I can't answer that from the provided documents."
- case-20 [hallucination] Q: What is the maximum approval limit for the spare parts? | A: '2,000 USD'
- case-21 [hallucination] Q: What is the price of the spare parts from the catalogue? | A: 'The price of the spare parts from the catalogue is not provided in the given context.'
- case-22 [hallucination] Q: Can you recommend a good stock to invest in? | A: '[procurement_procedure.md#3]'

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
