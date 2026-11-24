"""ForgeAI CLI.  python -m forgeai build|chat|selftest"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from .agent import Agent, load_agent
from .evalgen import generate_evals
from .generator import generate
from .intake import interview
from .llm import LLM
from .optimizer import optimize
from .report import write_report
from .text import chunk_docs, load_docs


def build(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    docs_out = out / "docs"
    if docs_out.exists():
        shutil.rmtree(docs_out)
    shutil.copytree(a.docs, docs_out)
    llm = LLM(a.model, cache_path=out / "llm_cache.json" if not a.no_cache else None)
    t0 = time.time()
    print(f"[forgeai] model: {llm.name}")
    docs = load_docs(docs_out)
    chunks = chunk_docs(docs, 600)
    answers = json.loads(Path(a.answers).read_text()) if a.answers else None
    req = interview(a.brief, docs, chunks, llm, answers, interactive=not a.unattended)
    (out / "requirements.json").write_text(json.dumps(req, indent=2))
    for w in req["warnings"]:
        print("[groundability] WARNING:", w)
    defn = generate(req, docs, llm)
    (out / "agent_initial.json").write_text(json.dumps(defn, indent=2))
    print("[generator] tools attached:", defn["tools"] or "none", "| not attached:", defn["tools_not_attached"])
    cases = generate_evals(chunks, a.brief, llm, req)
    (out / "evalset.json").write_text(json.dumps(cases, indent=2))
    print(f"[evalgen] {len(cases)} cases:", {t: sum(1 for c in cases if c['type'] == t) for t in sorted({c['type'] for c in cases})})

    def show(rec):
        print(f"[iter {rec['iteration']}] pass rate {rec['score']:.0%} ({rec['passed']}/{rec['total']}) {rec['by_type']}")
    history, best = optimize(defn, docs_out, cases, req, llm, max_iter=3, on_iter=show)
    (out / "agent.json").write_text(json.dumps(best["definition"], indent=2))
    (out / "iterations.json").write_text(json.dumps(history, indent=2))
    from collections import Counter
    ev = getattr(llm, "events", [])
    cases_origin = Counter(("model" if x.get("origin", "").startswith("model") else "template/fallback") for x in cases)
    meta = {"events": ev, "case_origin": dict(cases_origin), "model": llm.name, "seconds": round(time.time() - t0), "llm_calls": llm.calls, "cache_hits": llm.cache_hits}
    write_report(out, req, defn, cases, history, best, meta)
    print(f"[done] {meta}  -> {out}/report.md")


def chat(a):
    agent = load_agent(a.agent, a.docs, LLM(a.model))
    print(f"Loaded {agent.d['name']} (tools: {agent.d['tools'] or 'none'}; model: {agent.llm.name}). Ctrl-D to quit.")
    for line in sys.stdin if a.question is None else [a.question]:
        r = agent.ask(line.strip())
        print("->", r["answer"], "\n   retrieved:", r["retrieved"], "tools:", r["tool_calls"])


def main():
    p = argparse.ArgumentParser(prog="forgeai")
    sp = p.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build")
    b.add_argument("--brief", required=True)
    b.add_argument("--docs", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--answers")
    b.add_argument("--model")
    b.add_argument("--unattended", action="store_true")
    b.add_argument("--no-cache", action="store_true")
    b.set_defaults(f=build)
    c = sp.add_parser("chat")
    c.add_argument("--agent", required=True)
    c.add_argument("--docs")
    c.add_argument("--model")
    c.add_argument("-q", "--question")
    c.set_defaults(f=chat)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
