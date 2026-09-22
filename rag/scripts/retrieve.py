"""
Real dense retrieval over the FAISS index built by build_index.py.

retrieve(query, k) -> list of {text, meta, score} sorted by cosine similarity
(highest first). Uses the same sentence-transformers model used to build the
index, loaded once and cached at module level.
"""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = ROOT / "index"


@lru_cache(maxsize=1)
def _load():
    index = faiss.read_index(str(INDEX_DIR / "faiss.index"))
    chunks = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
    model_name = (INDEX_DIR / "model_name.txt").read_text(encoding="utf-8").strip()
    model = SentenceTransformer(model_name)
    return index, chunks, model


def retrieve(query: str, k: int = 5):
    index, chunks, model = _load()
    q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    scores, ids = index.search(q_emb, min(k, len(chunks)))
    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx == -1:
            continue
        c = chunks[idx]
        results.append({
            "text": c["text"],
            "meta": c["meta"],
            "score": float(score),
        })
    return results


def build_query_from_context(route_risk_context: dict, location: str, time: str) -> str:
    """Turn structured risk context + location/time into a retrieval query.

    Never free-text-guesses at "what might be happening" -- only uses the
    factual fields already present in route_risk_context, plus location/time.
    """
    parts = [location, time]
    factors = route_risk_context.get("high_risk_factors") or []
    parts.extend(factors)
    segments = route_risk_context.get("segments") or []
    for seg in segments[:3]:
        desc = seg.get("description") if isinstance(seg, dict) else None
        if desc:
            parts.append(desc)
    return " ".join(str(p) for p in parts if p)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Surat isolated road night lighting safety"
    for r in retrieve(q, k=5):
        print(f"[{r['score']:.3f}] {r['meta'].get('title')} ({r['meta'].get('publish_date')})")
        print("   ", r["text"][:200].replace("\n", " "), "...")
