from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from app.data_loader import haversine_m
from app.graph import get_road_graph
from app.models import LatLon, SafeDropCandidateScored, SafeDropRequest, SafeDropResponse
from app.risk_engine import point_risk

router = APIRouter()

WALK_PENALTY_PER_M = 0.0015  # trade-off: extra walking distance vs risk reduction (section 24.7)


def _generate_candidates(rg, dest_lat: float, dest_lon: float, max_extra_walk_m: float):
    """Real candidate generation: road graph nodes within radius (actual
    street junctions/points on the network) rather than arbitrary offsets."""
    candidates = []
    for n, data in rg.graph.nodes(data=True):
        if "lat" not in data:
            continue
        d = haversine_m(dest_lat, dest_lon, data["lat"], data["lon"])
        if 0 < d <= max_extra_walk_m:
            candidates.append((data["lat"], data["lon"], f"road_node:{n}"))
    return candidates


@router.post("/safedrop", response_model=SafeDropResponse)
def post_safedrop(req: SafeDropRequest):
    rg = get_road_graph()
    at_time = req.time or time.time()
    dest = req.destination

    if req.candidates:
        raw_candidates = [(c.lat, c.lon, c.label or f"candidate_{i}") for i, c in enumerate(req.candidates)]
    else:
        raw_candidates = _generate_candidates(rg, dest.lat, dest.lon, req.max_extra_walk_m)

    # always include the exact destination pin itself as the baseline candidate
    raw_candidates.append((dest.lat, dest.lon, "destination_pin"))

    if not raw_candidates:
        raise HTTPException(status_code=422, detail="No candidate drop points available "
                                                      "(no road network loaded near destination).")

    scored: list[SafeDropCandidateScored] = []
    for lat, lon, label in raw_candidates:
        walk_d = haversine_m(dest.lat, dest.lon, lat, lon)
        rstate = point_risk(rg, lat, lon, at_time)
        trade_off = rstate.risk_score + walk_d * WALK_PENALTY_PER_M
        scored.append(SafeDropCandidateScored(
            lat=lat, lon=lon, label=label, walk_distance_m=walk_d,
            risk_score=rstate.risk_score, trade_off_score=trade_off,
            evidence_ids=rstate.evidence_ids,
        ))

    scored.sort(key=lambda c: c.trade_off_score)
    best = scored[0]
    pin = next((c for c in scored if c.label == "destination_pin"), None)

    if pin and best.label == "destination_pin":
        reason = "The destination pin itself is the safest practical stopping point available."
    elif pin:
        reason = (
            f"Recommended point is {best.walk_distance_m:.0f}m from the destination pin "
            f"(risk {best.risk_score:.2f} vs pin risk {pin.risk_score:.2f}); "
            f"the extra walk is offset by materially lower infrastructure/crime risk evidence."
        )
    else:
        reason = f"Recommended point has the best safety/walk-distance trade-off among {len(scored)} candidates."

    return SafeDropResponse(destination=dest, recommended=best, all_candidates=scored, reason=reason)
