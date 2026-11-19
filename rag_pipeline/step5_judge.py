"""Step 5 - Grade every answer (LLM judge), compute retrieval metrics, and PRE-label failures R1-R6.

Outputs
  results/judged.jsonl            every (system, question) with verdict + retrieval metrics + llm_label
  results/labels_for_review.csv   only the WRONG answers - open in Excel and fill human_label_A / human_label_B

Re-running never erases what you typed in the human_label_* / notes columns.
"""
import csv
import sys

from common import (DATA, FAILURE_LABELS, IDK, JUDGE_MODEL, RESULTS, RUNS, llm_json, pmap,
                    read_json, read_jsonl, write_jsonl)
from retrieval import Retriever

REVIEW_CSV = RESULTS / "labels_for_review.csv"
HUMAN_COLS = ["human_label_A", "human_label_B", "final_label", "notes"]

RUBRIC = {
    "lookup": "Correct if the system answer conveys the key fact(s) of the gold answer and makes no claim that "
              "contradicts it. Extra correct detail is fine. A refusal ('I don't know') is incorrect.",
    "multi_hop": "The gold answer combines two facts. Correct only if the system answer gets BOTH parts right. "
                 "Missing either part, or a refusal, is incorrect.",
    "unanswerable": "The documentation does NOT contain this answer. Correct ONLY if the system declines or says the "
                    "documentation doesn't cover it. Incorrect if it gives a substantive answer as if documented.",
    "ambiguous": "The question has two valid readings (both described in the gold answer). Correct if the system "
                 "asks for clarification, addresses more than one reading, or explicitly states which reading it "
                 "assumed and answers that reading correctly. Incorrect if it silently answers just one reading, "
                 "or contains factual errors, or refuses.",
    "conflicting": "The docs contain old/new or version-dependent guidance. Correct if the system gives the CURRENT "
                   "recommended approach from the gold answer (mentioning the older one is fine). Incorrect if it "
                   "presents the outdated approach as the answer without flagging it, or refuses.",
}

TAXONOMY = "\n".join(f"{k} - {v}" for k, v in FAILURE_LABELS.items())
TAXONOMY_DETAIL = """R1 Retrieval miss: the information needed is NOT in the retrieved passages at all.
R2 Retrieved, ignored: the needed info IS in the passages, but the answer doesn't use it (e.g. says "I don't know",
   or answers from general knowledge / an irrelevant passage).
R3 Right chunk, wrong answer: the answer uses the right passage but misreads, misstates or over-generalises it
   (includes silently picking one reading of an ambiguous question, or giving outdated guidance that IS in context).
R4 Hallucinated citation: the main error is that the answer's claim is attributed to a cited passage that does not
   say that (claim unsupported by its citation).
R5 No-answer overreach: the question is not answerable from the docs, but the system answered anyway.
R6 Multi-hop failure: the question needs facts from two places; the answer gets one part but fails to combine them
   (whether because only one part was retrieved or because it didn't synthesise).
OTHER: none of the above fits (explain)."""


def judge(row, q):
    out = llm_json([{"role": "user", "content": f"""You are grading an answer from a QA system over the FastAPI docs.
Question type: {q['type']}
Rubric: {RUBRIC[q['type']]}

QUESTION: {q['question']}
GOLD ANSWER: {q['gold_answer']}
{('NOTE: ' + q['note']) if q.get('note') else ''}
SYSTEM ANSWER: {row['answer']}

Return {{"verdict": "correct" | "incorrect", "reason": "<one sentence>"}}"""}], JUDGE_MODEL)
    return out.get("verdict", "incorrect").lower().strip() == "correct", out.get("reason", "")


