import json, subprocess, sys
from forgeai.tools_registry import calculator, select_tools
from forgeai.text import load_docs, chunk_docs, BM25, tokens
from forgeai.intake import groundability

def test_calc():
    assert calculator("4 x 184.5") == 738.0

def test_tool_selection_attaches_only_needed():
    docs = load_docs("demo_inputs/hr/docs")
    assert select_tools("answer HR policy questions about leave", docs) == []
    docs2 = load_docs("demo_inputs/procurement/docs")
    t = select_tools("catalogue part prices and order totals", docs2)
    assert "csv_lookup" in t and "calculator" in t and "http_api" not in t

def test_groundability_flags_gap():
    chunks = chunk_docs(load_docs("demo_inputs/hr/docs"))
    g = groundability("answers questions about annual leave and visa sponsorship", chunks)
    assert any("visa" in x["topic"] for x in g["unsupported"])

def test_retrieval():
    chunks = chunk_docs(load_docs("demo_inputs/hr/docs"))
    top = BM25(chunks).search(tokens("how many days of sick leave"), 1)[0][1]
    assert top["doc"] == "leave_policy.md"
