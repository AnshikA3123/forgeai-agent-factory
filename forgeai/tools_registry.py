"""Tool registry: 4 tools. The generator attaches only the ones a brief needs."""
import ast
import json
import operator
import re
import urllib.request
from datetime import date

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}


def _ev(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in OPS:
        return OPS[type(n.op)](_ev(n.left), _ev(n.right))
    if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
        return OPS[type(n.op)](_ev(n.operand))
    raise ValueError("unsupported expression")


def calculator(expr):
    return _ev(ast.parse(expr.replace(",", "").replace("x", "*"), mode="eval").body)


def current_date():
    return date.today().isoformat()


def csv_lookup(rows, key):
    key = key.lower()
    return [r for r in rows if any(key == str(v).lower() for v in r.values())]


def http_api(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)["current_weather"]


# name -> (description, brief keyword triggers, needs_csv)
REGISTRY = {
    "csv_lookup": {"desc": "Exact lookup of a row in a CSV catalogue by part id / key.",
                   "triggers": [r"\bcatalog", r"\bprice", r"\bpart\b", r"\bsku\b", r"\blook ?up", r"\binventory", r"\bstock\b"],
                   "needs_csv": True},
    "calculator": {"desc": "Safe arithmetic on numbers.",
                   "triggers": [r"\bcalculat", r"\btotal", r"\bcost", r"\bquote", r"\border value", r"\bsum\b", r"\bcompute"],
                   "needs_csv": False},
    "http_api": {"desc": "Keyless public HTTP API (open-meteo current weather).",
                 "triggers": [r"\bweather", r"\bforecast", r"\bsea state", r"\bwind\b"], "needs_csv": False},
    "current_date": {"desc": "Today's date.",
                     "triggers": [r"\btoday", r"\bcurrent date", r"\bdays (left|until|since)", r"\bdeadline", r"\boverdue", r"\bexpir"],
                     "needs_csv": False},
}


def select_tools(brief, docs):
    has_csv = any(d["kind"] == "csv" for d in docs)
    chosen = []
    for name, t in REGISTRY.items():
        if t["needs_csv"] and not has_csv:
            continue
        if any(re.search(p, brief.lower()) for p in t["triggers"]):
            chosen.append(name)
    return chosen
