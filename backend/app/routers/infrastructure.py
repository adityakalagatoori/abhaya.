from __future__ import annotations

import time

from fastapi import APIRouter, Query

from app.graph import get_road_graph
from app.models import InfrastructureDetection, InfrastructureResponse
from app.risk_engine import point_risk

router = APIRouter()


@router.get("/infrastructure", response_model=InfrastructureResponse)
def get_infrastructure(lat: float = Query(...), lon: float = Query(...),
                        radius: float = Query(150.0, description="meters")):
    rg = get_road_graph()
    cv_hits = rg.cv_index.query_radius(lat, lon, radius)
    detections = []
    for h in cv_hits:
        ev = rg.get_evidence(h["evidence_id"])
        if ev is None:
            continue
        detections.append(InfrastructureDetection(
            evidence_id=ev.id, factor=ev.factor, value=ev.value, confidence=ev.confidence,
            lat=ev.lat, lon=ev.lon, timestamp=ev.timestamp, description=ev.description,
        ))

    rstate = point_risk(rg, lat, lon)
    status = rg.load_status.get("cv_infrastructure", "unknown")
    return InfrastructureResponse(
        lat=lat, lon=lon, radius_m=radius, detections=detections,
        infrastructure_score=rstate.factors.infrastructure_condition,
        data_source_status=status,
    )
