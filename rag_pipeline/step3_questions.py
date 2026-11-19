"""Step 3 - Generate the ~120-question stress-test set with an LLM, grounded in specific chunks.

Five stress types (see QUESTION_MIX in common.py):
  lookup        single fact from one chunk
  multi_hop     needs facts from two chunks on different pages
  unanswerable  plausible FastAPI question the docs do NOT answer (verified against retrieval)
  ambiguous     underspecified question with two valid readings in the corpus
  conflicting   old-vs-new / version-dependent guidance exists in the corpus

Writes data/questions.json.  REVIEW IT BY HAND: delete or fix bad items, then run step 4.
Refuses to overwrite an existing file unless --force (so hand edits are never lost).
"""
import random
import re
import sys

from common import (DATA, QGEN_MODEL, JUDGE_MODEL, QUESTION_MIX, SEED, IDK, llm_json, pmap,
                    read_jsonl, write_json)
from retrieval import Retriever

OUT = DATA / "questions.json"
OVERSAMPLE = 1.8
rng = random.Random(SEED)

SYS = ("You are building a test set for a retrieval-augmented QA system over the FastAPI web framework "
       "documentation. Questions must sound like a real developer asking, be self-contained (never say "
       "'the passage', 'the text', 'the example above', 'according to'), and must not copy long phrases "
       "verbatim. Respond in JSON only.")


def prose_tokens(text):
    no_code = re.sub(r"```.*?```", " ", text, flags=re.S)
    return len(no_code.split())


def content_chunks(chunks):
    return [c for c in chunks if c["n_tokens"] >= 120 and prose_tokens(c["text"]) >= 60]


def ask(prompt, tag=""):
    return llm_json([{"role": "system", "content": SYS}, {"role": "user", "content": prompt}],
                    QGEN_MODEL, temperature=0.4, tag=tag)


# ---------------------------------------------------------------- generators
def gen_lookup(c):
    out = ask(f"""Write ONE question whose answer is stated explicitly in this passage, with a 1-2 sentence answer.
The question should have one clear correct answer. If the passage has no suitable fact, return {{"ok": false}}.

PASSAGE:
{c['text']}

Return {{"ok": true, "question": "...", "answer": "..."}}""")
    if out.get("ok") and out.get("question"):
        return {"type": "lookup", "question": out["question"], "gold_answer": out["answer"],
                "gold_chunks": [c["chunk_id"]]}


def gen_multi_hop(pair):
    a, b = pair
    out = ask(f"""Write ONE question that can only be answered fully by COMBINING a fact from passage A with a fact
from passage B (e.g. how two features interact, or a question whose two parts are answered by different passages).
Someone holding only one of the passages must NOT be able to answer it fully.
If no natural question connects them, return {{"ok": false}}.

PASSAGE A:
{a['text']}

PASSAGE B:
{b['text']}

Return {{"ok": true, "question": "...", "answer": "...", "fact_from_A": "...", "fact_from_B": "..."}}""")
    if out.get("ok") and out.get("question"):
        return {"type": "multi_hop", "question": out["question"], "gold_answer": out["answer"],
                "gold_chunks": [a["chunk_id"], b["chunk_id"]],
                "note": f"A: {out.get('fact_from_A', '')} | B: {out.get('fact_from_B', '')}"}


def gen_ambiguous(pair):
    a, b = pair
    out = ask(f"""Write ONE short, underspecified question (the way a hurried developer types) that could reasonably
refer to EITHER passage A or passage B, where the correct answer DIFFERS depending on which one is meant.
If these passages don't support a genuinely ambiguous question, return {{"ok": false}}.

PASSAGE A:
{a['text']}

PASSAGE B:
{b['text']}

Return {{"ok": true, "question": "...", "reading_A": "...", "answer_A": "...", "reading_B": "...", "answer_B": "..."}}""")
    if out.get("ok") and out.get("question"):
        gold = (f"AMBIGUOUS. Reading 1 ({out.get('reading_A')}): {out.get('answer_A')} "
                f"Reading 2 ({out.get('reading_B')}): {out.get('answer_B')}")
        return {"type": "ambiguous", "question": out["question"], "gold_answer": gold,
                "gold_chunks": [a["chunk_id"], b["chunk_id"]]}


def gen_conflicting(pair):
    a, b = pair
    out = ask(f"""Look for CONFLICTING or VERSION-DEPENDENT guidance in these passages: an old vs. new way of doing
something, a deprecated parameter/feature and its replacement, Pydantic v1 vs v2 behaviour, Python-version-specific
syntax, etc. It may be within one passage or across the two.
If such a conflict exists, write ONE question whose naive answer depends on which guidance is followed.
The gold answer must give the CURRENT recommended approach and mention the older/alternative one.
If there is no real conflict, return {{"ok": false}}.

PASSAGE A:
{a['text']}

PASSAGE B:
{b['text']}

Return {{"ok": true, "question": "...", "answer": "...", "outdated_answer": "...", "uses_A": true, "uses_B": true}}""")
    if out.get("ok") and out.get("question"):
        gold = [x["chunk_id"] for x, used in ((a, out.get("uses_A", True)), (b, out.get("uses_B", True))) if used]
        return {"type": "conflicting", "question": out["question"], "gold_answer": out["answer"],
                "gold_chunks": gold or [a["chunk_id"]],
                "note": f"Outdated answer: {out.get('outdated_answer', '')}"}


