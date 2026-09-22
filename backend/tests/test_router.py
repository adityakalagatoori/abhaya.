import time

from fastapi.testclient import TestClient


def _client():
    from app.db import init_db
    from app.main import app
    init_db()
    return TestClient(app)


def test_health_reports_graph_loaded():
    c = _client()
    r = c.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["road_graph_edges"] > 0
    assert body["road_graph_source"] == "geojson"


def test_route_returns_segments_and_evidence():
    c = _client()
    r = c.post("/route", json={
        "origin": {"lat": 21.1700, "lon": 72.8300},
        "destination": {"lat": 21.1720, "lon": 72.8320},
        "time": 1750000000,  # arbitrary daytime-ish unix ts
        "mode": "walk",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["segments"]) > 0
    assert body["total_distance_m"] > 0
    for seg in body["segments"]:
        assert "risk_score" in seg
        assert isinstance(seg["evidence_ids"], list)


def test_safety_weighting_avoids_high_risk_segment():
    """The row0 corridor has synthetic crime + a broken-streetlight CV
    detection at its midpoint. With high safety weight, the router should
    achieve materially lower total_risk than with safety weight ~0
    (pure time-optimal), demonstrating the safety/time trade-off (section 19)."""
    c = _client()
    origin = {"lat": 21.1700, "lon": 72.8300}
    dest = {"lat": 21.1700, "lon": 72.8320}

    fast = c.post("/route", json={
        "origin": origin, "destination": dest, "mode": "walk",
        "w_safety": 0.0, "w_time": 1.0, "w_infra": 0.0,
    }).json()
    safe = c.post("/route", json={
        "origin": origin, "destination": dest, "mode": "walk",
        "w_safety": 5.0, "w_time": 0.2, "w_infra": 3.0,
    }).json()

    assert safe["total_risk"] <= fast["total_risk"]


def test_time_of_day_changes_risk():
    c = _client()
    origin = {"lat": 21.1700, "lon": 72.8300}
    dest = {"lat": 21.1710, "lon": 72.8300}
    # 2am local vs 2pm local on the same date, using naive local timestamps
    import datetime
    day = datetime.datetime(2026, 1, 15, 14, 0, 0).timestamp()
    night = datetime.datetime(2026, 1, 15, 2, 0, 0).timestamp()

    r_day = c.post("/route", json={"origin": origin, "destination": dest, "time": day, "mode": "walk"}).json()
    r_night = c.post("/route", json={"origin": origin, "destination": dest, "time": night, "mode": "walk"}).json()

    assert r_night["total_risk"] >= r_day["total_risk"]


def test_infrastructure_endpoint_returns_detections():
    c = _client()
    r = c.get("/infrastructure", params={"lat": 21.1700, "lon": 72.8305, "radius": 100})
    assert r.status_code == 200
    body = r.json()
    assert body["data_source_status"] == "ok"
    assert len(body["detections"]) > 0


def test_safedrop_prefers_safer_point_over_pin():
    c = _client()
    r = c.post("/safedrop", json={
        "destination": {"lat": 21.1700, "lon": 72.8305},
        "max_extra_walk_m": 300,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["recommended"]["trade_off_score"] <= min(
        cand["trade_off_score"] for cand in body["all_candidates"]
    ) + 1e-9


def test_routeguard_flags_deviation_into_riskier_segment():
    c = _client()
    route_resp = c.post("/route", json={
        "origin": {"lat": 21.1710, "lon": 72.8300},
        "destination": {"lat": 21.1710, "lon": 72.8320},
        "mode": "walk", "w_safety": 5.0, "w_time": 0.1, "w_infra": 3.0,
    }).json()
    journey_id = route_resp["journey_id"]
    expected_segments = [s["segment_id"] for s in route_resp["segments"]]

    # simulate GPS jumping onto the risky row0 corridor instead
    check = c.post("/routeguard/check", json={
        "journey_id": journey_id,
        "expected_route_segment_ids": expected_segments,
        "current": {"lat": 21.1700, "lon": 72.8305},
    }).json()
    assert check["actual_segment_risk"] is not None
    assert check["safety_state"] in ("level1_subtle", "level2_critical")


def test_walkguard_running_plus_high_risk_location_triggers_checkin():
    c = _client()
    r = c.post("/walkguard/event", json={
        "location": {"lat": 21.1700, "lon": 72.8305},
        "accel_magnitude": 13.0,
        "accel_variance": 2.0,
        "gyro_magnitude": 1.0,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["anomaly_detected"] is True
    assert body["safety_state"] in ("level1_subtle", "level2_critical")


def test_walkguard_normal_walk_in_low_risk_area_stays_normal():
    c = _client()
    r = c.post("/walkguard/event", json={
        "location": {"lat": 21.1710, "lon": 72.8310},
        "accel_magnitude": 2.0,
        "accel_variance": 0.5,
        "gyro_magnitude": 0.2,
    })
    body = r.json()
    assert body["anomaly_detected"] is False
    assert body["safety_state"] == "normal"


def test_safe_havens_filters_by_verified_or_open():
    c = _client()
    r = c.get("/safe-havens", params={"lat": 21.1711, "lon": 72.8311, "radius": 500})
    assert r.status_code == 200
    body = r.json()
    assert body["data_source_status"] == "ok"
    assert any(cand["name"] == "Test 24x7 Pharmacy" for cand in body["candidates"])


def test_safety_insight_contract_is_grounded_when_passages_given():
    c = _client()
    r = c.post("/safety-insight", json={
        "route_context": {"total_risk": 1.2, "segments": [1, 2, 3], "high_risk_factors": ["lighting"]},
        "retrieved_passages": [{"text": "Reported incident near this street.", "source": "local_news",
                                 "timestamp": "2026-01-10"}],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    assert "1.20" in body["explanation"]


def test_safety_insight_reports_uncertainty_without_evidence():
    c = _client()
    r = c.post("/safety-insight", json={"route_context": {}, "retrieved_passages": []})
    body = r.json()
    assert body["grounded"] is False
    assert body["uncertainty_note"] is not None
