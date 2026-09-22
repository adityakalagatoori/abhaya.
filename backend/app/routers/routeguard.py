from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import (ROUTEGUARD_LEVEL1_DEVIATION_M, ROUTEGUARD_LEVEL1_RISK_DELTA,
                         ROUTEGUARD_LEVEL2_PERSIST_SEC, ROUTEGUARD_LEVEL2_RISK_DELTA)
from app.data_loader import haversine_m
from app.db import get_session
from app.graph import get_road_graph
from app.journey_store import load_journey, save_journey
from app.models import RouteGuardCheckRequest, RouteGuardCheckResponse, SafetyState
from app.risk_engine import point_risk

router = APIRouter()


def _map_match(rg, lat: float, lon: float):
    """Map-match a live GPS fix to the nearest graph edge (real network,
    not a straight-line snap to an arbitrary point)."""
    best_edge, best_d = None, float("inf")
    for u, v, k, data in rg.graph.edges(keys=True, data=True):
        for node in (u, v):
            nd = rg.graph.nodes.get(node)
            if not nd or "lat" not in nd:
                continue
            d = haversine_m(lat, lon, nd["lat"], nd["lon"])
            if d < best_d:
                best_d, best_edge = d, (u, v, k, data)
    return best_edge, best_d


@router.post("/routeguard/check", response_model=RouteGuardCheckResponse)
def post_routeguard_check(req: RouteGuardCheckRequest, session: Session = Depends(get_session)):
    rg = get_road_graph()
    now = req.current_time or time.time()
    expected_time = req.expected_time or now

    if rg.graph.number_of_edges() == 0:
        return RouteGuardCheckResponse(
            journey_id=req.journey_id, matched_segment_id=None, is_on_expected_route=True,
            deviation_distance_m=0.0, expected_segment_risk=None, actual_segment_risk=None,
            risk_delta=0.0, safety_state=SafetyState.NORMAL, response_level="normal",
            reason="No road network data available; cannot evaluate deviation.", evidence_ids=[],
        )

    edge, dist = _map_match(rg, req.current.lat, req.current.lon)
    matched_segment_id = f"{edge[0]}->{edge[1]}" if edge else None
    is_expected = matched_segment_id in (req.expected_route_segment_ids or [])

    expected_risk = None
    if req.expected_route_segment_ids:
        expected_states = []
        for seg in req.expected_route_segment_ids:
            try:
                u, v = seg.split("->")
                if rg.graph.has_edge(u, v):
                    for k, edata in rg.graph.get_edge_data(u, v).items():
                        expected_states.append(rg.edge_risk_state(u, v, k, edata, expected_time).risk_score)
            except ValueError:
                continue
        if expected_states:
            expected_risk = sum(expected_states) / len(expected_states)

    actual_risk = None
    evidence_ids: list[str] = []
    if edge:
        u, v, k, edata = edge
        rstate = rg.edge_risk_state(u, v, k, edata, now)
        actual_risk = rstate.risk_score
        evidence_ids = rstate.evidence_ids

    risk_delta = (actual_risk - expected_risk) if (actual_risk is not None and expected_risk is not None) else 0.0

    js = load_journey(session, req.journey_id) if req.journey_id else None

    safety_state = SafetyState.NORMAL
    response_level = "normal"
    reason = "Vehicle is following the expected route; no meaningful risk change detected."

    materially_worse = risk_delta >= ROUTEGUARD_LEVEL1_RISK_DELTA
    deviated_far = dist >= ROUTEGUARD_LEVEL1_DEVIATION_M and not is_expected

    if materially_worse or deviated_far:
        safety_state = SafetyState.LEVEL1_SUBTLE
        response_level = "level1_subtle_checkin"
        reason = (
            f"Deviation onto a segment with risk delta {risk_delta:+.2f} "
            f"({dist:.0f}m from expected corridor). Discreet check-in requested."
        )
        now_ts = now
        if js and js.safety_state == SafetyState.LEVEL1_SUBTLE and js.level1_since:
            persisted = now_ts - js.level1_since
            if persisted >= ROUTEGUARD_LEVEL2_PERSIST_SEC and risk_delta >= ROUTEGUARD_LEVEL2_RISK_DELTA:
                safety_state = SafetyState.LEVEL2_CRITICAL
                response_level = "level2_critical_escalation"
                reason = (
                    f"Materially worse route persisted for {persisted:.0f}s with risk delta "
                    f"{risk_delta:+.2f} and no resolution; escalating per configured workflow."
                )
        if js:
            if js.safety_state != SafetyState.LEVEL1_SUBTLE:
                js.level1_since = now_ts
        else:
            pass

    if js:
        js.current_lat, js.current_lon = req.current.lat, req.current.lon
        js.safety_state = safety_state
        if safety_state == SafetyState.NORMAL:
            js.level1_since = None
        elif js.level1_since is None:
            js.level1_since = now
        save_journey(session, js)

    return RouteGuardCheckResponse(
        journey_id=req.journey_id, matched_segment_id=matched_segment_id,
        is_on_expected_route=is_expected, deviation_distance_m=dist,
        expected_segment_risk=expected_risk, actual_segment_risk=actual_risk,
        risk_delta=risk_delta, safety_state=safety_state, response_level=response_level,
        reason=reason, evidence_ids=evidence_ids,
    )
