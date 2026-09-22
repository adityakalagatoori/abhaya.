"""
evaluate.py -- the callable module the ABHAYA backend imports for
/walkguard/event and /routeguard/check (spec sections 7.2/7.3/24.8/24.9).

    from evaluate import evaluate_motion

    result = evaluate_motion(sensor_window, risk_context, detector_state=None)

See schema.md for the exact input/output contract. This function is
deliberately stateless at the Python-call level (all persistent state is
passed in/out as plain dict `detector_state`) so it drops into a stateless
FastAPI handler that loads/saves journey state from its existing Journey
State store (spec section 25) without needing an in-process singleton.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from features import extract_features
from state_machine import AnomalyDetector, RiskContext


def evaluate_motion(sensor_window: List[Dict[str, Any]],
                     risk_context: Optional[Dict[str, Any]] = None,
                     detector_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evaluate one window of real accelerometer/gyroscope samples.

    Args:
        sensor_window: list of {"t","ax","ay","az","gx"?,"gy"?,"gz"?} samples,
            chronologically ordered, from ONE journey's live sensor stream
            (t in unix ms; accel in m/s^2; gyro in rad/s if present).
            Typically 3-10 seconds of samples per call (WalkGuard/RouteGuard
            batch cadence) -- see schema.md.
        risk_context: dict matching RiskContext (risk_score, route_deviation,
            on_expected_walk_route, checkin_acknowledged,
            seconds_since_candidate). Supplied by the same risk engine used
            by navigation/RouteGuard/SafeDrop (spec section 25 Risk State).
        detector_state: the `detector_state` dict returned by the previous
            call for this journey (None on the first call of a journey).

    Returns:
        dict with:
            anomaly_state: "NORMAL" | "ANOMALY_CANDIDATE" | "CAUTION" | "ESCALATED"
            reasons: list of trigger reasons for this window
            detector_state: opaque dict to persist and pass back next call
            ... (see schema.md for full field list)

    Raises:
        ValueError if sensor_window has fewer than 3 samples.
    """
    feats = extract_features(sensor_window)
    risk = RiskContext.from_dict(risk_context)
    detector = AnomalyDetector.from_dict(detector_state)

    result = detector.step(feats, risk)
    result["detector_state"] = detector.to_dict()
    return result


if __name__ == "__main__":
    # tiny smoke test with a hand-built (clearly-labelled-synthetic, NOT used
    # for validation) window, just to prove the module imports and runs.
    demo_window = [
        {"t": i * 200.0, "ax": 0.2, "ay": 9.8, "az": 0.3}
        for i in range(10)
    ]
    out = evaluate_motion(demo_window, {"risk_score": 0.2})
    print(out["anomaly_state"], out["reasons"])
