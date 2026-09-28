"""
Fellow Traveller Matching / Journey Companion (spec 31.1, 31.2, 31.7, 31.9).

Matches the requester's journey against other travellers' journeys using
real route-corridor overlap, real time-window overlap and real
meeting-point/verification scoring (app/matching.py). The pool of "other
travellers" matched against is currently DEMO SEED DATA
(app/companion_seed.py) -- clearly labeled there and never described as real
people -- because ABHAYA has no real second users yet. The algorithm itself
is real; only that placeholder dataset is not.

The companion relationship is attached to the SAME JourneyState object used
by /route, /routeguard/check and /walkguard/event (spec 31.5: "Journey
State: shared journey"), not a separate parallel companion object.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.companion_seed import get_demo_traveller_journeys
from app.db import get_session
from app.graph import get_road_graph
from app.journey_store import load_journey, save_journey
from app.matching import DEFAULT_COMPANION_WEIGHTS, compute_companion_match
from app.models import (CompanionCandidateOut, CompanionMatchRequest, CompanionMatchResponse,
                         CompanionRequestIn, CompanionRequestResponse, CompanionStatus, LatLon,
                         VerificationEvidence)

router = APIRouter()

MAX_CANDIDATES_RETURNED = 10


@router.post("/companions/match", response_model=CompanionMatchResponse)
def post_companions_match(req: CompanionMatchRequest):
    rg = get_road_graph()
    req_time = req.time or time.time()
    req_origin = (req.origin.lat, req.origin.lon)
    req_dest = (req.destination.lat, req.destination.lon)

    demo_journeys = get_demo_traveller_journeys()
    data_source_status = (
        "DEMO_SEED_DATA: matched against app/companion_seed.py's labeled "
        "hypothetical traveller journeys -- ABHAYA has no real other users "
        "yet. The matching algorithm/scoring is real; the candidate pool is "
        "a placeholder dataset."
    )

    scored: list[CompanionCandidateOut] = []
    for dj in demo_journeys:
        result = compute_companion_match(
            rg,
            req_origin, req_dest, req.mode.value, req_time,
            dj.origin, dj.destination, dj.mode, dj.departure_time,
            dj.phone_verified,
            weights=DEFAULT_COMPANION_WEIGHTS,
        )
        if result is None:
            continue  # no route-corridor overlap at all -- not a candidate (31.1)

        verification = VerificationEvidence(
            phone_verified=dj.phone_verified, evidence_score=result.verification_score,
        )
        scored.append(CompanionCandidateOut(
            candidate_id=dj.candidate_id,
            first_name_or_initial=dj.first_name_or_initial,
            verification_evidence=verification,
            route_overlap_pct=round(result.route_overlap_pct, 1),
            time_overlap_minutes=round(result.time_overlap_minutes, 1),
            travel_window={"start": dj.departure_time, "end": dj.departure_time + 3600},
            meeting_point=LatLon(lat=result.meeting_point[0], lon=result.meeting_point[1]),
            meeting_point_label="computed_overlap_centroid",
            meeting_point_practicality=round(result.meeting_point_practicality, 3),
            match_score=round(result.match_score, 4),
        ))

    scored.sort(key=lambda c: c.match_score, reverse=True)

    return CompanionMatchResponse(
        origin=req.origin, destination=req.destination, time=req_time, mode=req.mode,
        candidates=scored[:MAX_CANDIDATES_RETURNED],
        data_source_status=data_source_status,
        weights=DEFAULT_COMPANION_WEIGHTS,
    )


def _find_demo_candidate(candidate_id: str):
    for dj in get_demo_traveller_journeys():
        if dj.candidate_id == candidate_id:
            return dj
    return None


@router.post("/companions/request", response_model=CompanionRequestResponse)
def post_companions_request(req: CompanionRequestIn, session: Session = Depends(get_session)):
    js = load_journey(session, req.journey_id)
    if js is None:
        raise HTTPException(status_code=404, detail=f"No journey state found for journey_id={req.journey_id!r}. "
                                                      "Create one first via /route.")

    candidate = _find_demo_candidate(req.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"No companion candidate found for candidate_id={req.candidate_id!r}.")

    rg = get_road_graph()
    result = compute_companion_match(
        rg,
        js.origin, js.destination, js.mode.value, js.departure_time,
        candidate.origin, candidate.destination, candidate.mode, candidate.departure_time,
        candidate.phone_verified,
        weights=DEFAULT_COMPANION_WEIGHTS,
    )
    if result is None:
        raise HTTPException(status_code=422, detail="This candidate's journey no longer overlaps "
                                                      "this journey's route corridor.")

    companion_status = CompanionStatus(
        candidate_id=candidate.candidate_id,
        first_name_or_initial=candidate.first_name_or_initial,
        verified=candidate.phone_verified,
        meeting_point=LatLon(lat=result.meeting_point[0], lon=result.meeting_point[1]),
        match_score=round(result.match_score, 4),
    )

    # Attach to the SAME existing JourneyState object (spec 31.5) rather than
    # creating a separate parallel companion-state record.
    js.companion_status = companion_status
    save_journey(session, js)

    return CompanionRequestResponse(journey_id=js.journey_id, companion_status=companion_status, journey=js)
