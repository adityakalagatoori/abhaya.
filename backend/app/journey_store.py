"""Thin persistence helpers for JourneyState, backing RouteGuard/WalkGuard
continuity across requests (section 25: Journey State shared by Navigation,
RouteGuard, SafeDrop, WalkGuard)."""
from __future__ import annotations

import time
from typing import Optional

from sqlalchemy.orm import Session

from app.db import JourneyStateORM
from app.models import JourneyState, SafetyState, TravelMode


def save_journey(session: Session, js: JourneyState) -> None:
    row = session.get(JourneyStateORM, js.journey_id)
    if row is None:
        row = JourneyStateORM(journey_id=js.journey_id)
    row.origin_lat, row.origin_lon = js.origin
    row.dest_lat, row.dest_lon = js.destination
    row.mode = js.mode.value
    row.expected_route_json = ",".join(js.expected_route_segment_ids)
    row.departure_time = js.departure_time
    row.current_lat = js.current_lat
    row.current_lon = js.current_lon
    row.safety_state = js.safety_state.value
    row.level1_since = js.level1_since
    row.walkguard_active_until = js.walkguard_active_until
    row.updated_at = time.time()
    session.merge(row)
    session.commit()


def load_journey(session: Session, journey_id: str) -> Optional[JourneyState]:
    row = session.get(JourneyStateORM, journey_id)
    if row is None:
        return None
    return JourneyState(
        journey_id=row.journey_id,
        origin=(row.origin_lat, row.origin_lon),
        destination=(row.dest_lat, row.dest_lon),
        mode=TravelMode(row.mode) if row.mode else TravelMode.WALK,
        expected_route_segment_ids=row.expected_route_json.split(",") if row.expected_route_json else [],
        departure_time=row.departure_time or time.time(),
        current_lat=row.current_lat, current_lon=row.current_lon,
        safety_state=SafetyState(row.safety_state) if row.safety_state else SafetyState.NORMAL,
        level1_since=row.level1_since,
        walkguard_active_until=row.walkguard_active_until,
        updated_at=row.updated_at or time.time(),
    )
