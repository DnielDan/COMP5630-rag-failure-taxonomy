"""Step 2 - Chunk documents (~400 tokens, heading/code-fence aware) and build a FAISS index.

Outputs: data/chunks.jsonl, data/embeddings.npy, data/faiss.index
"""
import re

import numpy as np
import tiktoken

from common import CHUNK_OVERLAP, CHUNK_TOKENS, DATA, EMBED_MODEL, read_jsonl, write_jsonl

ENC = tiktoken.get_encoding("cl100k_base")


def ntok(s):
    return len(ENC.encode(s))


def blocks(text):
    """Split markdown into blocks (paragraphs / whole code fences), tracking the current heading path."""
    out, buf, in_code, headings = [], [], False, {}

    def flush():
        if buf:
            out.append((" > ".join(headings[k] for k in sorted(headings)), "\n".join(buf).strip()))
            buf.clear()

    for line in text.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            buf.append(line)
            if not in_code:
                flush()
            continue
        if in_code:
            buf.append(line)
            continue
        m = re.match(r"^(#{1,4})\s+(.+)", line)
        if m:
            flush()
            level = len(m.group(1))
            headings = {k: v for k, v in headings.items() if k < level}
            headings[level] = m.group(2).strip()
            continue
        if not line.strip():
            flush()
        else:
            buf.append(line)
    flush()
    return [(h, b) for h, b in out if b]


def split_long(text, limit):
    ids = ENC.encode(text)
    return [ENC.decode(ids[i:i + limit]) for i in range(0, len(ids), limit)]


def chunk_doc(doc):
    chunks, cur, cur_tok, cur_head = [], [], 0, ""

    def emit():
        if cur:
            chunks.append((cur_head, "\n\n".join(cur)))

    for head, block in blocks(doc["text"]):
        pieces = split_long(block, CHUNK_TOKENS) if ntok(block) > CHUNK_TOKENS else [block]
        for piece in pieces:
            t = ntok(piece)
            if cur and cur_tok + t > CHUNK_TOKENS:
                emit()
                # carry a small tail of the previous chunk for overlap
                tail = cur[-1] if ntok(cur[-1]) <= CHUNK_OVERLAP * 2 else ""
                cur, cur_tok = ([tail], ntok(tail)) if tail else ([], 0)
            if not cur:
                cur_head = head
            cur.append(piece)
            cur_tok += t
    emit()

    rows = []
    for i, (head, body) in enumerate(chunks):
        if ntok(body) < 25:  # skip crumbs
            continue
        section = f"{doc['title']} > {head}" if head and head != doc["title"] else doc["title"]
        rows.append({
            "chunk_id": f"{doc['doc_id']}#{i:03d}",
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "section": section,
            "text": f"[{section}]\n{body}",
            "n_tokens": ntok(body),
        })
    return rows


def main():
    import faiss
    from sentence_transformers import SentenceTransformer

    docs = read_jsonl(DATA / "docs.jsonl")
    chunks = [c for d in docs for c in chunk_doc(d)]
    write_jsonl(DATA / "chunks.jsonl", chunks)
    toks = [c["n_tokens"] for c in chunks]
    print(f"{len(docs)} docs -> {len(chunks)} chunks (mean {np.mean(toks):.0f} tok, max {max(toks)})")

    model = SentenceTransformer(EMBED_MODEL)
    emb = model.encode([c["text"] for c in chunks], batch_size=64, show_progress_bar=True,
                       normalize_embeddings=True).astype("float32")
    np.save(DATA / "embeddings.npy", emb)
    index = faiss.IndexFlatIP(emb.shape[1])  # cosine similarity on normalized vectors
    index.add(emb)
    faiss.write_index(index, str(DATA / "faiss.index"))
    print(f"FAISS index saved ({index.ntotal} vectors, dim {emb.shape[1]})")


if __name__ == "__main__":
    main()
