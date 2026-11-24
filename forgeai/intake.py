"""Stage 1 intake interviewer + stage 2 groundability guard."""
import json
import re
import sys

from .llm import prompt, ask_json
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


def groundability(brief, chunks, min_cov=0.5, topics=None):
    idx = BM25(chunks)
    flagged, ok = [], []
    for t in (topics or brief_topics(brief)):
        toks = tokens(t)
        if not toks:
            continue
        if any(re.search(pat, t.lower()) for r in REGISTRY.values() if not r['needs_csv'] for pat in r['triggers']):
            continue  # a capability a tool provides (e.g. calculate totals), not a document topic
        cov = sum(1 for x in toks if x in idx.vocab) / len(toks)
        (ok if cov >= min_cov else flagged).append({"topic": t, "coverage": round(cov, 2)})
    return {"supported": ok, "unsupported": flagged}


def _validate_req(o):
    def strs(k, lo, hi):
        v = o[k]
        if not isinstance(v, list) or not (lo <= len(v) <= hi) or not all(isinstance(x, str) and 2 < len(x) < 80 for x in v):
            raise ValueError(f"{k} must be a list of {lo}-{hi} short strings")
        return v
    out = {"requested_topics": strs("requested_topics", 1, 8), "must_refuse": strs("must_refuse", 1, 5)}
    for k in ("audience", "tone"):
        if not isinstance(o.get(k), str) or not (2 < len(o[k]) < 100):
            raise ValueError(f"{k} must be a short string")
        out[k] = o[k]
    return out


def interview(brief, docs, chunks, llm, answers=None, interactive=False):
    answers = dict(answers or {})
    asked = []
    headings0 = sorted({c["heading"] for c in chunks if not c["heading"].startswith("row ")})[:12]
    proposal = ask_json(llm, "intake_requirements", prompt("intake_requirements.txt", brief=brief,
                        docs=", ".join(d["name"] for d in docs), headings="; ".join(headings0) or "(csv rows)"), _validate_req, 220)
    prov = {"requirements": "model" if proposal else "template-fallback (model JSON invalid or no model)"}
    for key, q, default in QUESTIONS[:5]:
        if key in answers:
            asked.append({"q": q, "a": answers[key], "source": "answers file"})
            continue
        if interactive and sys.stdin.isatty():
            a = input(q + f" [{default}] ") or default
            src = "requester"
        else:
            a, src = default, "assumed default (unattended)"
            if proposal and key in ("audience", "tone"):
                a, src = proposal[key], "model proposal (unattended)"
            elif proposal and key == "must_refuse":
                a, src = "; ".join(proposal["must_refuse"]) + "; anything not in the documents", "model proposal (unattended)"
        answers[key] = a
        asked.append({"q": q, "a": a, "source": src})
    g = groundability(brief, chunks, topics=proposal["requested_topics"] if proposal else None)
    prov["topics"] = "model" if proposal else "regex fallback"
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
        "groundability": g, "model_summary": summary, "provenance": prov,
        "warnings": [f"Brief asks for '{t['topic']}' but the documents do not support it; the agent will refuse it."
                     for t in g["unsupported"]],
    }
