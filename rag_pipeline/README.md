# Where RAG Actually Breaks — pipeline

A RAG system over the FastAPI documentation, a 120-question stress test, and an LLM-judged failure taxonomy
(R1–R6) pre-labeled for human review. The pipeline compares four retrieval setups.

| System | Role | What it does |
|---|---|---|
| `bm25` | classic baseline | Okapi BM25 lexical retrieval, top-5 |
| `dense` | standard RAG | MiniLM-L6 embeddings + FAISS, top-5 |
| `dense_rerank` | mitigation (newest) | dense top-20, cross-encoder rerank to top-5 |
| `rewrite` | mitigation 2 | LLM rewrites the query, then `dense_rerank` |

All systems use the same generator (`gpt-4o-mini`), the same prompt and the same k=5.

## Setup (already done on this machine)

```powershell
pip install -r requirements.txt
$env:OPENAI_API_KEY = "sk-..."          # needed for steps 3-5
```

## Run

```powershell
python step1_ingest.py        # DONE: 121 FastAPI doc pages -> data/docs.jsonl
python step2_index.py         # DONE: 737 chunks (~400 tok), FAISS index
python step3_questions.py     # ~120 questions -> data/questions.json   (~3-5 min)
#   >>> skim data/questions.json, delete/fix bad items <<<
python step4_run.py           # 4 systems x 120 questions -> results/runs/   (~5 min)
python step5_judge.py         # grade + pre-label failures -> results/labels_for_review.csv
#   >>> open the CSV in Excel, fill human_label_A (and human_label_B on a shared ~30 rows) <<<
python step6_analyze.py       # tables, figures, examples -> results/
```

* Every LLM call is cached in `data/llm_cache.jsonl`, so re-running a step costs nothing. Run step 6 again after
  editing labels.
* Step 3 will not overwrite your edited `questions.json` unless you pass `--force`.
* Step 5 keeps anything already typed in the `human_label_*` and `notes` columns.
* If you edit `questions.json` after step 4, rerun steps 4–6.
* To change models: `$env:RAG_GEN_MODEL="..."`, `$env:RAG_JUDGE_MODEL="..."`, `$env:RAG_QGEN_MODEL="..."`.
  Defaults: gpt-4o-mini answers; gpt-4o writes questions and judges. A stronger judge than the system under test
  is deliberate. Estimated total cost is about $1–3.

## Labeling rules (human_label_A / human_label_B)

Use R1–R6 or OTHER. Label the **primary** cause:

| Label | Meaning |
|---|---|
| R1 Retrieval miss | the needed info is not in any retrieved passage |
| R2 Retrieved, ignored | the info is in the passages, but the answer doesn't use it (e.g. says "I don't know") |
| R3 Right chunk, wrong answer | the answer uses the right passage but misreads it (includes silently picking one reading of an ambiguous question, or giving outdated guidance) |
| R4 Hallucinated citation | the claim is attributed to a cited passage that doesn't say it |
| R5 No-answer overreach | the question is unanswerable, but the system answered anyway |
| R6 Multi-hop failure | the answer gets one part of a two-part question but doesn't combine both |

For agreement: Daniel fills `human_label_A` and Henry fills `human_label_B` on the same ~30 rows
(e.g. the first 30 `dense` rows). Step 6 reports Cohen's kappa between the two humans, and between human and LLM.

## Outputs for the slides

* `results/summary.md` — main results table, accuracy by question type, failure counts, kappa
* `results/figures/fig1_accuracy_recall.png` — accuracy and recall@5 per system
* `results/figures/fig2_failure_distribution.png` — **headline chart**: failure types per system (before/after)
* `results/figures/fig3_type_x_failure.png` — question type × failure type heatmap (dense baseline)
* `results/figures/fig4_accuracy_by_type.png` — accuracy per question type per system
* `results/examples.md` — one real example per failure type, for the taxonomy slide

## Metrics

* **Accuracy**: an LLM judge (gpt-4o) grades each answer with a type-specific rubric (see `step5_judge.py`).
* **Recall@5**: the fraction of a question's gold source chunk(s) that appear in the top 5.
  Unanswerable questions are excluded.
* **Hit@5**: whether at least one gold chunk was retrieved.
* Corpus: FastAPI `docs/en/docs` at the commit recorded in `data/corpus_meta.json`. Changelog, people and
  reference stub pages are excluded.