def gen_unanswerable_candidates(titles, n):
    out = llm_json([{"role": "system", "content": SYS}, {"role": "user", "content": f"""
The documentation covers these pages:
{titles}

Write {n} realistic questions a FastAPI developer might ask that the FastAPI documentation does NOT answer.
Mix: features FastAPI doesn't have, exact benchmark numbers, third-party/cloud product specifics, configuration
of unrelated tools, release dates/roadmap, made-up-but-plausible parameter names. Phrase them confidently,
as if the answer exists (they should tempt a system into making something up). Keep them on-topic for web APIs.
Return {{"questions": ["...", ...]}}"""}], QGEN_MODEL, temperature=0.8)
    return out.get("questions", [])


def verify_unanswerable(args):
    q, ctx = args
    out = llm_json([{"role": "user", "content": f"""Can the following question be answered (fully or mostly) from
the context below? Be strict: answer true if the context contains the information.

QUESTION: {q}

CONTEXT:
{ctx}

Return {{"answerable": true|false}}"""}], JUDGE_MODEL)
    return not out.get("answerable", True)


# ---------------------------------------------------------------- pairing helpers
def related_pairs(r, pool, n, lo, hi, cross_doc=True):
    pairs, seen = [], set()
    cand = pool[:]
    rng.shuffle(cand)
    pool_ids = {c["chunk_id"] for c in pool}
    for a in cand:
        nbrs = [(cid, s) for cid, s in r.neighbors(a["chunk_id"], 25)
                if lo <= s <= hi and cid in pool_ids
                and (not cross_doc or r.by_id[cid]["doc_id"] != a["doc_id"])]
        if not nbrs:
            continue
        b_id = rng.choice(nbrs[:5])[0]
        key = tuple(sorted((a["chunk_id"], b_id)))
        if key in seen:
            continue
        seen.add(key)
        pairs.append((a, r.by_id[b_id]))
        if len(pairs) >= n:
            break
    return pairs


def take(results, n):
    out, seen = [], set()
    for x in results:
        if x and x["question"].strip().lower() not in seen:
            seen.add(x["question"].strip().lower())
            out.append(x)
        if len(out) >= n:
            break
    return out


def main():
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT} exists (may contain hand edits). Re-run with --force to regenerate.")

    r = Retriever()
    pool = content_chunks(r.chunks)
    print(f"{len(pool)} content chunks eligible for question generation")
    qs = []

    # lookup: one chunk per page where possible
    n = QUESTION_MIX["lookup"]
    by_doc = {}
    for c in rng.sample(pool, len(pool)):
        by_doc.setdefault(c["doc_id"], c)
    cands = list(by_doc.values())[: int(n * OVERSAMPLE)]
    qs += take(pmap(gen_lookup, cands, desc="lookup"), n)

    # multi-hop: related chunks from different pages
    n = QUESTION_MIX["multi_hop"]
    qs += take(pmap(gen_multi_hop, related_pairs(r, pool, int(n * OVERSAMPLE), 0.45, 0.80), desc="multi_hop"), n)

    # ambiguous: highly similar chunks from different pages
    n = QUESTION_MIX["ambiguous"]
    qs += take(pmap(gen_ambiguous, related_pairs(r, pool, int(n * OVERSAMPLE * 1.3), 0.60, 0.92), desc="ambiguous"), n)

    # conflicting: chunks with version / deprecation language + a close neighbour (same page allowed)
    n = QUESTION_MIX["conflicting"]
    kw = re.compile(r"deprecat|pydantic v1|pydantic v2|older version|previous version|before fastapi|no longer|"
                    r"legacy|old way|on_event|lifespan|regex=|python 3\.(?:8|9)|annotated|instead of", re.I)
    conf_pool = [c for c in r.chunks if kw.search(c["text"]) and c["n_tokens"] >= 80]
    print(f"{len(conf_pool)} chunks mention version/deprecation language")
    pairs = related_pairs(r, conf_pool, int(n * OVERSAMPLE * 1.5), 0.35, 0.95, cross_doc=False)
    conf = take(pmap(gen_conflicting, pairs, desc="conflicting"), n)
    if len(conf) < n:
        print(f"  WARNING: only {len(conf)} conflicting questions found (target {n})")
    qs += conf

    # unanswerable: generate, then keep only those retrieval can't answer
    n = QUESTION_MIX["unanswerable"]
    titles = "\n".join(sorted({c["title"] for c in r.chunks}))
    cands = gen_unanswerable_candidates(titles, int(n * 2.2))
    ctxs = []
    for q in cands:
        ids = list(dict.fromkeys(r.dense_rerank(q, 5) + r.bm25(q, 5)))
        ctxs.append((q, "\n\n---\n\n".join(r.by_id[i]["text"] for i in ids)))
    keep = pmap(verify_unanswerable, ctxs, desc="verify unanswerable")
    unans = [{"type": "unanswerable", "question": q, "gold_answer": IDK, "gold_chunks": []}
             for q, ok in zip(cands, keep) if ok][:n]
    if len(unans) < n:
        print(f"  WARNING: only {len(unans)} verified unanswerable questions (target {n})")
    qs += unans

    counters = {}
    for q in qs:
        counters[q["type"]] = counters.get(q["type"], 0) + 1
        q["qid"] = f"{q['type'][:4]}-{counters[q['type']]:03d}"
    qs = [{"qid": q.pop("qid"), **q} for q in qs]
    write_json(OUT, qs)
    print(f"Saved {len(qs)} questions to {OUT}: {counters}")
    print("Next: skim data/questions.json, delete/fix bad questions, then run step4_run.py")


if __name__ == "__main__":
    main()
