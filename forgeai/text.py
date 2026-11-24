"""Tokenising, chunking and BM25 retrieval. Standard library only."""
import csv
import math
import re
from collections import Counter
from pathlib import Path

STOP = set("""a an the of to in on for and or is are was were be been it its this that these those with by as at from
what which who whom how when where why do does did can could should would will may might must i you we they he she
my our your their me us them about any all per if not no yes than then so such into over under between also""".split())


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokens(text, keep_stop=False):
    ws = re.findall(r"[a-z0-9][a-z0-9\-\.%$]*", text.lower())
    out = []
    for w in ws:
        w = w.strip(".-")
        if not w:
            continue
        if not keep_stop and w in STOP:
            continue
        out.append(stem(w))
    return out


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 12]


def load_docs(folder):
    """Return list of {name, kind, text|rows}."""
    docs = []
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() in (".md", ".txt"):
            docs.append({"name": p.name, "kind": "text", "text": p.read_text(encoding="utf-8")})
        elif p.suffix.lower() == ".csv":
            with open(p, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            docs.append({"name": p.name, "kind": "csv", "rows": rows})
        elif p.suffix.lower() == ".pdf":
            import subprocess
            t = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout
            docs.append({"name": p.name, "kind": "text", "text": t})
    return docs


def chunk_docs(docs, chunk_chars=600):
    """Heading-aware chunks. Each chunk: {id, doc, heading, text}."""
    chunks = []
    for d in docs:
        if d["kind"] == "csv":
            for i, r in enumerate(d["rows"]):
                txt = "; ".join(f"{k}: {v}" for k, v in r.items())
                chunks.append({"id": f"{d['name']}#r{i}", "doc": d["name"], "heading": "row %d" % i, "text": txt})
            continue
        heading, buf = "intro", []
        sections = []
        for line in d["text"].splitlines():
            m = re.match(r"^#{1,4}\s+(.*)", line)
            if m:
                if buf:
                    sections.append((heading, "\n".join(buf).strip()))
                heading, buf = m.group(1).strip(), []
            else:
                buf.append(line)
        sections.append((heading, "\n".join(buf).strip()))
        n = 0
        for h, body in sections:
            if not body:
                continue
            cur = ""
            for s in re.split(r"(?<=[.!?])\s+", body):
                if cur and len(cur) + len(s) > chunk_chars:
                    chunks.append({"id": f"{d['name']}#{n}", "doc": d["name"], "heading": h, "text": cur.strip()})
                    n += 1
                    cur = ""
                cur += s + " "
            if cur.strip():
                chunks.append({"id": f"{d['name']}#{n}", "doc": d["name"], "heading": h, "text": cur.strip()})
                n += 1
    return chunks


class BM25:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.toks = [tokens(c["heading"] + " " + c["text"]) for c in chunks]
        self.df = Counter()
        for t in self.toks:
            self.df.update(set(t))
        self.avg = sum(map(len, self.toks)) / max(1, len(self.toks))
        self.vocab = set(self.df)

    def score(self, qtoks):
        n = len(self.chunks)
        res = []
        for i, t in enumerate(self.toks):
            tf = Counter(t)
            s = 0.0
            for q in qtoks:
                if q in tf:
                    idf = math.log(1 + (n - self.df[q] + 0.5) / (self.df[q] + 0.5))
                    s += idf * tf[q] * (self.k1 + 1) / (tf[q] + self.k1 * (1 - self.b + self.b * len(t) / self.avg))
            res.append((s, i))
        res.sort(reverse=True)
        return res

    def search(self, qtoks, k):
        return [(s, self.chunks[i]) for s, i in self.score(qtoks)[:k] if s > 0]
