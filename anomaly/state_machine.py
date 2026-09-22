"""
state_machine.py -- the anomaly state machine required by spec 6.4 / 24.5 /
24.9. Implements the "recommended unique implementation" verbatim:

    1. Create a normal-motion baseline for the current journey.
    2. Measure deviation from that baseline.
    3. Check whether the user is simultaneously in a materially higher-risk
       location or has deviated from the route.
    4. Only then move the journey into the existing caution/check-in state.
    5. Keep one weak sensor signal from causing emergency escalation.

Explicitly implements the required "do not"s:
    - "Running = danger."          -> running only ever becomes ANOMALY_CANDIDATE.
    - "Sudden stop = emergency."   -> sudden stop only ever becomes ANOMALY_CANDIDATE,
                                       and only escalates if it PERSISTS.
    - "Trigger on every sudden movement." (WalkGuard 24.9) -> persistence window +
       risk-context gating are mandatory before CAUTION/ESCALATED.

State machine (per Journey State object, spec section 25):
    NORMAL            -> ordinary matches-baseline motion, or no baseline yet.
    ANOMALY_CANDIDATE -> this window's motion deviates from baseline
                         (running-like, sudden-stop-like, or erratic), but
                         it's a single window -- not yet acted on.
    CAUTION           -> the anomaly candidate has PERSISTED across
                         `persistence_windows` consecutive windows AND
                         risk_context is elevated (existing discreet
                         check-in flow per spec 6.4/24.8's tiered response,
                         "Level 1 - subtle").
    ESCALATED         -> CAUTION persisted with no resolving user response
                         within `escalation_timeout_s` (existing "Level 2 -
                         critical" tiered response), still gated on
                         risk_context.

The state machine is a pure, serialisable object: `to_dict()`/`from_dict()`
let a stateless HTTP backend (FastAPI /walkguard/event, /routeguard/check)
persist it between calls without needing server-side session memory.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any

from features import MotionFeatures
from baseline import JourneyBaseline, FeatureStat, _TRACKED


class AnomalyState(str, Enum):
    NORMAL = "NORMAL"
    ANOMALY_CANDIDATE = "ANOMALY_CANDIDATE"
    CAUTION = "CAUTION"
    ESCALATED = "ESCALATED"


# Deviation thresholds (z-scores against this journey's own baseline).
# Chosen from empirical validation against the WISDM real-world dataset
# (see validate.py / README) -- jogging windows separate from walking
# windows at roughly these thresholds for jerk/mean-mag/step-frequency.
Z_RUNNING = 2.0        # accel_mean_mag / dominant_step_freq_hz jump
Z_SUDDEN_STOP = 3.0    # jerk spike (deceleration) magnitude
Z_ERRATIC = 2.5        # accel_std_mag / jerk_std jump (pacing irregularity)

DEFAULT_PERSISTENCE_WINDOWS = 3     # spec: "require persistence/context before escalation"
DEFAULT_RISK_THRESHOLD = 0.6        # risk_context.risk_score in [0,1]; >= this is "materially higher risk"
DEFAULT_ESCALATION_TIMEOUT_S = 45.0  # no check-in response -> Level 2 (spec 7.2 "no response within window")


@dataclass
class RiskContext:
    """The subset of ABHAYA's shared Risk State / Journey State (spec
    section 25) this module needs. The backend fills this in from the same
    risk engine that powers navigation/RouteGuard/SafeDrop -- it is NOT
    computed here, so behaviour is interpreted "in the context of where the
    journey is happening" (spec 24.5 unique-implementation line).
    """
    risk_score: float = 0.0            # 0..1, current-segment infrastructure/crime/time risk
    route_deviation: bool = False      # RouteGuard: user/vehicle has left the expected corridor
    on_expected_walk_route: bool = True  # WalkGuard: still tracking the expected final-walk path
    checkin_acknowledged: bool = False  # user answered the discreet check-in prompt
    seconds_since_candidate: float = 0.0  # caller-tracked wall-clock time since first candidate in this streak

    @staticmethod
    def from_dict(d: Optional[dict]) -> "RiskContext":
        d = d or {}
        return RiskContext(
            risk_score=float(d.get("risk_score", 0.0)),
            route_deviation=bool(d.get("route_deviation", False)),
            on_expected_walk_route=bool(d.get("on_expected_walk_route", True)),
            checkin_acknowledged=bool(d.get("checkin_acknowledged", False)),
            seconds_since_candidate=float(d.get("seconds_since_candidate", 0.0)),
        )

    def is_elevated(self, threshold: float = DEFAULT_RISK_THRESHOLD) -> bool:
        return self.risk_score >= threshold or self.route_deviation or (not self.on_expected_walk_route)


@dataclass
class DeviationReport:
    z_scores: Dict[str, float]
    running_like: bool
    sudden_stop_like: bool
    erratic_like: bool

    @property
    def any_candidate(self) -> bool:
        return self.running_like or self.sudden_stop_like or self.erratic_like

    def reasons(self) -> List[str]:
        r = []
        if self.running_like:
            r.append("running_like")
        if self.sudden_stop_like:
            r.append("sudden_stop_like")
        if self.erratic_like:
            r.append("erratic_like")
        return r


# Sudden-stop is a TEMPORAL event (motion -> near-stillness), not something
# a single window's peak jerk can identify on its own -- ordinary walking
# footstep impacts produce jerk peaks of similar magnitude to a real stop
# (validated empirically against WISDM, see validate.py). What actually
# separates a real stop from ongoing gait, in the real dataset, is a sharp
# COLLAPSE in motion variance from one window to the next.
SUDDEN_STOP_MIN_PREV_STD = 1.5   # previous window must show real motion (not already still)
SUDDEN_STOP_MAX_CUR_STD = 1.5    # current window must be near-still
SUDDEN_STOP_DROP_RATIO = 0.5     # current std must fall to <= this fraction of previous std


def classify_deviation(feats: MotionFeatures, baseline: JourneyBaseline,
                        prev_accel_std_mag: Optional[float] = None) -> DeviationReport:
    z = baseline.deviation(feats)
    running_like = z.get("accel_mean_mag", 0.0) >= Z_RUNNING or z.get("dominant_step_freq_hz", 0.0) >= Z_RUNNING
    erratic_like = z.get("accel_std_mag", 0.0) >= Z_ERRATIC

    sudden_stop_like = False
    if prev_accel_std_mag is not None:
        prev_std, cur_std = prev_accel_std_mag, feats.accel_std_mag
        if (prev_std >= SUDDEN_STOP_MIN_PREV_STD and cur_std <= SUDDEN_STOP_MAX_CUR_STD
                and prev_std > 0 and cur_std <= SUDDEN_STOP_DROP_RATIO * prev_std):
            sudden_stop_like = True

    return DeviationReport(z_scores=z, running_like=running_like,
                            sudden_stop_like=sudden_stop_like, erratic_like=erratic_like)


@dataclass
class AnomalyDetector:
    """Stateful per-journey detector. Serialise with to_dict()/from_dict()
    between HTTP calls (/walkguard/event, /routeguard/check)."""
    baseline: JourneyBaseline = field(default_factory=JourneyBaseline)
    state: AnomalyState = AnomalyState.NORMAL
    consecutive_candidate_windows: int = 0
    persistence_windows: int = DEFAULT_PERSISTENCE_WINDOWS
    last_reasons: List[str] = field(default_factory=list)
    windows_seen: int = 0
    _prev_accel_std_mag: Optional[float] = None

    def step(self, feats: MotionFeatures, risk: RiskContext) -> Dict[str, Any]:
        self.windows_seen += 1
        prev_accel_std_mag = self._prev_accel_std_mag
        self._prev_accel_std_mag = feats.accel_std_mag

        # Only feed the baseline while we are NOT currently flagging a
        # candidate/caution/escalation -- otherwise an ongoing anomaly would
        # slowly get absorbed into "normal" and mask itself.
        if self.state == AnomalyState.NORMAL:
            self.baseline.update(feats)

        if not self.baseline.is_ready:
            self.state = AnomalyState.NORMAL
            self.consecutive_candidate_windows = 0
            self.last_reasons = []
            return self._result(feats, DeviationReport({}, False, False, False), risk)

        dev = classify_deviation(feats, self.baseline, prev_accel_std_mag)
        self.last_reasons = dev.reasons()

        if dev.any_candidate:
            self.consecutive_candidate_windows += 1
        else:
            self.consecutive_candidate_windows = 0

        # ---- state transition logic (spec 24.5 steps 1-5) ----
        if not dev.any_candidate:
            self.state = AnomalyState.NORMAL
        else:
            persisted = self.consecutive_candidate_windows >= self.persistence_windows
            risk_aligned = risk.is_elevated()

            if not persisted:
                # single/short-lived deviation: candidate only, spec:
                # "Running = anomaly candidate", "keep one weak sensor
                # signal from causing emergency escalation"
                self.state = AnomalyState.ANOMALY_CANDIDATE
            elif persisted and risk_aligned and not risk.checkin_acknowledged:
                if self.state == AnomalyState.CAUTION and risk.seconds_since_candidate >= DEFAULT_ESCALATION_TIMEOUT_S:
                    self.state = AnomalyState.ESCALATED
                else:
                    self.state = AnomalyState.CAUTION
            elif persisted and risk.checkin_acknowledged:
                # user responded to the discreet check-in -- stand down
                self.state = AnomalyState.ANOMALY_CANDIDATE
            else:
                # persisted, but risk context does NOT align -- spec:
                # motion anomaly alone (even if persistent) never escalates
                # without a materially worse safety context.
                self.state = AnomalyState.ANOMALY_CANDIDATE

        return self._result(feats, dev, risk)

    def _result(self, feats: MotionFeatures, dev: DeviationReport, risk: RiskContext) -> Dict[str, Any]:
        return {
            "anomaly_state": self.state.value,
            "reasons": dev.reasons(),
            "consecutive_candidate_windows": self.consecutive_candidate_windows,
            "baseline_ready": self.baseline.is_ready,
            "z_scores": dev.z_scores,
            "risk_context_elevated": risk.is_elevated(),
            "features": asdict(feats),
        }

    # -------- serialisation for stateless HTTP handlers --------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "consecutive_candidate_windows": self.consecutive_candidate_windows,
            "persistence_windows": self.persistence_windows,
            "windows_seen": self.windows_seen,
            "last_reasons": self.last_reasons,
            "prev_accel_std_mag": self._prev_accel_std_mag,
            "baseline": {
                "min_samples_for_baseline": self.baseline.min_samples_for_baseline,
                "max_history": self.baseline.max_history,
                "count": self.baseline._count,
                "stats": {k: {"n": s.n, "mean": s.mean, "m2": s.m2} for k, s in self.baseline.stats.items()},
            },
        }

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> "AnomalyDetector":
        if not d:
            return AnomalyDetector()
        det = AnomalyDetector(
            state=AnomalyState(d.get("state", "NORMAL")),
            consecutive_candidate_windows=d.get("consecutive_candidate_windows", 0),
            persistence_windows=d.get("persistence_windows", DEFAULT_PERSISTENCE_WINDOWS),
            windows_seen=d.get("windows_seen", 0),
            last_reasons=d.get("last_reasons", []),
        )
        det._prev_accel_std_mag = d.get("prev_accel_std_mag")
        b = d.get("baseline") or {}
        det.baseline.min_samples_for_baseline = b.get("min_samples_for_baseline", det.baseline.min_samples_for_baseline)
        det.baseline.max_history = b.get("max_history", det.baseline.max_history)
        det.baseline._count = b.get("count", 0)
        for k, sv in (b.get("stats") or {}).items():
            if k in det.baseline.stats:
                det.baseline.stats[k] = FeatureStat(n=sv.get("n", 0), mean=sv.get("mean", 0.0), m2=sv.get("m2", 0.0))
        return det