def label(row, q, r, verdict_reason):
    gold = set(q["gold_chunks"])
    ctx = "\n\n".join(
        f"[{i + 1}]{' (GOLD SOURCE)' if cid in gold else ''} {r.by_id[cid]['text']}"
        for i, cid in enumerate(row["retrieved"]))
    out = llm_json([{"role": "user", "content": f"""A RAG system answered a FastAPI documentation question WRONGLY.
Classify the PRIMARY cause using this taxonomy:
{TAXONOMY_DETAIL}

Question type: {q['type']}
QUESTION: {q['question']}
GOLD ANSWER: {q['gold_answer']}
{('NOTE: ' + q['note']) if q.get('note') else ''}
WHY IT WAS GRADED WRONG: {verdict_reason}

RETRIEVED PASSAGES (numbers match the answer's citations; GOLD SOURCE marks the passage the question was written from,
but other passages may also contain the info):
{ctx}

SYSTEM ANSWER: {row['answer']}

Return {{"answer_in_context": "yes" | "partial" | "no", "label": "R1".."R6" | "OTHER", "reason": "<one sentence>"}}"""}],
        JUDGE_MODEL)
    lab = str(out.get("label", "OTHER")).upper().strip()
    in_ctx = str(out.get("answer_in_context", "")).lower().strip()

    # deterministic overrides so the taxonomy is applied consistently
    if q["type"] == "unanswerable":
        lab = "R5"
    elif in_ctx == "no":
        lab = "R1"
    elif q["type"] == "multi_hop" and in_ctx == "partial":
        lab = "R6"
    elif in_ctx == "yes" and IDK.lower()[:20] in row["answer"].lower():
        lab = "R2"
    if lab not in FAILURE_LABELS and lab != "OTHER":
        lab = "OTHER"
    return lab, in_ctx, out.get("reason", "")


def main():
    questions = {q["qid"]: q for q in read_json(DATA / "questions.json")}
    r = Retriever()
    systems = [s for s in sys.argv[1:] if not s.startswith("-")] or \
              [p.stem for p in sorted(RUNS.glob("*.jsonl"))]

    all_rows = []
    for s in systems:
        rows = [x for x in read_jsonl(RUNS / f"{s}.jsonl") if x["qid"] in questions]

        def process(row):
            q = questions[row["qid"]]
            gold = q["gold_chunks"]
            hits = len(set(gold) & set(row["retrieved"]))
            row["n_gold"] = len(gold)
            row["gold_hits"] = hits
            row["recall_at_k"] = hits / len(gold) if gold else None
            row["hit_at_k"] = (hits > 0) if gold else None
            row["correct"], row["judge_reason"] = judge(row, q)
            row["llm_label"] = row["answer_in_context"] = row["label_reason"] = ""
            if not row["correct"]:
                row["llm_label"], row["answer_in_context"], row["label_reason"] = label(row, q, r, row["judge_reason"])
            return row

        rows = pmap(process, rows, desc=f"judge [{s}]")
        acc = sum(x["correct"] for x in rows) / len(rows)
        print(f"  {s:13s} accuracy {acc:.1%}  ({sum(not x['correct'] for x in rows)} failures)")
        all_rows += rows

    write_jsonl(RESULTS / "judged.jsonl", all_rows)

    # ---- review CSV, preserving any human labels already entered
    existing = {}
    if REVIEW_CSV.exists():
        with open(REVIEW_CSV, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                existing[(row["system"], row["qid"])] = {c: row.get(c, "") for c in HUMAN_COLS}
    cols = ["system", "qid", "type", "question", "gold_answer", "answer", "gold_retrieved",
            "answer_in_context", "llm_label", "llm_reason", "judge_reason"] + HUMAN_COLS
    with open(REVIEW_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for x in all_rows:
            if x["correct"]:
                continue
            q = questions[x["qid"]]
            keep = existing.get((x["system"], x["qid"]), {})
            w.writerow({
                "system": x["system"], "qid": x["qid"], "type": x["type"], "question": x["question"],
                "gold_answer": q["gold_answer"], "answer": x["answer"],
                "gold_retrieved": f"{x['gold_hits']}/{x['n_gold']}", "answer_in_context": x["answer_in_context"],
                "llm_label": x["llm_label"], "llm_reason": x["label_reason"], "judge_reason": x["judge_reason"],
                **{c: keep.get(c, "") for c in HUMAN_COLS},
            })
    print(f"Wrote {REVIEW_CSV}  -> fill in human_label_A (and human_label_B on a shared subset for agreement)")


if __name__ == "__main__":
    main()
