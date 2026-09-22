"""
Point-based risk scoring shared by /infrastructure, /safedrop and
/safe-havens, so those endpoints reuse exactly the same evidence indices
and factor weights as the road-graph router (section 24.1 "one risk state,
many existing features" / section 11 "keep the score consistent between
main navigation and the Uber extension").
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from app.graph import RoadGraph
from app.models import RiskFactorBreakdown, RiskState


def point_risk(rg: RoadGraph, lat: float, lon: float, at_time: float | None = None) -> RiskState:
    at_time = at_time or time.time()
    evidence_ids: list[str] = []

    crime_hits = rg.crime_index.query_radius(lat, lon, 80.0)
    point_crime_factor = 0.0
    for h in crime_hits:
        point_crime_factor += h["severity"] / (1 + h["distance_m"] / 40.0)
        evidence_ids.append(h["evidence_id"])
    point_crime_factor = min(1.0, point_crime_factor)
    # Same real district-level crime baseline used by the road-graph router
    # (app/graph.py's edge_risk_state) -- kept consistent per spec section 11
    # ("keep the score consistent between the main navigation and the Uber
    # extension" / "use the same infrastructure evidence for routing,
    # SafeDrop and route-deviation evaluation").
    district_factor = rg.district_crime_factor(lat, lon)
    crime_factor = min(1.0, max(point_crime_factor, district_factor))

    cv_hits = rg.cv_index.query_radius(lat, lon, 60.0)
    infra_factor = 0.0
    activity_factor = 0.0
    for h in cv_hits:
        contrib = max(0.0, h["weight"]) * h["confidence"]
        reduction = max(0.0, -h["weight"]) * h["confidence"]
        infra_factor += contrib / (1 + h["distance_m"] / 30.0)
        activity_factor += reduction / (1 + h["distance_m"] / 30.0)
        evidence_ids.append(h["evidence_id"])
    infra_factor = min(1.0, infra_factor)
    activity_factor = min(1.0, activity_factor)

    night = rg.is_night(at_time)
    time_factor = 0.35 if night else 0.05
    if night and infra_factor > 0.3:
        time_factor += 0.15

    factors = RiskFactorBreakdown(
        crime_history=crime_factor, infrastructure_condition=infra_factor,
        activity_level=activity_factor, reports=0.0, time_of_travel=time_factor,
        nearby_safety_context=0.0,
    )
    risk_score = min(1.0, max(0.0,
        0.35 * factors.crime_history + 0.30 * factors.infrastructure_condition
        + 0.20 * factors.time_of_travel - 0.10 * factors.activity_level
    ))
    return RiskState(
        segment_id=f"point:{lat:.6f},{lon:.6f}", lat=lat, lon=lon, evaluated_for_time=at_time,
        factors=factors, risk_score=risk_score, evidence_ids=list(dict.fromkeys(evidence_ids)),
    )
