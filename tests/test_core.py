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


def test_domain_label_not_flagged_unsupported():  # v3 regression: procurement brief flagged its own domain
    chunks = chunk_docs(load_docs("demo_inputs/procurement/docs"))
    b = "I need an assistant for ship engineers that answers ship-spares procurement questions about part prices from the catalogue, supplier payment terms."
    g = groundability(b, chunks, topics=["ship-spares procurement", "supplier payment terms"])
    assert not any("ship" in x["topic"] for x in g["unsupported"])
    chunks = chunk_docs(load_docs("demo_inputs/hr/docs"))
    g = groundability("answers HR questions about leave, and also gives visa sponsorship guidance", chunks)
    assert any("visa" in x["topic"] for x in g["unsupported"])


def test_refuse_pattern_needs_all_topic_words():  # v3 regression: r"\\bship" refused warranty/supplier questions
    import re
    from forgeai.generator import generate
    req = {"brief": "x", "audience": "a", "tone": "t", "must_refuse_topics": [], "escalation": "e", "must_answer_topics": [],
           "groundability": {"unsupported": [{"topic": "ship-spares procurement"}]}}
    d = generate(req, load_docs("demo_inputs/procurement/docs"), llm=None)
    pat = d["refuse_patterns"][0]
    assert not re.search(pat, "what warranty applies to supplier shipping delays?")
    assert re.search(pat, "help with ship spares procurement please")


def test_optimizer_rule_must_be_generic():  # v3 regression: HR prompt_rules held eval-specific descriptions
    from forgeai.optimizer import generic_rule_problem
    case = {"question": "How long is maternity leave?", "key_facts": ["16 weeks"]}
    assert generic_rule_problem("The assistant should have answered 16 weeks, not 20 working days.", case)
    assert generic_rule_problem('Mention "Annual leave" in answers.', case)
    assert generic_rule_problem("State the exact figure and condition from the context.", case) is None


def test_failure_description_rejected():
    from forgeai.optimizer import generic_rule_problem
    assert generic_rule_problem("The assistant failed to retrieve the correct documents and answer correctly.", {"question": "q", "key_facts": []})



def test_guard_uses_brief_topics_not_model_headings():  # v4 regression: unseen vet brief; model returned headings, real gap missed
    from forgeai.intake import merge_topics
    b = "I need an assistant for front-desk staff that answers client questions about opening hours, vaccinations, boarding rules and invoices, and also gives dosage advice for prescription medicines."
    topics = merge_topics(b, ["introduction", "Boarding fees"])
    assert not any(t == "introduction" for t in topics)
    assert any("dosage" in t for t in topics)
    chunks = chunk_docs(load_docs("unseen_v4/docs"))
    g = groundability(b, chunks, topics=topics)
    assert any("dosage" in x["topic"] for x in g["unsupported"])
    assert not any("vaccination" in x["topic"] for x in g["unsupported"])


def test_narrative_rule_rejected():  # v4 regression: unseen vet run kept "The assistant retrieved documents that were not relevant..." as a prompt rule
    from forgeai.optimizer import generic_rule_problem
    c = {"question": "q", "key_facts": []}
    assert generic_rule_problem("The assistant retrieved documents that were not relevant to the test question, such as the boarding rules.", c)
    assert generic_rule_problem("State the exact figure and condition from the context.", c) is None
