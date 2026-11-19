"""Shared config + helpers: paths, cached OpenAI calls, JSON I/O, parallel map."""
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

try:  # Windows consoles default to cp1252 and choke on emoji in the docs
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RUNS = RESULTS / "runs"
FIG = RESULTS / "figures"
for _d in (DATA, RESULTS, RUNS, FIG):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- .env (OPENAI_API_KEY=sk-...)
_ENV = ROOT / ".env"
if _ENV.exists():
    for _line in _ENV.read_text(encoding="utf-8-sig").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

# ---------------------------------------------------------------- config
# Models are overridable via env vars, e.g.  $env:RAG_GEN_MODEL="gpt-4.1-mini"
GEN_MODEL = os.getenv("RAG_GEN_MODEL", "gpt-4o-mini")      # answers questions (system under test)
QGEN_MODEL = os.getenv("RAG_QGEN_MODEL", "gpt-4o")         # writes the question set
JUDGE_MODEL = os.getenv("RAG_JUDGE_MODEL", "gpt-4o")       # grades + pre-labels failures

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

CHUNK_TOKENS = 400       # target chunk size (proposal: 300-500)
CHUNK_OVERLAP = 60       # tokens of overlap carried into next chunk
TOP_K = 5                # passages given to the LLM
RERANK_POOL = 20         # candidates the cross-encoder re-scores
SEED = 5630

# question-set composition (sums to 120)
QUESTION_MIX = {
    "lookup": 40,
    "multi_hop": 25,
    "unanswerable": 20,
    "ambiguous": 15,
    "conflicting": 20,
}

FAILURE_LABELS = {
    "R1": "Retrieval miss",
    "R2": "Retrieved, ignored",
    "R3": "Right chunk, wrong answer",
    "R4": "Hallucinated citation",
    "R5": "No-answer overreach",
    "R6": "Multi-hop failure",
}

IDK = "I don't know based on the provided documentation."

# ---------------------------------------------------------------- json io
def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write_jsonl(p, rows):
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- llm (cached)
_CACHE_PATH = DATA / "llm_cache.jsonl"
_cache = None
_lock = threading.Lock()
_client = None


def _get_client():
    global _client
    if _client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit(
                "OPENAI_API_KEY is not set.\n"
                '  PowerShell:  $env:OPENAI_API_KEY = "sk-..."\n'
                '  bash:        export OPENAI_API_KEY="sk-..."'
            )
        from openai import OpenAI
        _client = OpenAI()
    return _client


def _load_cache():
    global _cache
    if _cache is None:
        _cache = {}
        if _CACHE_PATH.exists():
            with open(_CACHE_PATH, encoding="utf-8") as f:
                for line in f:
                    try:
                        row = json.loads(line)
                        _cache[row["k"]] = row["v"]
                    except Exception:
                        pass
    return _cache


def llm(messages, model, json_mode=False, temperature=0.0, tag=""):
    """Chat completion with an on-disk cache so re-runs cost nothing.
    `tag` lets you force a distinct cache entry (e.g. for retries with a new sample)."""
    if json_mode and not any("json" in m["content"].lower() for m in messages):
        # the API rejects json_object mode unless the prompt mentions JSON
        messages = [{"role": "system", "content": "Respond with a single JSON object."}] + list(messages)
    cache = _load_cache()
    key = hashlib.sha256(
        json.dumps([model, messages, json_mode, temperature, tag], sort_keys=True).encode()
    ).hexdigest()
    if key in cache:
        return cache[key]

    client = _get_client()
    kwargs = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    last = None
    for attempt in range(6):
        try:
            resp = client.chat.completions.create(**kwargs)
            out = resp.choices[0].message.content or ""
            break
        except Exception as e:  # rate limits, transient errors, unsupported params
            last = e
            msg = str(e).lower()
            if "temperature" in msg and "temperature" in kwargs:
                kwargs.pop("temperature")  # some models only allow the default
                continue
            if any(s in msg for s in ("api key", "authentication", "model_not_found", "no credits", "quota", "per day")):
                raise
            time.sleep(min(2 ** attempt, 30))
    else:
        raise last

    with _lock:
        cache[key] = out
        with open(_CACHE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"k": key, "v": out}, ensure_ascii=False) + "\n")
    return out


def llm_json(messages, model, temperature=0.0, tag=""):
    raw = llm(messages, model, json_mode=True, temperature=temperature, tag=tag)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else {}


def pmap(fn, items, workers=8, desc=""):
    """Parallel map preserving order, with a progress bar."""
    items = list(items)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(tqdm(ex.map(fn, items), total=len(items), desc=desc))
