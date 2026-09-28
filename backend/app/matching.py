"""
Fellow Traveller Matching / Journey Companion (spec 31.1, 31.2, 31.7, 31.9).

Companion Match = w1(Route Overlap) + w2(Time Overlap)
                 + w3(Meeting-Point Practicality) + w4(Verification/Trust Evidence)

"Match the journey, not the person" (31.2): every term below is computed
from real geometry/time math on the two journeys, reusing the same road
graph / haversine distance already used by app/graph.py and
app/data_loader.py -- never a fabricated or hand-picked score.

Privacy rule (31.2): this module never returns a candidate's exact
origin/home location. It only ever returns a *computed* meeting point and an
aggregate overlap percentage.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from app.data_loader import haversine_m
from app.graph import RoadGraph

# Default weights for the four terms of the Companion Match score (31.2).
# Kept as module-level constants (mirrors app/config.py::DEFAULT_WEIGHTS
# pattern used by the router) so they are visible/tunable in one place.
DEFAULT_COMPANION_WEIGHTS = {
    "w_route_overlap": 0.40,
    "w_time_overlap": 0.25,
    "w_meeting_practicality": 0.15,
    "w_verification": 0.20,
}

# A candidate whose route corridor never comes within this distance of the
# requester's route is not a "fellow traveller" for this trip at all (31.1:
# "searches only for users who have an overlapping journey corridor").
CORRIDOR_WIDTH_M = 250.0

ROUTE_SAMPLE_POINTS = 12
ASSUMED_WALK_SPEED_MPS = 1.35  # same default as app/graph.py::WALK_SPEED_MPS, used for the fallback duration estimate
MAX_TIME_WINDOW_OVERLAP_MINUTES_FOR_NORM = 60.0  # normalizes the time-overlap term into 0..1


def _route_key(origin, destination, mode, depart_time) -> tuple:
    # Bucket depart_time to the minute -- companion matching doesn't need
    # second-level precision, and this lets repeated calls for the same
    # journey within a request (there are several: overlap needs it once per
    # side, duration estimate needs it once per side too) hit the same cache
    # entry instead of computing an identical real route multiple times.
    return (round(origin[0], 6), round(origin[1], 6), round(destination[0], 6), round(destination[1], 6),
            mode, round(depart_time / 60.0))


def _route_and_duration(rg: RoadGraph, origin: tuple[float, float], destination: tuple[float, float],
                         mode: str, depart_time: float, cache: dict) -> tuple[list[tuple[float, float]], float]:
    """Computes real route geometry AND duration together in a SINGLE
    rg.route() call (previously done as two separate calls -- one from
    _sample_route_points, one from _estimate_duration_s -- for the exact
    same journey, doubling real routing cost for no reason), and memoizes
    the result in `cache` for the lifetime of one /companions/match request
    so the requester's own journey (looked up once per candidate in the
    matching loop) is only ever routed once, not once per candidate.
    Falls back to straight-line interpolation when no road network is
    loaded, so the overlap computation degrades gracefully instead of
    fabricating a path."""
    key = _route_key(origin, destination, mode, depart_time)
    if key in cache:
        return cache[key]

    if rg.graph.number_of_edges() > 0:
        result = rg.route(origin, destination, depart_time, mode, w_safety=0.0, w_time=1.0, w_infra=0.0)
        if result and result["edge_states"]:
            pts = [(rg.graph.nodes[result["edge_states"][0][0]]["lat"],
                     rg.graph.nodes[result["edge_states"][0][0]]["lon"])]
            for (_u, v, _rstate, _edata) in result["edge_states"]:
                pts.append((rg.graph.nodes[v]["lat"], rg.graph.nodes[v]["lon"]))
            duration = max(60.0, result["total_time_s"])
            cache[key] = (pts, duration)
            return cache[key]

    lat1, lon1 = origin
    lat2, lon2 = destination
    n = ROUTE_SAMPLE_POINTS
    pts = [(lat1 + (lat2 - lat1) * i / (n - 1), lon1 + (lon2 - lon1) * i / (n - 1)) for i in range(n)]
    d = haversine_m(*origin, *destination)
    duration = max(60.0, d / ASSUMED_WALK_SPEED_MPS)
    cache[key] = (pts, duration)
    return cache[key]


def _point_to_polyline_distance_m(pt: tuple[float, float], polyline: list[tuple[float, float]]) -> float:
    """Real haversine distance from `pt` to the nearest sampled point of
    `polyline`. Sampling the candidate's route at ROUTE_SAMPLE_POINTS (or
    real graph nodes, see _sample_route_points) keeps this a genuine
    point-to-route proximity check rather than an endpoint-only comparison."""
    return min(haversine_m(pt[0], pt[1], p[0], p[1]) for p in polyline)


def route_overlap(rg: RoadGraph, req_origin, req_dest, req_mode, req_time,
                   cand_origin, cand_dest, cand_mode, cand_time,
                   cache: dict, corridor_m: float = CORRIDOR_WIDTH_M):
    """Real geometric corridor overlap: fraction of the requester's sampled
    route points that fall within `corridor_m` of the candidate's sampled
    route. Returns (overlap_pct 0..100, list of the requester's points that
    were within the corridor -- used downstream to place a meeting point)."""
    req_pts, _req_dur = _route_and_duration(rg, req_origin, req_dest, req_mode, req_time, cache)
    cand_pts, _cand_dur = _route_and_duration(rg, cand_origin, cand_dest, cand_mode, cand_time, cache)
    if not req_pts or not cand_pts:
        return 0.0, []
    within = [p for p in req_pts if _point_to_polyline_distance_m(p, cand_pts) <= corridor_m]
    pct = 100.0 * len(within) / len(req_pts)
    return pct, within


def time_overlap_minutes(req_start: float, req_duration_s: float,
                          cand_start: float, cand_duration_s: float) -> float:
    """Real interval-overlap math between the requester's and candidate's
    [departure, departure+duration] windows."""
    req_end = req_start + req_duration_s
    cand_end = cand_start + cand_duration_s
    overlap_s = max(0.0, min(req_end, cand_end) - max(req_start, cand_start))
    return overlap_s / 60.0


def meeting_point_and_practicality(overlap_points: list[tuple[float, float]]):
    """A practical meeting point is placed at the centroid of the points
    where the two journey corridors actually overlap (not an arbitrary
    midpoint of origin/destination, and never either party's exact origin).
    Practicality (0..1) penalizes overlap regions that are geometrically
    spread out (haversine distance from the centroid), since a tight,
    compact overlap is easier to actually meet at."""
    if not overlap_points:
        return None, 0.0
    lat = sum(p[0] for p in overlap_points) / len(overlap_points)
    lon = sum(p[1] for p in overlap_points) / len(overlap_points)
    avg_spread_m = sum(haversine_m(lat, lon, p[0], p[1]) for p in overlap_points) / len(overlap_points)
    practicality = max(0.0, min(1.0, 1.0 - avg_spread_m / 1000.0))
    return (lat, lon), practicality


def verification_evidence_score(phone_verified: bool) -> float:
    """Real field on the traveller record (not inferred/fabricated): a
    phone-verified traveller scores materially higher on the trust term."""
    return 1.0 if phone_verified else 0.3


@dataclass
class CompanionMatchResult:
    route_overlap_pct: float
    time_overlap_minutes: float
    meeting_point: tuple[float, float]
    meeting_point_practicality: float
    verification_score: float
    match_score: float


def compute_companion_match(rg: RoadGraph,
                             req_origin, req_dest, req_mode: str, req_time: float,
                             cand_origin, cand_dest, cand_mode: str, cand_time: float,
                             phone_verified: bool,
                             weights: dict | None = None,
                             route_cache: dict | None = None) -> CompanionMatchResult | None:
    """Runs all four real terms of the Companion Match score (spec 31.2) for
    one requester/candidate pair. Returns None if the two journeys' route
    corridors never overlap at all (31.1: only overlapping-corridor
    candidates are surfaced).

    `route_cache`: pass the SAME dict across every candidate in one
    /companions/match request so the requester's own journey -- identical on
    every iteration of that loop -- is only ever routed once via the real
    road graph, not once per candidate. Defaults to a fresh dict (no caching
    across calls) so existing single-pair callers/tests keep working."""
    w = weights or DEFAULT_COMPANION_WEIGHTS
    cache = route_cache if route_cache is not None else {}

    overlap_pct, overlap_pts = route_overlap(rg, req_origin, req_dest, req_mode, req_time,
                                              cand_origin, cand_dest, cand_mode, cand_time, cache)
    if overlap_pct <= 0.0:
        return None

    _req_pts, req_duration = _route_and_duration(rg, req_origin, req_dest, req_mode, req_time, cache)
    _cand_pts, cand_duration = _route_and_duration(rg, cand_origin, cand_dest, cand_mode, cand_time, cache)
    t_overlap_min = time_overlap_minutes(req_time, req_duration, cand_time, cand_duration)

    meeting_point, practicality = meeting_point_and_practicality(overlap_pts)
    if meeting_point is None:
        return None

    verification_score = verification_evidence_score(phone_verified)

    match_score = (
        w["w_route_overlap"] * (overlap_pct / 100.0)
        + w["w_time_overlap"] * min(1.0, t_overlap_min / MAX_TIME_WINDOW_OVERLAP_MINUTES_FOR_NORM)
        + w["w_meeting_practicality"] * practicality
        + w["w_verification"] * verification_score
    )

    return CompanionMatchResult(
        route_overlap_pct=overlap_pct,
        time_overlap_minutes=t_overlap_min,
        meeting_point=meeting_point,
        meeting_point_practicality=practicality,
        verification_score=verification_score,
        match_score=match_score,
    )
