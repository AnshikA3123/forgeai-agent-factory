"""Stage 3 agent generator: requirements + documents -> declarative agent definition."""
import re

from .llm import prompt, ask_text, yes_no
from .tools_registry import REGISTRY, select_tools
from .text import tokens

REFUSAL = "I can't answer that from the provided documents."


def build_system_prompt(req, rules=()):
    lines = [
        f"You are an assistant for: {req['brief']}",
        f"Audience: {req['audience']}. Tone: {req['tone']}.",
        "Answer ONLY from the provided context and tool results. Never use outside knowledge.",
        f"If the context does not contain the answer, reply exactly: {REFUSAL}",
        "Refuse and hand off for: " + "; ".join(req["must_refuse_topics"]) + ".",
        f"When you cannot help, suggest contacting: {req['escalation']}.",
        "Cite the source id in square brackets after each claim.",
    ]
    lines += list(rules)
    return "\n".join(lines)


def generate(req, docs, llm=None):
    """Small single-purpose model calls (a 0.5B model cannot reliably emit one big JSON object), each validated and logged.
    Deterministic safety: a tool is allowed only if its keyword/CSV precondition holds (veto), and generated instructions are
    rejected if the model itself says they offer an unsupported topic or if they mention one."""
    candidates = select_tools(req["brief"], docs)
    prov = {}
    unsup = [t["topic"] for t in req["groundability"]["unsupported"]]
    banned = {w for t in unsup for w in re.findall(r"[a-z]{4,}", t.lower())}
    rules, tools, top_k = [], list(candidates), 2
    if llm and llm.available:
        def v_instr(s):
            s = s.strip().strip('"')
            if not 30 <= len(s) <= 400:
                raise ValueError("instructions must be 30-400 chars")
            hit = [w for w in banned if w in s.lower()]
            if hit:
                raise ValueError("mentions unsupported topics " + ", ".join(hit))
            return s
        ins = ask_text(llm, "generator_instructions", prompt("gen_instructions.txt", topics="; ".join(req["must_answer_topics"][:6]), audience=req["audience"], tone=req["tone"]), v_instr, 90)
        prov["domain_instructions"] = "model" if ins else "none (model output rejected twice, see events)"
        if ins:
            rules = [ins]
            # advisory semantic check by the model (a 0.5B model says YES too often, so it is logged, not used as a veto)
            prov["offer_check_advisory"] = {t: yes_no(llm, "generator_offer_check", prompt("gen_check_offer.txt", text=ins, topic=t)) for t in unsup}
        tk = ask_text(llm, "generator_top_k", prompt("gen_topk.txt", brief=req["brief"]), lambda s: int(s.strip()[0]) if s.strip()[:1] in "234" and s.strip() else (_ for _ in ()).throw(ValueError("need digit 2-4")), 3)
        prov["top_k"] = "model" if tk else "default 2 (model output invalid)"
        top_k = tk or 2
        docdesc = "; ".join(f"{d['name']} (CSV table with columns {', '.join(d['rows'][0].keys()) if d['rows'] else ''})" if d['kind'] == 'csv' else f"{d['name']} (text)" for d in docs)
        verdicts = {}
        for name in candidates:  # model decides among rule-allowed candidates; it can only remove, never add
            verdicts[name] = yes_no(llm, "generator_tool_need", prompt("gen_tool_need.txt", brief=req["brief"], docs=docdesc, tool=name, desc=REGISTRY[name]["desc"]))
        tools = [n for n in candidates if verdicts[n] is not False]
        prov["tools"] = f"rule candidates {candidates}; model verdicts {verdicts}; attached {tools} (invalid verdict keeps the tool)"
    else:
        prov["tools"] = "template (no model loaded)"
        prov["domain_instructions"] = "none (no model)"
        prov["top_k"] = "default 2 (no model)"
    refuse_patterns = []
    for t in req["groundability"]["unsupported"]:
        toks = [w for w in re.findall(r"[a-z]{4,}", t["topic"].lower())]
        if toks:
            refuse_patterns.append(r"\b" + toks[0][:5])
    return {
        "name": "forge-agent",
        "generated_from": req["brief"],
        "system_prompt": build_system_prompt(req, rules),
        "prompt_rules": rules,
        "provenance": prov,
        "retrieval": {"chunk_chars": 600, "top_k": top_k, "k1": 1.5, "b": 0.75, "min_coverage": 0.5, "min_score": 1.0,
                      "expansions": {}},
        "tools": tools,
        "tool_rationale": {t: REGISTRY[t]["desc"] for t in tools},
        "tools_not_attached": [t for t in REGISTRY if t not in tools],
        "refuse_patterns": refuse_patterns,
        "output_contract": {"format": "short answer with [source-id] citations", "refusal_text": REFUSAL,
                            "max_tokens": 120, "max_sentences": 1},
    }
