# ABHAYA RAG Safety Insight — I/O Schema

This RAG service matches the **existing** backend contract at
`C:\Users\adity\Desktop\ieee-wls\backend\app\models.py`
(`SafetyInsightRequest` / `SafetyInsightResponse`) and
`C:\Users\adity\Desktop\ieee-wls\backend\app\routers\safety_insight.py`, rather than inventing a
new one. That router currently returns a deterministic, template-based explanation and explicitly
says it is meant to be replaced/extended by "the RAG service which imports `route_context` +
`retrieved_passages` in this exact shape." This package (`rag/`) is that RAG service.

## Existing backend Pydantic models (source of truth)

```python
class SafetyInsightRequest(BaseModel):
    route_context: dict          # e.g. {"segments":[...], "total_risk":..., "high_risk_factors":[...]}
    retrieved_passages: list[dict] = []   # [{"text":.., "source":.., "timestamp":.., "score":..}, ...]
    question: Optional[str] = None

class SafetyInsightResponse(BaseModel):
    explanation: str
    grounded: bool
    sources_used: list[dict]
    uncertainty_note: Optional[str] = None
```

`route_context` is produced upstream by `/route` or `/routeguard/check` and ultimately traces back
to `RiskState` / `RiskFactorBreakdown` / `EvidenceRecord` in `backend/app/models.py` — i.e. it is
never invented by the RAG layer, only consumed.

## What `rag/` adds

The backend explicitly does NOT retrieve or generate — it just forwards whatever
`retrieved_passages` it is given. `rag/scripts/generate.py` is the missing piece: given a
`route_context`-shaped dict plus a `location`/`time` description, it:

1. Builds a retrieval query from `route_context["high_risk_factors"]` + location/time strings.
2. Runs real embedding + FAISS similarity search over `rag/corpus/*.txt` (see `rag/index/`).
3. Converts the top matches into the exact `retrieved_passages` shape the backend expects:
   `{"text":..., "source":..., "timestamp":..., "score":...}`.
4. Calls the local generative model (Ollama, if present) with a constrained prompt to produce
   `explanation`, or falls back to an extractive/deterministic explanation (see README) if no
   generative runtime is available — never a fabricated LLM-style claim either way.
5. Returns a dict matching `SafetyInsightResponse` exactly, so the backend router's own template
   branch can be swapped for a call into this function with no schema change:

```python
from rag.scripts.generate import generate_safety_insight

result = generate_safety_insight(route_risk_context=req.route_context, location="Athwa Lines, Surat",
                                  time="2026-09-21T21:30:00+05:30")
return SafetyInsightResponse(**result)
```

## Guardrails (spec 6.5 / 24.6 / 19), enforced in `rag/scripts/generate.py`

1. The model is never prompted with "is this road safe?" The prompt frames the task as: "given
   this structured risk context and these retrieved real source excerpts, write a short grounded
   note; do not state anything not present in the excerpts or the structured context."
2. Retrieval below `MIN_RELEVANCE_SCORE` (cosine similarity threshold) yields zero passages, and
   the function short-circuits to `grounded=False` with a fixed `uncertainty_note` — the generative
   model is not called to "fill in" missing evidence.
3. Every passage returned in `sources_used` carries `source` (title/publisher/URL) and `timestamp`
   (original publish date + retrieval date), so the frontend can render retrieved text and
   generated explanation side by side per spec section 19.
4. The function only ever returns `explanation` text + sources; it never returns or overrides a
   `risk_score` or routing decision — those come solely from `route_context` (spec 6.5: "do not let
   it silently replace the routing logic").
