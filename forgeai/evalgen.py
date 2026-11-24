"""Stage 4 eval generator: cases are generated from the documents (LLM + deterministic fact extraction)."""
import random
import re

from .llm import prompt
from .text import sentences, tokens, BM25

FACT_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s?(?:%|percent|USD|days?|weeks?|months?|hours?|working days|kg|mm|m)?", re.I)

GENERIC_OOS = [
    "What is the weather forecast in Paris tomorrow?",
    "Can you recommend a good stock to invest in?",
    "Write me a Python script to sort a list.",
    "Who won the football world cup in 2018?",
    "What is the capital of Australia?",
    "Give me a recipe for chocolate cake.",
]


def key_facts(sentence):
    facts = [m.group(0).strip().rstrip(",") for m in FACT_RE.finditer(sentence) if re.search(r"\d", m.group(0))]
    facts = [f for f in facts if len(re.sub(r"\D", "", f)) >= 1]
    if not facts:
        toks = sorted(set(tokens(sentence)), key=lambda t: -len(t))
        facts = toks[:2]
    return facts[:3]


def best_sentence(chunk):
    ss = [s for s in sentences(chunk["text"])] or [chunk["text"]]
    return max(ss, key=lambda s: len(FACT_RE.findall(s)))


def clean_q(q):
    if not q:
        return None
    q = q.strip().split("\n")[0].strip(" \"'")
    return q if q.endswith("?") and 12 < len(q) < 200 else None


def fallback_q(chunk):
    return f"What does the policy say about {chunk['heading'].lower()}?"


def gen_question(llm, chunk, sentence=None):
    q = clean_q(llm.complete(prompt("eval_question.txt", doc=chunk["doc"], heading=chunk["heading"], text=(sentence or chunk["text"])[:500]), max_tokens=50))
    return q or fallback_q(chunk), bool(q)


def generate_evals(chunks, brief, llm, req, n_answerable=12, n_cross=3, n_amb=3, n_oos=6, seed=7):
    rnd = random.Random(seed)
    textual = [c for c in chunks]
    by_doc = {}
    for c in textual:
        by_doc.setdefault(c["doc"], []).append(c)
    for v in by_doc.values():
        rnd.shuffle(v)
    picked, i = [], 0
    docs = sorted(by_doc)
    while len(picked) < n_answerable and any(by_doc.values()):
        d = docs[i % len(docs)]
        i += 1
        if by_doc[d]:
            picked.append(by_doc[d].pop())
    cases = []
    used = {}
    while len(picked) < n_answerable and textual:  # small corpus: reuse chunks, different sentence each time
        picked.append(rnd.choice(textual))
    for c in picked:
        ss = sorted(sentences(c["text"]) or [c["text"]], key=lambda x: -len(FACT_RE.findall(x)))
        k = used.get(c["id"], 0)
        used[c["id"]] = k + 1
        s = ss[k % len(ss)]
        q, from_llm = gen_question(llm, c, s)
        cases.append({"type": "answerable", "question": q, "expected_docs": [c["doc"]], "key_facts": key_facts(s),
                      "source_chunk": c["id"], "source_sentence": s, "question_from_llm": from_llm})
    # cross-document: join two questions from different docs
    pool = [c for c in textual if c["doc"] in docs]
    for _ in range(n_cross):
        for _try in range(20):
            a, b = rnd.sample(pool, 2)
            if a["doc"] != b["doc"]:
                break
        sa, sb = best_sentence(a), best_sentence(b)
        qa, _ = gen_question(llm, a, sa)
        qb, _ = gen_question(llm, b, sb)
        cases.append({"type": "edge_cross_doc", "question": qa[:-1] + ", and also: " + qb[0].lower() + qb[1:],
                      "expected_docs": [a["doc"], b["doc"]], "key_facts": key_facts(sa) + key_facts(sb),
                      "source_chunk": [a["id"], b["id"]], "source_sentence": [sa, sb]})
    # ambiguous: keyword-only phrasing of the heading, lenient check
    heads = [c for c in textual if not c["heading"].startswith("row ")]
    for c in rnd.sample(heads, min(n_amb, len(heads))):
        cases.append({"type": "edge_ambiguous", "question": c["heading"].lower() + "?", "expected_docs": [c["doc"]],
                      "key_facts": [], "source_chunk": c["id"], "lenient": True})
    # out of scope: unsupported brief topics + adjacent (LLM) + generic
    oos = [f"Can you help me with {t['topic']}?" for t in req["groundability"]["unsupported"]]
    adj = llm.complete(prompt("eval_adjacent.txt", brief=brief, n=3), max_tokens=120) or ""
    idx = BM25(chunks)
    for x in adj.split("\n")[:3]:
        x = clean_q(re.sub(r"^\s*\d+[.)]\s*", "", x))
        if x:
            qt = tokens(x)
            if qt and sum(t in idx.vocab for t in qt) / len(qt) < 0.8:  # drop ones the documents could plausibly answer
                oos.append(x)
    rnd.shuffle(GENERIC := list(GENERIC_OOS))
    oos += GENERIC
    for q in oos[:n_oos]:
        cases.append({"type": "out_of_scope", "question": q, "expected_docs": [], "key_facts": [], "should_refuse": True})
    for n, c in enumerate(cases):
        c["id"] = f"case-{n+1:02d}"
        c.setdefault("should_refuse", False)
    return cases
