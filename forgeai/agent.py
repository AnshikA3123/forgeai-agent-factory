"""Generic agent runtime: loads any definition JSON and answers questions."""
import json
import re
from pathlib import Path

from . import tools_registry as T
from .llm import LLM, prompt
from .text import BM25, chunk_docs, load_docs, sentences, tokens


class Agent:
    def __init__(self, definition, docs_dir, llm=None):
        self.d = definition
        self.llm = llm or LLM()
        self.docs = load_docs(docs_dir)
        r = self.d["retrieval"]
        self.chunks = chunk_docs(self.docs, r["chunk_chars"])
        self.index = BM25(self.chunks, r.get("k1", 1.5), r.get("b", 0.75))

    def expand(self, qtoks):
        ex = self.d["retrieval"].get("expansions", {})
        out = list(qtoks)
        for t in qtoks:
            out += ex.get(t, [])
        return out

    def coverage(self, qtoks):
        if not qtoks:
            return 0.0
        return sum(1 for t in qtoks if t in self.index.vocab) / len(qtoks)

    def ask(self, question):
        d, r = self.d, self.d["retrieval"]
        refusal = d["output_contract"]["refusal_text"]
        res = {"question": question, "answer": "", "refused": False, "retrieved": [], "context": "", "tool_calls": []}
        qtoks = tokens(question)
        low = question.lower()
        for pat in d.get("refuse_patterns", []):
            if re.search(pat, low):
                res.update(answer=refusal, refused=True, why="refuse_pattern")
                return res
        tool_out = []
        if "calculator" in d["tools"]:
            m = re.search(r"(\d[\d,\.]*(?:\s*[x*/+\-]\s*\d[\d,\.]*)+)", question)
            if m:
                try:
                    tool_out.append(f"calculator({m.group(1)}) = {T.calculator(m.group(1))}")
                except Exception:
                    pass
        if "current_date" in d["tools"] and re.search(r"\btoday|current date", low):
            tool_out.append(f"current_date() = {T.current_date()}")
        if "csv_lookup" in d["tools"]:
            for doc in self.docs:
                if doc["kind"] == "csv":
                    for w in re.findall(r"[A-Za-z0-9\-]{4,}", question):
                        hit = T.csv_lookup(doc["rows"], w)
                        if hit:
                            tool_out.append(f"csv_lookup({w}) = {json.dumps(hit[0])}")
                            break
        res["tool_calls"] = tool_out
        eq = self.expand(qtoks)
        cov = self.coverage(qtoks)
        parts = [p for p in re.split(r",? and also:? |\? (?=[A-Z])|; ", question) if len(tokens(p)) >= 2]
        if len(parts) > 1:  # multi-part question: retrieve for each part, keep the best chunk of each
            seen, hits = set(), []
            for part in parts:
                for sc, c in self.index.search(self.expand(tokens(part)), max(1, r["top_k"] - 1))[:2]:
                    if c["id"] not in seen:
                        seen.add(c["id"])
                        hits.append((sc, c))
            hits.sort(key=lambda x: -x[0])
            hits = hits[: r["top_k"] + 2]
        else:
            hits = self.index.search(eq, r["top_k"])
        res["retrieved"] = [c["id"] for _, c in hits]
        res["coverage"] = round(cov, 2)
        if not tool_out and (cov < r["min_coverage"] or not hits or hits[0][0] < r["min_score"]):
            res.update(answer=refusal, refused=True, why="low_coverage_or_score")
            return res
        ctx = "\n".join(f"[{c['id']}] {c['text']}" for _, c in hits)
        if tool_out:
            ctx = "\n".join(f"[tool] {t}" for t in tool_out) + "\n" + ctx
        res["context"] = ctx
        if self.llm.available:
            ans = self.llm.complete(prompt("agent_runtime.txt", context=ctx, question=question, refusal=refusal),
                                    system=d["system_prompt"], max_tokens=d["output_contract"]["max_tokens"])
        else:
            ss = sorted(sentences(" ".join(c["text"] for _, c in hits)), key=lambda s: -len(set(tokens(s)) & set(eq)))
            ans = " ".join(ss[: d["output_contract"]["max_sentences"]]) + f" [{hits[0][1]['id']}]"
        res["answer"] = ans
        res["refused"] = refusal.lower()[:25] in ans.lower()
        if d["output_contract"].get("extractive_fallback") and not res["refused"] and not tool_out:
            body = re.sub(r"\[[^\]]*\]", "", ans)
            at = set(tokens(body))
            ov = len(at & set(tokens(ctx))) / max(1, len(at))
            if len(tokens(body)) < 4 or ov < 0.6:  # tiny model gave a fragment or drifted: quote the best context sentence instead
                ss = sorted(sentences(" ".join(c["text"] for _, c in hits)), key=lambda x: -len(set(tokens(x)) & set(eq)))
                if ss:
                    ans = ss[0] + f" [{hits[0][1]['id']}]"
                    res["answer"] = ans
                    res["fallback_used"] = True
        if res["refused"] and tool_out:  # a tool produced a result: never refuse over it
            res["answer"] = "Tool result: " + "; ".join(tool_out)
            res["refused"] = False
        return res


def load_agent(path, docs_dir=None, llm=None):
    p = Path(path)
    d = json.loads(p.read_text())
    return Agent(d, docs_dir or p.parent / "docs", llm)
