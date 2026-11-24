"""Stage 3 agent generator: requirements + documents -> declarative agent definition."""
import re

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


def generate(req, docs):
    tools = select_tools(req["brief"], docs)
    refuse_patterns = []
    for t in req["groundability"]["unsupported"]:
        toks = [w for w in re.findall(r"[a-z]{4,}", t["topic"].lower())]
        if toks:
            refuse_patterns.append(r"\b" + toks[0][:5])
    return {
        "name": "forge-agent",
        "generated_from": req["brief"],
        "system_prompt": build_system_prompt(req),
        "prompt_rules": [],
        "retrieval": {"chunk_chars": 600, "top_k": 2, "k1": 1.5, "b": 0.75, "min_coverage": 0.5, "min_score": 1.0,
                      "expansions": {}},
        "tools": tools,
        "tool_rationale": {t: REGISTRY[t]["desc"] for t in tools},
        "tools_not_attached": [t for t in REGISTRY if t not in tools],
        "refuse_patterns": refuse_patterns,
        "output_contract": {"format": "short answer with [source-id] citations", "refusal_text": REFUSAL,
                            "max_tokens": 120, "max_sentences": 1},
    }
