"""Tests for ABHAYA TransitGuard (spec section 31.3-31.9).

Reuses the same synthetic fixture graph as test_router.py's RouteGuard tests
(backend/tests/fixtures/) to prove /transitguard/check triggers Level 1/2
exactly like /routeguard/check does for a bus GPS trace that deviates into a
materially riskier real road segment -- because it is the same map-matching
and risk-comparison logic, just applied to a bus vehicle_id.
"""
from fastapi.testclient import TestClient


def _client():
    from app.db import init_db
    from app.main import app
    init_db()
    return TestClient(app)


def test_bus_safety_status_reports_demo_evidence_honestly():
    c = _client()
    r = c.get("/bus/safety-status", params={"vehicle_id": "DL1PC1234"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["tracking"]["source"] == "demo_bus_fleet_records"
    assert body["tracking"]["value"] == 1.0
    assert "DEMO_BUS_FLEET_DATA" in body["data_source_status"]
    assert body["overall_compliance_score"] == 1.0


def test_bus_safety_status_reports_non_compliant_demo_bus():
    c = _client()
    r = c.get("/bus/safety-status", params={"vehicle_id": "UP16XX9988"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["tracking"]["raw_value"] == "non_compliant"
    assert body["overall_compliance_score"] < 1.0
    assert "DEMO_BUS_FLEET_DATA" in body["data_source_status"]


def test_bus_safety_status_unknown_vehicle_is_honest_not_fabricated():
    c = _client()
    r = c.get("/bus/safety-status", params={"vehicle_id": "NOT_A_REAL_DEMO_BUS"})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is False
    assert body["overall_compliance_score"] == 0.0
    assert "DEMO_BUS_FLEET_DATA" in body["data_source_status"]


def test_transitguard_flags_deviation_into_riskier_segment_like_routeguard():
    """Same synthetic fixture as test_router.py's
    test_routeguard_flags_deviation_into_riskier_segment: a safety-weighted
    route around the risky row0 corridor is the expected route, then the
    live GPS jumps onto row0 itself (synthetic crime + broken streetlight),
    which must escalate exactly as RouteGuard does."""
    c = _client()
    route_resp = c.post("/route", json={
        "origin": {"lat": 21.1710, "lon": 72.8300},
        "destination": {"lat": 21.1710, "lon": 72.8320},
        "mode": "walk", "w_safety": 5.0, "w_time": 0.1, "w_infra": 3.0,
    }).json()
    expected_segments = [s["segment_id"] for s in route_resp["segments"]]

    check = c.post("/transitguard/check", json={
        "vehicle_id": "DL1PC1234",
        "expected_route_segment_ids": expected_segments,
        "current": {"lat": 21.1700, "lon": 72.8305},
    }).json()
    assert check["actual_segment_risk"] is not None
    assert check["transit_state"] in ("level1_subtle", "level2_critical")
    assert check["bus_compliance_score"] == 1.0  # DL1PC1234 is the fully-compliant demo bus


def test_transitguard_on_expected_route_stays_normal():
    c = _client()
    route_resp = c.post("/route", json={
        "origin": {"lat": 21.1710, "lon": 72.8300},
        "destination": {"lat": 21.1710, "lon": 72.8320},
        "mode": "walk", "w_safety": 5.0, "w_time": 0.1, "w_infra": 3.0,
    }).json()
    expected_segments = [s["segment_id"] for s in route_resp["segments"]]
    first_seg = route_resp["segments"][0]

    check = c.post("/transitguard/check", json={
        "vehicle_id": "DL1PC1234",
        "expected_route_segment_ids": expected_segments,
        "current": {"lat": first_seg["from_latlon"]["lat"], "lon": first_seg["from_latlon"]["lon"]},
    }).json()
    assert check["transit_state"] == "normal"
    assert check["response_level"] == "normal"


def test_transitguard_persists_to_level2_like_routeguard():
    """Reproduces the same Level-1-persists-then-escalates gating RouteGuard
    uses, via journey_id continuity, but through /transitguard/check."""
    import time as _time
    from app.config import ROUTEGUARD_LEVEL2_PERSIST_SEC

    c = _client()
    route_resp = c.post("/route", json={
        "origin": {"lat": 21.1710, "lon": 72.8300},
        "destination": {"lat": 21.1710, "lon": 72.8320},
        "mode": "walk", "w_safety": 5.0, "w_time": 0.1, "w_infra": 3.0,
    }).json()
    journey_id = route_resp["journey_id"]
    expected_segments = [s["segment_id"] for s in route_resp["segments"]]

    now = _time.time()
    first = c.post("/transitguard/check", json={
        "journey_id": journey_id, "vehicle_id": "UP16XX9988",
        "expected_route_segment_ids": expected_segments,
        "current": {"lat": 21.1700, "lon": 72.8305},
        "current_time": now,
    }).json()
    assert first["transit_state"] == "level1_subtle"

    later = now + ROUTEGUARD_LEVEL2_PERSIST_SEC + 5
    second = c.post("/transitguard/check", json={
        "journey_id": journey_id, "vehicle_id": "UP16XX9988",
        "expected_route_segment_ids": expected_segments,
        "current": {"lat": 21.1700, "lon": 72.8305},
        "current_time": later,
    }).json()
    assert second["transit_state"] == "level2_critical"
    # Non-compliant demo bus (UP16XX9988) should surface in the reason text
    assert "compliance" in second["reason"].lower()
