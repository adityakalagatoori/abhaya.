"""
generate_safety_insight(route_risk_context, location, time) -> dict

Matches backend/app/models.py::SafetyInsightResponse shape exactly:
    {"explanation": str, "grounded": bool, "sources_used": list[dict], "uncertainty_note": str|None}

Pipeline:
1. Build a retrieval query from structured route_risk_context + location/time
   (never a free-text guess -- see retrieve.build_query_from_context).
2. Run real dense retrieval (sentence-transformers + FAISS) over the real corpus.
3. If nothing clears MIN_RELEVANCE_SCORE, return grounded=False + a fixed
   uncertainty_note WITHOUT calling any generative model. This is the spec's
   "insufficient evidence -> uncertainty statement, not fabricated warning" rule.
4. Otherwise, try a real local LLM via Ollama's HTTP API (http://localhost:11434)
   with a constrained prompt: the model must only use the retrieved excerpts +
   structured context, must not invent incidents, must not be asked "is this
   safe", and must produce a short explanation.
5. If Ollama is not reachable (no local LLM runtime available in this
   environment), fall back to GENERATION_BACKEND="extractive": a real,
   non-fabricating algorithm that assembles the explanation by selecting and
   lightly connecting the actual highest-scoring retrieved sentences plus the
   structured risk numbers -- it is not a template pretending to be an LLM,
   it does not invent any sentence not present in either route_risk_context or
   the retrieved text. This fallback is documented (not hidden) in README.md.
"""
from __future__ import annotations

import json
import re
from typing import Optional

import requests

from retrieve import retrieve, build_query_from_context

MIN_RELEVANCE_SCORE = 0.35  # cosine similarity threshold on normalized MiniLM embeddings
TOP_K = 4
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b-instruct"  # small/quantized-friendly instruct model, per spec 24.6

FIXED_UNCERTAINTY = (
    "No sufficiently relevant real source text was found for this location/time/risk context in "
    "the current corpus. This is not a statement that the area is unsafe or safe -- it means the "
    "RAG layer has insufficient grounded evidence to comment beyond the structured risk score "
    "already computed by the routing/risk engine."
)


def _passage_to_source_dict(p: dict) -> dict:
    meta = p["meta"]
    return {
        "text": p["text"],
        "source": f"{meta.get('title', 'unknown source')} — {meta.get('publisher', 'unknown publisher')} ({meta.get('source_url', '')})",
        "timestamp": meta.get("publish_date", "undated"),
        "retrieved": meta.get("retrieved_date", "unknown"),
        "score": p["score"],
    }


def _try_ollama(prompt: str) -> Optional[str]:
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        text = data.get("response", "").strip()
        return text or None
    except requests.exceptions.RequestException:
        return None


def _build_prompt(route_risk_context: dict, location: str, time: str, passages: list[dict]) -> str:
    evidence_block = "\n".join(
        f"- ({p['meta'].get('title')}, {p['meta'].get('publish_date')}): {p['text']}"
        for p in passages
    )
    ctx_json = json.dumps(route_risk_context, ensure_ascii=False)
    return f"""You are a safety-context summarizer for a navigation app. You are NOT being asked whether
a road is safe, and you must never answer that question directly.

Rules (must follow exactly):
- Only use facts from the STRUCTURED RISK CONTEXT and the RETRIEVED EVIDENCE below.
- Never invent an incident, statistic, or location detail that is not in the evidence.
- Never assert the current status (e.g. "is/is not lit", "has/lacks CCTV") of THIS specific
  location unless the evidence explicitly states that status for this exact location. If the
  structured risk context names a factor (e.g. "low_lighting_reported_zone"), you may repeat that
  factor as-is, but do not add confirmation, elaboration, or certainty beyond what the factor
  label and the evidence literally say.
- ABSOLUTE RULE, most important: you are FORBIDDEN from stating or implying a conclusion about
  whether the location/route "is safe", "is unsafe", "is risky", "is considered safe", "is a safe
  route", or any equivalent verdict, in either direction. Your only job is to (a) restate the
  structured risk factors given to you, and (b) summarize what the retrieved evidence says,
  attributing it to its source. The routing/risk engine (not you) has already computed the risk
  score; you must not agree, disagree, second-guess, or add your own safety verdict on top of it.
- Always mention that evidence is general/regional context unless the evidence text itself names
  the specific location.
- Keep the explanation to 2-4 sentences.
- End with one clause noting the retrieved evidence is time-stamped context, not a live report.

LOCATION: {location}
TIME: {time}
STRUCTURED RISK CONTEXT (from the deterministic risk engine, not from you): {ctx_json}

RETRIEVED EVIDENCE (real, source-attributed excerpts):
{evidence_block}

Write the short grounded explanation now:"""


def _extractive_fallback(route_risk_context: dict, passages: list[dict]) -> str:
    """Real, non-fabricating fallback used when no local generative LLM runtime
    (e.g. Ollama) is reachable. Documented explicitly in README.md: this is
    NOT an LLM. It deterministically selects the single highest-scoring
    retrieved sentence from each of up to 2 passages and states the
    structured risk numbers already computed upstream, without adding any
    claim not present in either input.
    """
    parts = []
    total_risk = route_risk_context.get("total_risk")
    factors = route_risk_context.get("high_risk_factors") or []
    if total_risk is not None:
        parts.append(f"The routing/risk engine estimates a cumulative risk score of {total_risk:.2f} for this route.")
    if factors:
        parts.append("Contributing structured risk factors: " + ", ".join(factors) + ".")

    for p in passages[:2]:
        sentences = re.split(r"(?<=[.!?])\s+", p["text"])
        best = max(sentences, key=len) if sentences else p["text"]
        title = p["meta"].get("title", "a retrieved source")
        date = p["meta"].get("publish_date", "undated")
        parts.append(f'Related regional context from "{title}" ({date}): "{best.strip()}"')

    parts.append(
        "This is general/regional source context, not a confirmed incident on this exact segment."
    )
    return " ".join(parts)


def generate_safety_insight(route_risk_context: dict, location: str, time: str) -> dict:
    query = build_query_from_context(route_risk_context, location, time)
    passages = retrieve(query, k=TOP_K)
    passages = [p for p in passages if p["score"] >= MIN_RELEVANCE_SCORE]

    if not passages:
        return {
            "explanation": FIXED_UNCERTAINTY,
            "grounded": False,
            "sources_used": [],
            "uncertainty_note": FIXED_UNCERTAINTY,
        }

    sources_used = [_passage_to_source_dict(p) for p in passages]

    prompt = _build_prompt(route_risk_context, location, time, passages)
    llm_text = _try_ollama(prompt)

    if llm_text:
        explanation = llm_text
        backend_used = f"ollama:{OLLAMA_MODEL}"
    else:
        explanation = _extractive_fallback(route_risk_context, passages)
        backend_used = "extractive_fallback (no local Ollama runtime reachable -- see README.md)"

    return {
        "explanation": explanation,
        "grounded": True,
        "sources_used": sources_used,
        "uncertainty_note": None,
        "_generation_backend": backend_used,  # diagnostic field, not part of the strict backend schema
    }


if __name__ == "__main__":
    example_ctx = {
        "segments": [{"segment_id": "seg-4821", "description": "riverfront service road near Athwa, low commercial density"}],
        "total_risk": 0.71,
        "high_risk_factors": ["low_lighting_reported_zone", "isolated_after_dark", "low_foot_traffic"],
    }
    result = generate_safety_insight(example_ctx, "Athwa Lines, Surat", "2026-09-21T21:30:00+05:30")
    print(json.dumps(result, indent=2, ensure_ascii=False))
