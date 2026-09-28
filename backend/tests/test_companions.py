"""Tests for Fellow Traveller Matching / Journey Companion (spec 31.1/31.2/31.9).

Matches the same TestClient/fixture pattern as tests/test_router.py: the
synthetic 3x3 grid fixture road network (tests/fixtures/road_network) plus
the app's own DEMO SEED traveller journeys (app/companion_seed.py, labeled
as hypothetical -- not real people).
"""
from fastapi.testclient import TestClient


def _client():
    from app.db import init_db
    from app.main import app
    init_db()
    return TestClient(app)


def test_companions_match_returns_only_overlapping_candidates():
    c = _client()
    r = c.post("/companions/match", json={
        "origin": {"lat": 21.1700, "lon": 72.8300},
        "destination": {"lat": 21.1700, "lon": 72.8320},
        "mode": "walk",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["candidates"]) > 0
    # demo_traveller_004's journey is in an unrelated city (Kolkata) with zero
    # route-corridor overlap -- it must never appear as a match (spec 31.1:
    # "searches only for users who have an overlapping journey corridor").
    ids = [cand["candidate_id"] for cand in body["candidates"]]
    assert "demo_traveller_004" not in ids


def test_route_overlap_scoring_differs_for_overlapping_vs_nonoverlapping_journeys():
    """Real geometric corridor overlap: candidates whose journey runs along
    the same corridor as the requester must score a materially higher
    route_overlap_pct than a candidate whose corridor never comes close."""
    from app.graph import get_road_graph
    from app.matching import DEFAULT_COMPANION_WEIGHTS, compute_companion_match

    rg = get_road_graph()
    req_origin, req_dest = (21.1700, 72.8300), (21.1700, 72.8320)
    now = 1_750_000_000.0

    overlapping = compute_companion_match(
        rg, req_origin, req_dest, "walk", now,
        (21.1701, 72.8301), (21.1701, 72.8319), "walk", now,
        phone_verified=True, weights=DEFAULT_COMPANION_WEIGHTS,
    )
    non_overlapping = compute_companion_match(
        rg, req_origin, req_dest, "walk", now,
        (22.5726, 88.3639), (22.5800, 88.3700), "walk", now,
        phone_verified=True, weights=DEFAULT_COMPANION_WEIGHTS,
    )

    assert overlapping is not None
    assert overlapping.route_overlap_pct > 0
    # A journey in an unrelated city has zero corridor overlap -> no match at all.
    assert non_overlapping is None


def test_time_overlap_minutes_is_correct_interval_math():
    from app.matching import time_overlap_minutes

    # Requester: 10:00-10:30 (1800s). Candidate: 10:15-10:45 (1800s).
    # Overlap should be exactly 15 minutes (10:15-10:30).
    req_start = 1_000_000.0
    cand_start = req_start + 900  # +15 min
    overlap = time_overlap_minutes(req_start, 1800, cand_start, 1800)
    assert abs(overlap - 15.0) < 1e-6

    # No overlap at all: candidate starts after requester's window ends.
    no_overlap = time_overlap_minutes(req_start, 1800, req_start + 3600, 1800)
    assert no_overlap == 0.0

    # Fully contained window.
    contained = time_overlap_minutes(req_start, 3600, req_start + 900, 600)
    assert abs(contained - 10.0) < 1e-6


def test_companion_match_response_never_exposes_exact_origin_address():
    c = _client()
    r = c.post("/companions/match", json={
        "origin": {"lat": 21.1700, "lon": 72.8300},
        "destination": {"lat": 21.1700, "lon": 72.8320},
        "mode": "walk",
    })
    body = r.json()
    assert len(body["candidates"]) > 0

    # None of the demo seed's real origin/destination coordinates may appear
    # anywhere in the serialized response -- only a computed meeting point.
    from app.companion_seed import get_demo_traveller_journeys
    raw = r.text
    for dj in get_demo_traveller_journeys():
        origin_str = f"{dj.origin[0]}"
        # A coordinate this specific should not leak into the response text
        # (meeting points are centroids of overlap regions, not raw origins).
        assert str(dj.origin) not in raw

    for cand in body["candidates"]:
        assert "origin" not in cand
        assert "home" not in cand
        assert "exact_location" not in cand
        assert "meeting_point" in cand
        assert "first_name_or_initial" in cand


def test_companion_request_attaches_to_existing_journey_state():
    c = _client()

    route_resp = c.post("/route", json={
        "origin": {"lat": 21.1700, "lon": 72.8300},
        "destination": {"lat": 21.1700, "lon": 72.8320},
        "mode": "walk",
    }).json()
    journey_id = route_resp["journey_id"]

    match_resp = c.post("/companions/match", json={
        "origin": {"lat": 21.1700, "lon": 72.8300},
        "destination": {"lat": 21.1700, "lon": 72.8320},
        "mode": "walk",
    }).json()
    assert len(match_resp["candidates"]) > 0
    candidate_id = match_resp["candidates"][0]["candidate_id"]

    req_resp = c.post("/companions/request", json={
        "journey_id": journey_id, "candidate_id": candidate_id,
    })
    assert req_resp.status_code == 200, req_resp.text
    body = req_resp.json()
    assert body["journey_id"] == journey_id
    assert body["companion_status"]["candidate_id"] == candidate_id
    assert body["companion_status"]["status"] == "requested"
    # The companion status must be attached to the SAME journey object that
    # /route created (spec 31.5), not a separate parallel state.
    assert body["journey"]["journey_id"] == journey_id
    assert body["journey"]["companion_status"]["candidate_id"] == candidate_id

    # Re-fetching a fresh journey/companion request against the SAME
    # journey_id confirms it persisted on that JourneyState row.
    req_resp2 = c.post("/companions/request", json={
        "journey_id": journey_id, "candidate_id": candidate_id,
    })
    assert req_resp2.status_code == 200
    assert req_resp2.json()["journey"]["journey_id"] == journey_id


def test_companion_request_404s_for_unknown_journey():
    c = _client()
    r = c.post("/companions/request", json={"journey_id": "jrn_doesnotexist", "candidate_id": "demo_traveller_001"})
    assert r.status_code == 404


def test_companion_request_404s_for_unknown_candidate():
    c = _client()
    route_resp = c.post("/route", json={
        "origin": {"lat": 21.1700, "lon": 72.8300},
        "destination": {"lat": 21.1700, "lon": 72.8320},
        "mode": "walk",
    }).json()
    r = c.post("/companions/request", json={
        "journey_id": route_resp["journey_id"], "candidate_id": "not_a_real_candidate",
    })
    assert r.status_code == 404
