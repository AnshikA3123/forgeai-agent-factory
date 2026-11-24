# ForgeAI run report

Brief: I need an assistant for library members that answers questions about borrowing, renewals, fines, membership, opening hours and study rooms, and also gives book recommendations and recommends reading lists for children.

Model: `qwen.gguf` | 73 model calls | 176s wall time

## Requirements and groundability

- Scope: Answer questions grounded in: borrowing_rules.md, membership_and_spaces.md.
- Audience: library members
- Tone: friendly and brief
- Must answer: Library borrowing rules, Membership and spaces, Opening hours, Study rooms, Fines, Lost items, Renewals
- Must refuse: legal advice, questions about individual people, anything not in the documents, Reading lists for children
- WARNING: Brief asks for 'Reading lists for children' but the documents do not support it; the agent will refuse it.

Interview (max 5 questions):
- Who will use this assistant (role, seniority)? -> library members (model proposal (unattended))
- What tone should it use (formal, friendly, terse)? -> friendly and brief (model proposal (unattended))
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
| 0 | 75% | 18/24 | {'answerable': '8/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '1/3', 'out_of_scope': '6/6'} | baseline |
| 1 | 75% | 18/24 | {'answerable': '8/12', 'edge_cross_doc': '3/3', 'edge_ambiguous': '1/3', 'out_of_scope': '6/6'} | False |

## Change log

### Iteration 1: 75% -> 75% (nothing kept: no fix improved the score)
- Attempt on **retrieval_miss**: 75% -> 75% (rejected, no gain)
  - added 17 query expansions (question words absent from the expected chunk -> its heading words) (addresses case-05, case-06, case-09, case-12, case-16, case-18)

## What still fails and why

- prompt_defect: 1
- wrong_refusal: 4
- hallucination: 1
- case-05 [prompt_defect] Q: Can you provide information on how to make a renewal online, by phone, or at the front desk? | A: '[borrowing_rules.md#1] Items can be renewed twice, for 14 days each time, unless another member has reserved them.'
- case-06 [wrong_refusal] Q: How many people can be accommodated in a study room according to the passage? | A: "I can't answer that from the provided documents."
- case-09 [wrong_refusal] Q: Is there a specific day on which the membership and spaces office is open? | A: "I can't answer that from the provided documents."
- case-12 [wrong_refusal] Q: Can you confirm if the passage states that reference works and newspapers cannot leave the building? | A: "I can't answer that from the provided documents."
- case-16 [hallucination] Q: Why can't I borrow a DVD or audiobook? | A: '[borrowing_rules.md#2]'
- case-18 [wrong_refusal] Q: Why is it difficult to find a study room? | A: "I can't answer that from the provided documents."

## Limits of this evidence

- Eval cases come from the same documents the agent reads; fixes (query expansions, thresholds) are tuned on this set, so the final score is optimistic.
- Key facts are extracted deterministically from one sentence per chunk; an answer that is correct but phrased differently can be marked wrong.
- The judge combines deterministic checks with a small-model support vote that only counts when it agrees in both prompt orderings.
- Small model used: qwen.gguf. Quality depends heavily on it; results with another model will differ.
