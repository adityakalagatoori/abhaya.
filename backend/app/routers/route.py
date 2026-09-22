from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEFAULT_WEIGHTS
from app.db import get_session
from app.graph import get_road_graph
from app.journey_store import save_journey
from app.models import (JourneyState, LatLon, RouteRequest, RouteResponse,
                         RouteSegmentOut, TravelMode)

router = APIRouter()


@router.post("/route", response_model=RouteResponse)
def post_route(req: RouteRequest, session: Session = Depends(get_session)):
    rg = get_road_graph()
    if rg.graph.number_of_edges() == 0:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Road network data not yet available.",
                "expected_location": str(rg.load_status.get("status")),
            },
        )

    depart_time = req.time or time.time()
    w_safety = req.w_safety if req.w_safety is not None else DEFAULT_WEIGHTS["w_safety"]
    w_time = req.w_time if req.w_time is not None else DEFAULT_WEIGHTS["w_time"]
    w_infra = req.w_infra if req.w_infra is not None else DEFAULT_WEIGHTS["w_infra"]

    origin = (req.origin.lat, req.origin.lon)
    destination = (req.destination.lat, req.destination.lon)

    result = rg.route(origin, destination, depart_time, req.mode.value, w_safety, w_time, w_infra)
    if result is None:
        raise HTTPException(status_code=422, detail="No path found between origin and destination "
                                                      "in the available road network.")

    fastest = rg.route_fastest(origin, destination, req.mode.value)

    segments_out = []
    for (u, v, rstate, edata) in result["edge_states"]:
        segments_out.append(RouteSegmentOut(
            segment_id=rstate.segment_id, from_node=u, to_node=v,
            from_latlon=LatLon(lat=rg.graph.nodes[u]["lat"], lon=rg.graph.nodes[u]["lon"]),
            to_latlon=LatLon(lat=rg.graph.nodes[v]["lat"], lon=rg.graph.nodes[v]["lon"]),
            length_m=edata.get("length", 0.0), expected_arrival_time=rstate.evaluated_for_time,
            risk_score=rstate.risk_score, factors=rstate.factors, evidence_ids=rstate.evidence_ids,
        ))

    js = JourneyState(
        origin=origin, destination=destination, mode=req.mode,
        expected_route_segment_ids=[s.segment_id for s in segments_out],
        departure_time=depart_time,
        current_lat=origin[0], current_lon=origin[1],
    )
    save_journey(session, js)

    n_seg = max(1, len(segments_out))
    high_risk = [s for s in segments_out if s.risk_score > 0.4]
    if fastest and fastest["total_time_s"] > 0:
        delta_t = result["total_time_s"] - fastest["total_time_s"]
        explanation = (
            f"Route balances safety and time across {n_seg} segments (avg risk "
            f"{result['total_risk']/n_seg:.2f}). "
            + (f"{len(high_risk)} segment(s) still carry elevated risk factors "
               f"(lighting/crime/night); " if high_risk else "No high-risk segments detected; ")
            + (f"chosen route takes {delta_t:.0f}s longer than the pure-fastest path in exchange "
               f"for lower cumulative risk." if delta_t > 1 else
               "chosen route is also close to the fastest available path.")
        )
    else:
        explanation = f"Route computed across {n_seg} segments; average risk {result['total_risk']/n_seg:.2f}."

    return RouteResponse(
        journey_id=js.journey_id, origin=req.origin, destination=req.destination,
        departure_time=depart_time, total_distance_m=result["total_distance_m"],
        total_time_s=result["total_time_s"], total_risk=result["total_risk"],
        objective_value=result["objective_value"],
        weights={"w_safety": w_safety, "w_time": w_time, "w_infra": w_infra},
        segments=segments_out,
        alternative_fastest_time_s=fastest["total_time_s"] if fastest else None,
        alternative_fastest_risk=fastest["total_risk"] if fastest else None,
        explanation=explanation,
    )
