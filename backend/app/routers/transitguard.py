"""
ABHAYA TransitGuard -- bus journey safety layer (spec section 31.3-31.9).

TransitGuard is the bus-specific implementation of ABHAYA's existing
continuous safety philosophy (section 24.1/25): it is NOT a separate
detection system. `/transitguard/check` reuses the EXACT SAME map-matching
(`RoadGraph`/nearest-edge) and risk-comparison (`RoadGraph.edge_risk_state`)
logic that `/routeguard/check` already uses for ride-hailing vehicles --
same real road graph, same tiered Normal / Level1-subtle / Level2-critical
response, same persistence-gated escalation. Only the bus-compliance
evidence layer (`/bus/safety-status`) is new, and it is explicitly
demo/placeholder data (see app/demo_bus_data.py) because no bus operator
publishes real per-vehicle telemetry.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import (ROUTEGUARD_LEVEL1_DEVIATION_M, ROUTEGUARD_LEVEL1_RISK_DELTA,
                         ROUTEGUARD_LEVEL2_PERSIST_SEC, ROUTEGUARD_LEVEL2_RISK_DELTA)
from app.data_loader import haversine_m
from app.db import get_session
from app.demo_bus_data import DEMO_BUS_FLEET, DEMO_DATA_SOURCE_STATUS
from app.graph import get_road_graph
from app.journey_store import load_journey, save_journey
from app.models import (BusEvidenceRecord, BusSafetyStatusRequest, BusSafetyStatusResponse,
                         SafetyState, TransitGuardCheckRequest, TransitGuardCheckResponse,
                         TransitStatus)

router = APIRouter()


def _map_match(rg, lat: float, lon: float):
    """Identical map-matching approach to routeguard.py: snap the live GPS
    fix to the nearest node of the real road graph, returning the edge it
    belongs to. Kept as its own copy (not imported from routeguard.py) so
    this router has no dependency on another feature's router module --
    only on the shared app.graph/app.risk_engine layer, per spec 24.1."""
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


def _bus_evidence(record: dict, now: float) -> dict[str, BusEvidenceRecord]:
    """Convert one demo bus fleet record into EvidenceRecord-style objects
    (spec 25: value/source/timestamp/confidence), clearly sourced as demo
    data. Confidence is fixed at a modest value because this is placeholder
    data, not a real sensor/operator feed with a measurable confidence."""
    def rec(factor: str, raw: object) -> BusEvidenceRecord:
        if isinstance(raw, bool):
            value = 1.0 if raw else 0.0
            raw_value = "compliant" if raw else "non_compliant"
        elif isinstance(raw, list):
            value = 1.0 if raw else 0.0
            raw_value = ", ".join(raw) if raw else "none_listed"
        else:
            value = 0.0
            raw_value = str(raw)
        return BusEvidenceRecord(
            factor=factor, value=value, raw_value=raw_value,
            source="demo_bus_fleet_records", timestamp=now, confidence=0.5,
        )

    return {
        "tracking": rec("tracking_active", record["tracking_active"]),
        "panic_button": rec("panic_button_functional", record["panic_button_functional"]),
        "visibility": rec("visibility_compliant", record["visibility_compliant"]),
        "lighting": rec("lighting_adequate", record["lighting_adequate"]),
        "authorised_stops": rec("authorised_stops", record["authorised_stops"]),
    }


@router.get("/bus/safety-status", response_model=BusSafetyStatusResponse)
def get_bus_safety_status(vehicle_id: str, operator: str | None = None, journey_id: str | None = None):
    now = time.time()
    record = DEMO_BUS_FLEET.get(vehicle_id)
    if record is None:
        return BusSafetyStatusResponse(
            vehicle_id=vehicle_id, operator=operator, route_name=None, found=False,
            overall_compliance_score=0.0, data_source_status=DEMO_DATA_SOURCE_STATUS,
            reason=(f"No demo compliance record for vehicle_id '{vehicle_id}'. "
                    f"Known demo vehicle_ids: {sorted(DEMO_BUS_FLEET.keys())}."),
        )

    evid = _bus_evidence(record, now)
    bool_checks = [record["tracking_active"], record["panic_button_functional"],
                   record["visibility_compliant"], record["lighting_adequate"]]
    score = sum(1 for b in bool_checks if b) / len(bool_checks)

    return BusSafetyStatusResponse(
        vehicle_id=vehicle_id, operator=record["operator"], route_name=record["route_name"],
        found=True, tracking=evid["tracking"], panic_button=evid["panic_button"],
        visibility=evid["visibility"], lighting=evid["lighting"],
        authorised_stops=evid["authorised_stops"], overall_compliance_score=score,
        data_source_status=DEMO_DATA_SOURCE_STATUS,
        reason=(f"{sum(1 for b in bool_checks if b)}/{len(bool_checks)} demo compliance "
                f"checks pass for {record['operator']} ({record['route_name']})."),
    )


@router.post("/transitguard/check", response_model=TransitGuardCheckResponse)
def post_transitguard_check(req: TransitGuardCheckRequest, session: Session = Depends(get_session)):
    rg = get_road_graph()
    now = req.current_time or time.time()
    expected_time = req.expected_time or now

    bus_score = None
    bus_status = None
    if req.include_bus_evidence:
        record = DEMO_BUS_FLEET.get(req.vehicle_id)
        bus_status = DEMO_DATA_SOURCE_STATUS
        if record is not None:
            bool_checks = [record["tracking_active"], record["panic_button_functional"],
                           record["visibility_compliant"], record["lighting_adequate"]]
            bus_score = sum(1 for b in bool_checks if b) / len(bool_checks)

    if rg.graph.number_of_edges() == 0:
        return TransitGuardCheckResponse(
            journey_id=req.journey_id, vehicle_id=req.vehicle_id, matched_segment_id=None,
            is_on_expected_route=True, deviation_distance_m=0.0, expected_segment_risk=None,
            actual_segment_risk=None, risk_delta=0.0, bus_compliance_score=bus_score,
            bus_data_source_status=bus_status, transit_state=SafetyState.NORMAL,
            response_level="normal", reason="No road network data available; cannot evaluate deviation.",
            evidence_ids=[],
        )

    # Real map-matching + real risk comparison -- identical approach to
    # /routeguard/check (app/routers/routeguard.py), applied to a bus's GPS.
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
    prior_ts = js.transit_status if js else None

    transit_state = SafetyState.NORMAL
    response_level = "normal"
    reason = "Bus is following the expected route; no meaningful risk change detected."

    materially_worse = risk_delta >= ROUTEGUARD_LEVEL1_RISK_DELTA
    deviated_far = dist >= ROUTEGUARD_LEVEL1_DEVIATION_M and not is_expected

    # Non-compliant bus safety evidence (e.g. no functional tracking/panic
    # button) is incorporated into the concern -- per spec 31.4, non-compliance
    # is surfaced transparently and feeds the journey-risk context, but is
    # never by itself proof of danger, same discipline as motion-only signals
    # in WalkGuard (spec 24.5/24.9).
    poorly_compliant = bus_score is not None and bus_score < 0.5

    if materially_worse or deviated_far:
        transit_state = SafetyState.LEVEL1_SUBTLE
        response_level = "level1_subtle_checkin"
        compliance_note = (
            f" Bus compliance evidence is also weak (score {bus_score:.2f})."
            if poorly_compliant else ""
        )
        reason = (
            f"Bus deviated onto a segment with risk delta {risk_delta:+.2f} "
            f"({dist:.0f}m from expected corridor). Discreet check-in requested."
            f"{compliance_note}"
        )
        now_ts = now
        if prior_ts and prior_ts.transit_state == SafetyState.LEVEL1_SUBTLE and prior_ts.level1_since:
            persisted = now_ts - prior_ts.level1_since
            if persisted >= ROUTEGUARD_LEVEL2_PERSIST_SEC and risk_delta >= ROUTEGUARD_LEVEL2_RISK_DELTA:
                transit_state = SafetyState.LEVEL2_CRITICAL
                response_level = "level2_critical_escalation"
                reason = (
                    f"Materially worse bus route persisted for {persisted:.0f}s with risk delta "
                    f"{risk_delta:+.2f} and no resolution; escalating per configured workflow."
                    f"{compliance_note}"
                )

    level1_since = prior_ts.level1_since if prior_ts else None
    if transit_state == SafetyState.NORMAL:
        level1_since = None
    elif level1_since is None:
        level1_since = now

    new_ts = TransitStatus(
        vehicle_id=req.vehicle_id, transit_state=transit_state, level1_since=level1_since,
        last_checked_at=now, last_matched_segment_id=matched_segment_id,
    )

    if js:
        js.current_lat, js.current_lon = req.current.lat, req.current.lon
        js.transit_status = new_ts
        save_journey(session, js)

    return TransitGuardCheckResponse(
        journey_id=req.journey_id, vehicle_id=req.vehicle_id, matched_segment_id=matched_segment_id,
        is_on_expected_route=is_expected, deviation_distance_m=dist,
        expected_segment_risk=expected_risk, actual_segment_risk=actual_risk,
        risk_delta=risk_delta, bus_compliance_score=bus_score, bus_data_source_status=bus_status,
        transit_state=transit_state, response_level=response_level, reason=reason,
        evidence_ids=evidence_ids,
    )
