"""Retrievers for the three systems under comparison.

  bm25          classic lexical baseline (Okapi BM25)
  dense         standard RAG: MiniLM embeddings + FAISS
  dense_rerank  dense top-20 re-scored by a cross-encoder, keep top-k   (the mitigation)
  rewrite       LLM rewrites the query first, then dense_rerank          (optional 2nd mitigation)
"""
import re
from functools import cached_property

import numpy as np

from common import DATA, EMBED_MODEL, GEN_MODEL, RERANK_MODEL, RERANK_POOL, TOP_K, llm, read_jsonl

_TOKEN = re.compile(r"[a-z0-9_]+")


def tokenize(s):
    return _TOKEN.findall(s.lower())


class Retriever:
    def __init__(self):
        self.chunks = read_jsonl(DATA / "chunks.jsonl")
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self.ids = [c["chunk_id"] for c in self.chunks]

    # lazily-loaded heavy components ------------------------------------
    @cached_property
    def embedder(self):
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(EMBED_MODEL)

    @cached_property
    def index(self):
        import faiss
        return faiss.read_index(str(DATA / "faiss.index"))

    @cached_property
    def embeddings(self):
        return np.load(DATA / "embeddings.npy")

    @cached_property
    def bm25_index(self):
        from rank_bm25 import BM25Okapi
        return BM25Okapi([tokenize(c["text"]) for c in self.chunks])

    @cached_property
    def reranker(self):
        from sentence_transformers import CrossEncoder
        return CrossEncoder(RERANK_MODEL)

    # retrieval methods -------------------------------------------------
    def bm25(self, q, k=TOP_K):
        scores = self.bm25_index.get_scores(tokenize(q))
        return [self.ids[i] for i in np.argsort(-scores)[:k]]

    def dense(self, q, k=TOP_K):
        v = self.embedder.encode([q], normalize_embeddings=True).astype("float32")
        _, idx = self.index.search(v, k)
        return [self.ids[i] for i in idx[0]]

    def dense_rerank(self, q, k=TOP_K, pool=RERANK_POOL):
        cands = self.dense(q, pool)
        scores = self.reranker.predict([(q, self.by_id[c]["text"]) for c in cands])
        return [cands[i] for i in np.argsort(-scores)[:k]]

    def rewrite_query(self, q):
        msg = [
            {"role": "system", "content": (
                "Rewrite the user's question into a precise search query for the FastAPI documentation. "
                "Expand abbreviations, name the relevant FastAPI concepts/classes, and keep it under 40 words. "
                "Output only the rewritten query.")},
            {"role": "user", "content": q},
        ]
        return llm(msg, GEN_MODEL).strip()

    def rewrite(self, q, k=TOP_K):
        return self.dense_rerank(self.rewrite_query(q), k)

    def retrieve(self, system, q, k=TOP_K):
        return getattr(self, system)(q, k)

    def neighbors(self, chunk_id, n=10):
        """Most similar chunks to a given chunk (used when building multi-hop/ambiguous questions)."""
        i = self.ids.index(chunk_id)
        sims = self.embeddings @ self.embeddings[i]
        return [(self.ids[j], float(sims[j])) for j in np.argsort(-sims)[1:n + 1]]


SYSTEMS = ["bm25", "dense", "dense_rerank", "rewrite"]
