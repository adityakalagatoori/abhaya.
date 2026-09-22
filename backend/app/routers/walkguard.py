from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import WALKGUARD_DURATION_SEC
from app.db import get_session
from app.graph import get_road_graph
from app.journey_store import load_journey, save_journey
from app.models import SafetyState, WalkGuardEventRequest, WalkGuardEventResponse
from app.risk_engine import point_risk

router = APIRouter()

# Coarse motion-feature thresholds (section 24.5: interpretable, not a
# black-box model; these operate on pre-computed features, never raw streams)
RUNNING_ACCEL_THRESHOLD = 11.0       # m/s^2 sustained magnitude typical of running
SUDDEN_STOP_VARIANCE_DROP = 0.5      # relative drop from baseline variance
HIGH_RISK_LOCATION_THRESHOLD = 0.35


@router.post("/walkguard/event", response_model=WalkGuardEventResponse)
def post_walkguard_event(req: WalkGuardEventRequest, session: Session = Depends(get_session)):
    rg = get_road_graph()
    now = req.timestamp or time.time()

    js = load_journey(session, req.journey_id) if req.journey_id else None
    remaining = None
    if js and js.walkguard_active_until:
        remaining = max(0.0, js.walkguard_active_until - now)
    elif js:
        js.walkguard_active_until = now + WALKGUARD_DURATION_SEC
        remaining = float(WALKGUARD_DURATION_SEC)

    rstate = point_risk(rg, req.location.lat, req.location.lon, now)
    location_risk = rstate.risk_score

    anomaly_type = None
    anomaly = False
    if req.impact_detected:
        anomaly, anomaly_type = True, "impact"
    elif req.accel_magnitude >= RUNNING_ACCEL_THRESHOLD:
        anomaly, anomaly_type = True, "running"
    elif (req.baseline_accel_magnitude and req.baseline_accel_magnitude > 0
          and req.accel_variance <= req.baseline_accel_magnitude * SUDDEN_STOP_VARIANCE_DROP
          and req.speed_mps is not None and req.speed_mps < 0.3):
        anomaly, anomaly_type = True, "sudden_stop"

    # Section 24.5: never escalate on motion alone; combine with location/route
    # risk context. A single weak signal in a low-risk area stays "normal".
    concern = 0.0
    if anomaly:
        concern = 0.5 if anomaly_type != "impact" else 0.8
        concern += location_risk * 0.5

    safety_state = SafetyState.NORMAL
    response_level = "normal"
    reason = "No anomaly detected, or anomaly not corroborated by location risk context."

    if concern >= 0.75:
        safety_state = SafetyState.LEVEL2_CRITICAL
        response_level = "level2_critical_escalation"
        reason = (f"{anomaly_type} anomaly with high concern score {concern:.2f} "
                  f"(location risk {location_risk:.2f}); escalating per configured workflow.")
    elif concern >= 0.4:
        safety_state = SafetyState.LEVEL1_SUBTLE
        response_level = "level1_subtle_checkin"
        reason = (f"{anomaly_type} anomaly detected with concern score {concern:.2f} "
                  f"(location risk {location_risk:.2f}); discreet check-in requested.")

    if js:
        js.current_lat, js.current_lon = req.location.lat, req.location.lon
        js.safety_state = safety_state
        save_journey(session, js)

    return WalkGuardEventResponse(
        journey_id=req.journey_id, anomaly_detected=anomaly, anomaly_type=anomaly_type,
        location_risk=location_risk, combined_concern_score=concern, safety_state=safety_state,
        response_level=response_level, reason=reason, monitoring_seconds_remaining=remaining,
    )
