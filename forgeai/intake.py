"""Stage 1 intake interviewer + stage 2 groundability guard."""
import json
import re
import sys

from .llm import prompt
from .text import BM25, chunk_docs, tokens
from .tools_registry import REGISTRY

QUESTIONS = [
    ("audience", "Who will use this assistant (role, seniority)?", "staff of the organisation that owns the documents"),
    ("tone", "What tone should it use (formal, friendly, terse)?", "clear, professional, concise"),
    ("must_refuse", "Anything it must refuse or hand off to a human (legal, medical, personal data)?", "legal advice; questions about individual people; anything not in the documents"),
    ("must_answer", "Which topics must it answer well?", ""),
    ("escalation", "Who should users contact when it cannot answer?", "the relevant department"),
]


def brief_topics(brief):
    """Topics the brief asks for: items of lists after about/covering/including/on, split on commas/and/or."""
    m = re.split(r"\b(?:about|covering|including|regarding|on)\b", brief, maxsplit=1, flags=re.I)
    tail = m[1] if len(m) > 1 else brief
    parts = re.split(r",|;|\band\b|\bor\b|\.", tail)
    out = []
    for p in parts:
        p = re.sub(r"^((also|gives?|can|and)\s+)+", "", p.strip(" .\"'"), flags=re.I).strip()
        if len(tokens(p)) >= 1 and len(p) > 3:
            out.append(p)
    return out


def groundability(brief, chunks, min_cov=0.5):
    idx = BM25(chunks)
    flagged, ok = [], []
    for t in brief_topics(brief):
        toks = tokens(t)
        if not toks:
            continue
        if any(re.search(pat, t.lower()) for r in REGISTRY.values() if not r['needs_csv'] for pat in r['triggers']):
            continue  # a capability a tool provides (e.g. calculate totals), not a document topic
        cov = sum(1 for x in toks if x in idx.vocab) / len(toks)
        (ok if cov >= min_cov else flagged).append({"topic": t, "coverage": round(cov, 2)})
    return {"supported": ok, "unsupported": flagged}


def interview(brief, docs, chunks, llm, answers=None, interactive=False):
    answers = dict(answers or {})
    asked = []
    for key, q, default in QUESTIONS[:5]:
        if key in answers:
            asked.append({"q": q, "a": answers[key], "source": "answers file"})
            continue
        if interactive and sys.stdin.isatty():
            a = input(q + f" [{default}] ") or default
            src = "requester"
        else:
            a, src = default, "assumed default (unattended)"
        answers[key] = a
        asked.append({"q": q, "a": a, "source": src})
    g = groundability(brief, chunks)
    names = ", ".join(d["name"] for d in docs)
    summary = llm.complete(prompt("intake_summary.txt", brief=brief, docs=names), max_tokens=60)
    headings = sorted({c["heading"] for c in chunks if not c["heading"].startswith("row ")})
    must_answer = [t["topic"] for t in g["supported"]] or headings[:8]
    if answers.get("must_answer"):
        must_answer = [answers["must_answer"]] + must_answer
    must_refuse = [x.strip() for x in answers["must_refuse"].split(";") if x.strip()]
    must_refuse += [t["topic"] for t in g["unsupported"]]
    return {
        "brief": brief, "documents": [d["name"] for d in docs], "interview": asked,
        "scope": f"Answer questions grounded in: {names}.", "audience": answers["audience"], "tone": answers["tone"],
        "escalation": answers["escalation"], "must_answer_topics": must_answer, "must_refuse_topics": must_refuse,
        "groundability": g, "model_summary": summary,
        "warnings": [f"Brief asks for '{t['topic']}' but the documents do not support it; the agent will refuse it."
                     for t in g["unsupported"]],
    }
