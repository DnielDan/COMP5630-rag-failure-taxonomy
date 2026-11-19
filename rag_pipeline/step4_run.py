"""Step 4 - Run every question through each RAG system and record retrieval + answer.

  python step4_run.py                      # all systems
  python step4_run.py dense dense_rerank   # a subset

Writes results/runs/<system>.jsonl
"""
import re
import sys

from common import DATA, GEN_MODEL, IDK, RUNS, TOP_K, llm, pmap, read_json, write_jsonl
from retrieval import SYSTEMS, Retriever

GEN_SYSTEM = f"""You are a documentation assistant for the FastAPI web framework.
Answer the user's question using ONLY the numbered context passages provided.
- Cite every passage you rely on with its number in square brackets, e.g. [2] or [1][3].
- If the passages do not contain the answer, reply exactly: "{IDK}"
- Be concise: at most 120 words, plus a short code snippet only if essential."""


def build_prompt(question, passages):
    ctx = "\n\n".join(f"[{i + 1}] {p['text']}" for i, p in enumerate(passages))
    return [{"role": "system", "content": GEN_SYSTEM},
            {"role": "user", "content": f"CONTEXT:\n{ctx}\n\nQUESTION: {question}"}]


def run_system(r, system, questions):
    # retrieval is sequential (torch models + threads don't mix well); LLM calls are parallel
    if system == "rewrite":
        rewrites = pmap(lambda q: r.rewrite_query(q["question"]), questions, desc="rewrite queries")
        retrieved = [r.dense_rerank(rw, TOP_K) for rw in rewrites]
    else:
        rewrites = [None] * len(questions)
        retrieved = [r.retrieve(system, q["question"], TOP_K) for q in questions]

    def answer(i):
        q, ids = questions[i], retrieved[i]
        passages = [r.by_id[c] for c in ids]
        text = llm(build_prompt(q["question"], passages), GEN_MODEL).strip()
        cited_nums = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})
        cited = [ids[n - 1] for n in cited_nums if 1 <= n <= len(ids)]
        bad_cites = [n for n in cited_nums if not 1 <= n <= len(ids)]
        row = {"qid": q["qid"], "system": system, "type": q["type"], "question": q["question"],
               "retrieved": ids, "answer": text, "cited": cited, "invalid_citations": bad_cites}
        if rewrites[i]:
            row["rewritten_query"] = rewrites[i]
        return row

    rows = pmap(answer, range(len(questions)), desc=f"answer [{system}]")
    write_jsonl(RUNS / f"{system}.jsonl", rows)
    return rows


def main():
    systems = [s for s in sys.argv[1:] if not s.startswith("-")] or SYSTEMS
    questions = read_json(DATA / "questions.json")
    r = Retriever()
    print(f"{len(questions)} questions x {len(systems)} systems, generator = {GEN_MODEL}")
    for s in systems:
        rows = run_system(r, s, questions)
        idk = sum(IDK.lower()[:20] in x["answer"].lower() for x in rows)
        print(f"  {s:13s} done - {idk} 'I don't know' answers")


if __name__ == "__main__":
    main()
