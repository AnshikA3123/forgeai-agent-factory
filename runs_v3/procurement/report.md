# ForgeAI run report

Brief: I need an assistant for ship engineers that answers ship-spares procurement questions about part prices from the catalogue, supplier payment terms, warranty and approval limits, and can calculate order totals.

Model: `qwen.gguf` | 62 model calls | 218s wall time

## Requirements and groundability

- Scope: Answer questions grounded in: parts_catalogue.csv, procurement_procedure.md, supplier_terms.md.
- Audience: ship engineers
- Tone: informative and professional
- Must answer: part prices from the catalogue, supplier payment terms, warranty and approval limits
- Must refuse: legal advice, questions about individual people, anything not in the documents

Interview (max 5 questions):
- Who will use this assistant (role, seniority)? -> ship engineers (model proposal (unattended))
- What tone should it use (formal, friendly, terse)? -> informative and professional (model proposal (unattended))
- Anything it must refuse or hand off to a human (legal, medical, personal data)? -> legal advice; questions about individual people; anything not in the documents (model proposal (unattended))
- Which topics must it answer well? ->  (assumed default (unattended))
- Who should users contact when it cannot answer? -> the relevant department (assumed default (unattended))

## Agent definition

- Tools attached: csv_lookup, calculator
- Tools deliberately not attached: http_api, current_date
- Retrieval: `{"chunk_chars": 600, "top_k": 4, "k1": 1.5, "b": 0.75, "min_coverage": 0.5, "min_score": 1.0}`, 0 query expansions

## Scorecard (pass = right docs retrieved, grounded, key facts present, or correct refusal)

| Iteration | Pass rate | Passed | By case type | Accepted |
|---|---|---|---|---|
| 0 | 71% | 17/24 | {'answerable': '9/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '2/3', 'out_of_scope': '5/6'} | baseline |
| 1 | 71% | 17/24 | {'answerable': '9/12', 'edge_cross_doc': '1/3', 'edge_ambiguous': '2/3', 'out_of_scope': '5/6'} | False |

## Change log

### Iteration 1: 71% -> 71% (nothing kept: no fix improved the score)
- Attempt on **hallucination**: 71% -> 71% (rejected, no gain)
  - stricter refusal gate: min_coverage -> 0.6, min_score -> 1.5 (addresses case-19)
  - added grounding rule to system prompt (fixed template) + extractive fallback when the answer drifts from context (addresses case-02, case-13, case-15, case-17)
- Attempt on **prompt_defect**: 71% -> 71% (rejected, no gain)
  - added answer-focus rule (fixed template); max_sentences/max_tokens raised (addresses case-10)
- Attempt on **wrong_refusal**: 71% -> 71% (rejected, no gain)
  - min_coverage -> 0.35, min_score -> 0.6 (addresses case-08)

## What still fails and why

- hallucination: 5
- wrong_refusal: 1
- prompt_defect: 1
- case-02 [hallucination] Q: Could you please specify the amount of the orders that require Superintendent approval? | A: '[2,001 to 15,000 USD]'
- case-08 [wrong_refusal] Q: Do you need at least 3 written quotes for orders above 5,000 USD? | A: "I can't answer that from the provided documents."
- case-10 [prompt_defect] Q: Could you please provide more details about the parts catalogue, such as the lead time, the supplier, and the minimum order quantity? | A: '[parts_catalogue.csv#r7] part_id: MP-1008; description: Exhaust valve spindle; unit_price_usd: 2290.00; lead_time_days: 30; supplier: NordMar Parts; min_order_q'
- case-13 [hallucination] Q: Could you please provide details about the product, including its description, unit price, lead time, supplier, and minimum order quantity, and also: could you please specify the amount of the orders that require Superintendent approval? | A: '[procurement_procedure.md#0] \n[procurement_procedure.md#2]\n[parts_catalogue.csv#r19] \n[parts_catalogue.csv#r2]'
- case-15 [hallucination] Q: How does the "Urgent delivery" feature affect the lead time for catalogue parts in stock, and also: how much does it cost to purchase a Lube oil filter element from Aquila Filters, and how long does it take to receive the order? | A: 'Urgent delivery shortens lead time to 3 working days for catalogue parts in stock. The lead time for Lube oil filter element is 7 days, and the lead time for Fu'
- case-17 [hallucination] Q: Why is it important to inspect goods within 48 hours? | A: 'Inspection within 48 hours ensures that the goods are ready for immediate use, reducing the risk of delays and potential issues that could arise from delays in '
- case-19 [hallucination] Q: Can you recommend a good stock to invest in? | A: '[procurement_procedure.md#3] Goods must be inspected within 48 hours of receipt. Discrepancies are reported to the supplier within 7 days, otherwise the deliver'

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
