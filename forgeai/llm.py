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
