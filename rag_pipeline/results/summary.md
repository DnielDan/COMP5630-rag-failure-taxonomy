# Results summary

Questions: 113  ·  k = 5

## Main results

| System | Accuracy | Recall@5 | Hit@5 | # Failures |
|---|---|---|---|---|
| BM25 (classic) | 80.5% | 71.3% | 83.0% | 22 |
| Dense RAG (standard) | 75.2% | 55.9% | 67.0% | 28 |
| Dense + reranker | 76.1% | 61.2% | 72.3% | 27 |
| Query rewrite + reranker | 77.9% | 56.4% | 66.0% | 25 |

## Accuracy by question type

| System | Lookup | Multi-hop | Unanswerable | Ambiguous | Conflicting |
|---|---|---|---|---|---|
| BM25 (classic) | 100% | 56% | 100% | 45% | 72% |
| Dense RAG (standard) | 90% | 56% | 100% | 36% | 67% |
| Dense + reranker | 90% | 60% | 100% | 45% | 61% |
| Query rewrite + reranker | 88% | 68% | 100% | 36% | 72% |

## Failure distribution (counts)

| System | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| BM25 (classic) | 4 | 0 | 10 | 0 | 0 | 8 |
| Dense RAG (standard) | 8 | 2 | 12 | 0 | 0 | 6 |
| Dense + reranker | 7 | 1 | 12 | 0 | 0 | 7 |
| Query rewrite + reranker | 8 | 0 | 12 | 0 | 0 | 5 |

## Label agreement

- Human A vs Human B: kappa = 0.78 on 140 failures
- Human A vs LLM pre-label: kappa = 0.53 on 140 failures
- Human B vs LLM pre-label: kappa = 0.40 on 140 failures
- Final (adjudicated) label vs LLM pre-label: kappa = 0.40 on 140 failures (23 A/B disagreements resolved by checking the retrieved passages)
- Failures with a human label: 140/140; with a final label: 140/140
- Figures and failure counts use final_label (fallback: human_label_A, then llm_label)

## Corrections (data/corrections.json)

- Dropped 4 bad-gold questions: ambi-005, ambi-008, ambi-014, conf-013 (117 -> 113 questions)
- 22 answers the LLM judge marked wrong were judged correct by both annotators and counted as correct

| System | Accuracy (LLM judge, raw) | Accuracy (corrected) | Failures raw -> corrected |
|---|---|---|---|
| BM25 (classic) | 75.2% | 80.5% | 29 -> 22 |
| Dense RAG (standard) | 66.7% | 75.2% | 39 -> 28 |
| Dense + reranker | 66.7% | 76.1% | 39 -> 27 |
| Query rewrite + reranker | 71.8% | 77.9% | 33 -> 25 |
