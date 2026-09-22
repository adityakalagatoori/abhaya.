from __future__ import annotations

from fastapi import APIRouter

from app.models import SafetyInsightRequest, SafetyInsightResponse

router = APIRouter()


@router.post("/safety-insight", response_model=SafetyInsightResponse)
def post_safety_insight(req: SafetyInsightRequest):
    """
    Contract for the RAG/LLM agent (see app/models.py::SafetyInsightRequest
    docstring). This endpoint intentionally does NOT call an LLM: the RAG
    agent is expected to either (a) call this endpoint's logic as a library
    function after generating text and pass the result through, or more
    likely (b) this endpoint is replaced/extended by the RAG service which
    imports `route_context` + `retrieved_passages` in this exact shape.

    Until the RAG agent is wired in, we return a deterministic, template-based
    explanation built ONLY from the structured route_context and the supplied
    retrieved_passages -- never fabricated -- so the contract is testable
    end-to-end today.
    """
    ctx = req.route_context or {}
    passages = req.retrieved_passages or []

    total_risk = ctx.get("total_risk")
    segments = ctx.get("segments", [])
    high_risk_factors = ctx.get("high_risk_factors", [])

    sentences = []
    if total_risk is not None:
        sentences.append(f"Estimated cumulative risk for this route is {total_risk:.2f}.")
    if high_risk_factors:
        sentences.append("Contributing factors: " + ", ".join(high_risk_factors) + ".")
    elif segments:
        sentences.append(f"No single dominant risk factor identified across {len(segments)} segment(s).")

    grounded = len(passages) > 0
    if passages:
        cited = "; ".join(f"[{p.get('source','unknown')} @ {p.get('timestamp','?')}]" for p in passages[:3])
        sentences.append(f"Supporting context: {cited}.")
    else:
        sentences.append("No retrieved textual evidence was supplied for this request.")

    uncertainty = None
    if not grounded and total_risk is None:
        uncertainty = "Insufficient structured or retrieved evidence to produce a grounded explanation."

    explanation = " ".join(sentences) if sentences else "No context supplied."

    return SafetyInsightResponse(
        explanation=explanation, grounded=grounded, sources_used=passages,
        uncertainty_note=uncertainty,
    )
