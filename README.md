# Where RAG Actually Breaks

COMP 5630 course project by Daniel Choi and Henry Naingshwe.

This is a failure taxonomy for retrieval-augmented question answering over the FastAPI documentation. We
compare four retrieval setups (BM25, dense, dense + cross-encoder reranker, and query rewriting) on 113
stress-test questions. Two annotators labeled every wrong answer with one of six failure types (R1–R6).

| Path | Contents |
|---|---|
| [`rag_pipeline/`](rag_pipeline/) | The full pipeline (steps 1–6), with its own README covering setup, run order and labeling rules |
| `rag_pipeline/data/` | Processed corpus, question set, corrections and the LLM response cache |
| `rag_pipeline/results/` | Run outputs, judged answers, human labels, summary tables and figures |
| [`final_deck/`](final_deck/) | Script that builds `RAG_Final_Presentation.pptx` from `results/summary.csv` |

## Reproduce

```bash
cd rag_pipeline
pip install -r requirements.txt
# skip step1: data/docs.jsonl is committed (FastAPI docs at the commit in data/corpus_meta.json);
# rerunning step1 would fetch the *latest* docs and change the corpus
python step2_index.py       # chunks + embeddings + FAISS index
python step4_run.py         # answers (served from data/llm_cache.jsonl, no API key needed)
python step5_judge.py
python step6_analyze.py     # tables + figures in results/
```

Every OpenAI call is cached in `rag_pipeline/data/llm_cache.jsonl`, so rerunning with the committed question set
reproduces the reported numbers without an API key. New questions or models need `OPENAI_API_KEY` in
`rag_pipeline/.env`. That file is never committed.
