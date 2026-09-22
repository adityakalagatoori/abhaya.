"""
Chunk the real corpus in rag/corpus/*.txt and build a FAISS vector index using a
real local sentence-transformers embedding model (all-MiniLM-L6-v2, ~80MB, CPU-friendly).

Each corpus file has a small metadata header (SOURCE_URL, TITLE, PUBLISHER, AUTHOR,
PUBLISH_DATE, RETRIEVED_DATE, REGION, TOPIC) followed by "---" and the body text.
We split the body into paragraph-level chunks (real text, verbatim from the source,
no fabrication) and embed each chunk, keeping the metadata attached to every chunk
so retrieval can always cite source + date.

Usage:
    python build_index.py

Outputs:
    rag/index/chunks.json   -- list of {id, text, meta}
    rag/index/faiss.index   -- FAISS IndexFlatIP over normalized embeddings
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus"
INDEX_DIR = ROOT / "index"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

HEADER_FIELDS = [
    "SOURCE_URL", "TITLE", "PUBLISHER", "AUTHOR",
    "PUBLISH_DATE", "RETRIEVED_DATE", "REGION", "TOPIC",
]


def parse_corpus_file(path: Path):
    raw = path.read_text(encoding="utf-8")
    header_text, _, body = raw.partition("\n---\n")
    meta = {}
    for line in header_text.splitlines():
        for field in HEADER_FIELDS:
            prefix = f"{field}:"
            if line.strip().startswith(prefix):
                meta[field.lower()] = line.split(":", 1)[1].strip()
    meta["file"] = path.name

    # Chunk by paragraph (blank-line separated); merge very short paragraphs
    # with the next one so chunks stay semantically useful (~40-400 words).
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    chunks = []
    buf = ""
    for p in paragraphs:
        buf = (buf + " " + p).strip() if buf else p
        if len(buf.split()) >= 40:
            chunks.append(buf)
            buf = ""
    if buf:
        if chunks and len(buf.split()) < 20:
            chunks[-1] = chunks[-1] + " " + buf
        else:
            chunks.append(buf)
    return meta, chunks


def main():
    INDEX_DIR.mkdir(exist_ok=True)
    files = sorted(CORPUS_DIR.glob("*.txt"))
    if not files:
        raise SystemExit(f"No corpus files found in {CORPUS_DIR}")

    all_chunks = []
    for f in files:
        meta, chunks = parse_corpus_file(f)
        for i, c in enumerate(chunks):
            all_chunks.append({
                "id": f"{f.stem}::chunk{i}",
                "text": c,
                "meta": meta,
            })

    print(f"Loaded {len(files)} corpus files -> {len(all_chunks)} chunks")

    print(f"Loading embedding model {MODEL_NAME} (real local sentence-transformers model)...")
    model = SentenceTransformer(MODEL_NAME)

    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True, normalize_embeddings=True)
    embeddings = embeddings.astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product on normalized vectors == cosine similarity
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_DIR / "faiss.index"))
    (INDEX_DIR / "chunks.json").write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (INDEX_DIR / "model_name.txt").write_text(MODEL_NAME, encoding="utf-8")

    print(f"Wrote index for {len(all_chunks)} chunks (dim={dim}) to {INDEX_DIR}")


if __name__ == "__main__":
    main()
