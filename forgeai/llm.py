"""Small open-model backend (llama.cpp via llama-cpp-python, GGUF) with a disk cache.
Backend 'none' returns None so callers fall back to deterministic logic (baseline mode)."""
import hashlib
import json
import os
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def prompt(name, **kw):
    return (PROMPTS / name).read_text().format(**kw)


class LLM:
    def __init__(self, model_path=None, cache_path=None, n_ctx=2048, seed=7):
        self.model_path = model_path or os.environ.get("FORGE_MODEL")
        self.llm = None
        self.calls = 0
        self.cache_hits = 0
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache = {}
        if self.cache_path and self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text())
        if self.model_path and os.path.exists(self.model_path):
            from llama_cpp import Llama
            self.llm = Llama(model_path=self.model_path, n_ctx=n_ctx, verbose=False, n_threads=os.cpu_count() or 1, seed=seed)
        self.name = Path(self.model_path).name if self.llm else "none (deterministic baseline)"

    @property
    def available(self):
        return self.llm is not None

    def complete(self, user, system="You are a precise assistant.", max_tokens=160):
        if not self.llm:
            return None
        key = hashlib.sha256(json.dumps([self.name, system, user, max_tokens]).encode()).hexdigest()
        if key in self.cache:
            self.cache_hits += 1
            return self.cache[key]
        r = self.llm.create_chat_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens, temperature=0.0)
        out = r["choices"][0]["message"]["content"].strip()
        self.calls += 1
        self.cache[key] = out
        if self.cache_path:
            self.cache_path.write_text(json.dumps(self.cache))
        return out


def _parse_json(text):
    if not text:
        raise ValueError("empty model output")
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no JSON object in output")
    return json.loads(text[a:b + 1])


def ask_json(llm, stage, user, validate, max_tokens=220, system="You are a precise assistant. Reply with one JSON object only."):
    """Ask the model for JSON, validate it, try once more with a stricter instruction.
    Returns the validated dict or None. Every call is logged in llm.events (stage, ok, reason); nothing is repaired or invented."""
    if not hasattr(llm, "events"):
        llm.events = []
    if not llm.available:
        llm.events.append({"stage": stage, "ok": False, "reason": "no model loaded"})
        return None
    reason = ""
    for attempt in (1, 2):
        u = user if attempt == 1 else user + "\nYour previous reply was invalid (" + reason + "). Reply with ONLY the JSON object, nothing else."
        raw = llm.complete(u, system=system, max_tokens=max_tokens)
        try:
            obj = validate(_parse_json(raw))
            llm.events.append({"stage": stage, "ok": True, "attempts": attempt})
            return obj
        except Exception as e:  # invalid output is recorded, never silently repaired
            reason = str(e)[:120]
    llm.events.append({"stage": stage, "ok": False, "attempts": 2, "reason": reason, "raw": (raw or "")[:200]})
    return None


def ask_text(llm, stage, user, validate, max_tokens=120, system="You are a precise assistant."):
    """Free-text model call with validation and one retry that names the reason. Logged in llm.events; returns validated text or None."""
    if not hasattr(llm, "events"):
        llm.events = []
    if not llm.available:
        llm.events.append({"stage": stage, "ok": False, "reason": "no model loaded"})
        return None
    reason = ""
    for attempt in (1, 2):
        u = user if attempt == 1 else user + "\nYour previous reply was rejected: " + reason + ". Try again."
        raw = (llm.complete(u, system=system, max_tokens=max_tokens) or "").strip()
        try:
            out = validate(raw)
            llm.events.append({"stage": stage, "ok": True, "attempts": attempt})
            return out
        except Exception as e:
            reason = str(e)[:140]
    llm.events.append({"stage": stage, "ok": False, "attempts": 2, "reason": reason, "raw": raw[:200]})
    return None


def yes_no(llm, stage, question):
    r = ask_text(llm, stage, question + "\nAnswer with one word: YES or NO.", lambda s: s.strip().upper().rstrip(".").split()[0] if s.strip().upper().split()[0].rstrip(".") in ("YES", "NO") else (_ for _ in ()).throw(ValueError("answer must be YES or NO")), 4)
    return None if r is None else r.rstrip(".") == "YES"
