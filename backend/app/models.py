"""
Pydantic API models AND the three shared engineering abstractions from
spec section 25: Risk State, Evidence Record, Journey State.

These three objects are what every feature (routing, SafeDrop, RouteGuard,
WalkGuard, safe-havens, safety-insight) reads and writes, per section 24.1 /
25 ("one risk state, many existing features"). No feature computes its own
private notion of "is this safe".
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Evidence Record  (section 25: value, source, timestamp, confidence, location)
# ---------------------------------------------------------------------------

class EvidenceSource(str, Enum):
    CRIME_HISTORY = "crime_history"
    CV_INFRASTRUCTURE = "cv_infrastructure"   # streetlight/visibility/open-establishment CV
    OSM_ROAD_ATTRIBUTE = "osm_road_attribute"  # lit=yes/no, highway class, surface
    GPS_TRACE = "gps_trace"
    USER_REPORT = "user_report"
    ESTABLISHMENT_REGISTRY = "establishment_registry"


class EvidenceRecord(BaseModel):
    """A single timestamped, sourced, confidence-scored observation.

    This is the atomic unit of "why" behind every risk number. Every risk
    contribution attached to a route/SafeDrop/RouteGuard decision must be
    traceable to one or more EvidenceRecord.id values (explainability
    requirement, section 24.2 / 11).
    """
    id: str = Field(default_factory=lambda: new_id("ev"))
    source: EvidenceSource
    factor: str  # e.g. "lighting", "crime_incident", "visibility_barrier", "open_establishment"
    value: float  # normalized 0..1 unless raw_value given for display
    raw_value: Optional[str] = None
    confidence: float = 0.7  # 0..1
    timestamp: float = Field(default_factory=time.time)
    lat: float
    lon: float
    segment_id: Optional[str] = None
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Risk State  (section 25: current/estimated risk factors per segment/time)
# ---------------------------------------------------------------------------

class RiskFactorBreakdown(BaseModel):
    crime_history: float = 0.0
    infrastructure_condition: float = 0.0  # from CV: lighting/visibility
    activity_level: float = 0.0            # crowd/open-establishment density proxy
    reports: float = 0.0
    time_of_travel: float = 0.0            # night penalty etc.
    nearby_safety_context: float = 0.0     # proximity to verified safe havens (reduces risk)


class RiskState(BaseModel):
    """Time-aware risk estimate for one road segment (or point), evaluated
    for a specific expected-arrival timestamp -- NOT a permanent label.
    Section 24.2: "evaluate the road in the context of when the user is
    actually expected to traverse it."
    """
    segment_id: str
    lat: float
    lon: float
    evaluated_for_time: float  # unix ts this score is valid for
    factors: RiskFactorBreakdown
    risk_score: float  # normalized 0 (low risk) .. 1 (high risk)
    evidence_ids: list[str] = Field(default_factory=list)
    computed_at: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Journey State  (section 25: expected route, mode, current location, safety state)
# ---------------------------------------------------------------------------

class SafetyState(str, Enum):
    NORMAL = "normal"
    LEVEL1_SUBTLE = "level1_subtle"
    LEVEL2_CRITICAL = "level2_critical"


class TravelMode(str, Enum):
    WALK = "walk"
    DRIVE = "drive"
    RIDE_HAILING = "ride_hailing"


class CompanionRequestStatus(str, Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"


class CompanionStatus(BaseModel):
    """Companion relationship attached to an existing JourneyState (spec
    31.1/31.5: the companion relationship becomes attached to the SAME
    Journey State, not a separate parallel object). Never carries the
    candidate's exact home/origin address -- only what section 31.2's
    privacy rule allows to be shared: first name/initial, verified status,
    the computed meeting point, and the match score."""
    candidate_id: str
    first_name_or_initial: str
    verified: bool
    meeting_point: "LatLon"
    match_score: float
    status: CompanionRequestStatus = CompanionRequestStatus.REQUESTED
    requested_at: float = Field(default_factory=time.time)


class TransitStatus(BaseModel):
    """Bus-journey status attached to an existing JourneyState (spec 31.4/31.5:
    TransitGuard reuses the SAME Journey State rather than a separate object).
    Mirrors safety_state's tiering but tracks the bus-specific deviation state
    plus a reference to the vehicle whose demo/real compliance evidence was
    last checked, so the shared journey timeline (spec 31.8 'Shared Journey'
    screen) can show bus + companion + route in one place."""
    vehicle_id: str
    transit_state: SafetyState = SafetyState.NORMAL
    level1_since: Optional[float] = None
    last_checked_at: float = Field(default_factory=time.time)
    last_matched_segment_id: Optional[str] = None


class JourneyState(BaseModel):
    journey_id: str = Field(default_factory=lambda: new_id("jrn"))
    origin: tuple[float, float]
    destination: tuple[float, float]
    mode: TravelMode = TravelMode.RIDE_HAILING
    expected_route_segment_ids: list[str] = Field(default_factory=list)
    departure_time: float = Field(default_factory=time.time)
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None
    safety_state: SafetyState = SafetyState.NORMAL
    level1_since: Optional[float] = None
    walkguard_active_until: Optional[float] = None
    companion_status: Optional[CompanionStatus] = None
    transit_status: Optional[TransitStatus] = None
    updated_at: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# API request/response schemas (section 17)
# ---------------------------------------------------------------------------

class LatLon(BaseModel):
    lat: float
    lon: float


class RouteRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    time: Optional[float] = None  # unix ts of departure; default = now
    mode: TravelMode = TravelMode.WALK
    w_safety: Optional[float] = None
    w_time: Optional[float] = None
    w_infra: Optional[float] = None


class RouteSegmentOut(BaseModel):
    segment_id: str
    from_node: str
    to_node: str
    from_latlon: LatLon
    to_latlon: LatLon
    length_m: float
    expected_arrival_time: float
    risk_score: float
    factors: RiskFactorBreakdown
    evidence_ids: list[str]


class RouteResponse(BaseModel):
    journey_id: str
    origin: LatLon
    destination: LatLon
    departure_time: float
    total_distance_m: float
    total_time_s: float
    total_risk: float
    objective_value: float
    weights: dict
    segments: list[RouteSegmentOut]
    alternative_fastest_time_s: Optional[float] = None
    alternative_fastest_risk: Optional[float] = None
    explanation: str


class InfrastructureDetection(BaseModel):
    evidence_id: str
    factor: str
    value: float
    confidence: float
    lat: float
    lon: float
    timestamp: float
    description: Optional[str] = None


class InfrastructureResponse(BaseModel):
    lat: float
    lon: float
    radius_m: float
    detections: list[InfrastructureDetection]
    infrastructure_score: float
    data_source_status: str


class SafeDropCandidate(BaseModel):
    lat: float
    lon: float
    label: Optional[str] = None


class SafeDropRequest(BaseModel):
    destination: LatLon
    candidates: Optional[list[SafeDropCandidate]] = None
    time: Optional[float] = None
    max_extra_walk_m: float = 250.0


class SafeDropCandidateScored(BaseModel):
    lat: float
    lon: float
    label: Optional[str]
    walk_distance_m: float
    risk_score: float
    trade_off_score: float
    evidence_ids: list[str]


class SafeDropResponse(BaseModel):
    destination: LatLon
    recommended: SafeDropCandidateScored
    all_candidates: list[SafeDropCandidateScored]
    reason: str


class RouteGuardCheckRequest(BaseModel):
    journey_id: Optional[str] = None
    expected_route_segment_ids: list[str]
    current: LatLon
    current_time: Optional[float] = None
    expected_time: Optional[float] = None


class RouteGuardCheckResponse(BaseModel):
    journey_id: Optional[str]
    matched_segment_id: Optional[str]
    is_on_expected_route: bool
    deviation_distance_m: float
    expected_segment_risk: Optional[float]
    actual_segment_risk: Optional[float]
    risk_delta: float
    safety_state: SafetyState
    response_level: str
    reason: str
    evidence_ids: list[str]


class WalkGuardEventRequest(BaseModel):
    journey_id: Optional[str] = None
    location: LatLon
    timestamp: Optional[float] = None
    accel_magnitude: float          # m/s^2, coarse feature (not raw stream)
    accel_variance: float
    gyro_magnitude: float
    speed_mps: Optional[float] = None
    impact_detected: bool = False
    baseline_accel_magnitude: Optional[float] = None


class WalkGuardEventResponse(BaseModel):
    journey_id: Optional[str]
    anomaly_detected: bool
    anomaly_type: Optional[str]
    location_risk: float
    combined_concern_score: float
    safety_state: SafetyState
    response_level: str
    reason: str
    monitoring_seconds_remaining: Optional[float] = None


class SafeHaven(BaseModel):
    evidence_source: str
    name: str
    category: str
    lat: float
    lon: float
    distance_m: float
    verified: bool
    open_now: bool


class SafeHavensResponse(BaseModel):
    lat: float
    lon: float
    time: float
    candidates: list[SafeHaven]
    data_source_status: str


class SafetyInsightRequest(BaseModel):
    """Contract for the RAG/LLM agent building /rag.

    This backend does NOT call an LLM itself. It packages structured,
    evidence-grounded route/risk context and forwards `retrieved_passages`
    (already retrieved by the RAG agent's retriever) through to whatever
    generation backend is wired in later via `insight_backend_url`
    (or, if unset, falls back to a deterministic template -- never a
    fabricated LLM-style claim).
    """
    route_context: dict = Field(
        description="Structured context: e.g. {'segments':[...], 'total_risk':..., "
                    "'high_risk_factors':[...]} as produced by /route or /routeguard/check"
    )
    retrieved_passages: list[dict] = Field(
        default_factory=list,
        description="[{'text':.., 'source':.., 'timestamp':.., 'score':..}, ...] "
                    "supplied by the RAG retriever; NOT fetched by this endpoint",
    )
    question: Optional[str] = None


class SafetyInsightResponse(BaseModel):
    explanation: str
    grounded: bool
    sources_used: list[dict]
    uncertainty_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Fellow Traveller Matching / Journey Companion (spec section 31.1/31.2/31.9)
# ---------------------------------------------------------------------------

class CompanionMatchRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    time: Optional[float] = None  # unix ts of departure; default = now
    mode: TravelMode = TravelMode.WALK


class VerificationEvidence(BaseModel):
    """Trust evidence shown SEPARATELY from the match relevance score
    (spec 31.2: "Verification evidence should be displayed separately from
    the match relevance so the user can make their own decision")."""
    phone_verified: bool
    evidence_score: float  # 0..1, contributes to w4 term of the match score


class CompanionCandidateOut(BaseModel):
    """Privacy-preserving candidate view (spec 31.1/31.2): first name/initial,
    verified status, approximate route overlap, travel window, meeting point.
    Exact home/origin address is NEVER included."""
    candidate_id: str
    first_name_or_initial: str
    verification_evidence: VerificationEvidence
    route_overlap_pct: float
    time_overlap_minutes: float
    travel_window: dict  # {"start": ts, "end": ts} -- candidate's journey window, not their home location
    meeting_point: LatLon
    meeting_point_label: str
    meeting_point_practicality: float  # 0..1
    match_score: float


class CompanionMatchResponse(BaseModel):
    origin: LatLon
    destination: LatLon
    time: float
    mode: TravelMode
    candidates: list[CompanionCandidateOut]
    data_source_status: str
    weights: dict


class CompanionRequestIn(BaseModel):
    journey_id: str
    candidate_id: str


class CompanionRequestResponse(BaseModel):
    journey_id: str
    companion_status: CompanionStatus
    journey: JourneyState


# ---------------------------------------------------------------------------
# ABHAYA TransitGuard -- bus journey safety layer (spec section 31.3-31.9)
# ---------------------------------------------------------------------------

class BusEvidenceRecord(BaseModel):
    """EvidenceRecord-shaped compliance observation for one bus-safety
    category (spec 25: value/source/timestamp/confidence), used by
    GET /bus/safety-status. `value` is the boolean compliance value coerced
    to 0.0/1.0 so it slots into the same numeric convention as EvidenceRecord;
    `raw_value` keeps the human-readable form."""
    factor: str  # "tracking_active" | "panic_button_functional" | "visibility_compliant" | "lighting_adequate" | "authorised_stops"
    value: float
    raw_value: str
    source: str
    timestamp: float
    confidence: float


class BusSafetyStatusRequest(BaseModel):
    vehicle_id: str
    operator: Optional[str] = None
    journey_id: Optional[str] = None


class BusSafetyStatusResponse(BaseModel):
    vehicle_id: str
    operator: Optional[str]
    route_name: Optional[str]
    found: bool
    tracking: Optional[BusEvidenceRecord] = None
    panic_button: Optional[BusEvidenceRecord] = None
    visibility: Optional[BusEvidenceRecord] = None
    lighting: Optional[BusEvidenceRecord] = None
    authorised_stops: Optional[BusEvidenceRecord] = None
    overall_compliance_score: float  # 0..1, fraction of boolean checks that pass
    data_source_status: str
    reason: str


class TransitGuardCheckRequest(BaseModel):
    journey_id: Optional[str] = None
    vehicle_id: str
    expected_route_segment_ids: list[str]
    current: LatLon
    current_time: Optional[float] = None
    expected_time: Optional[float] = None
    include_bus_evidence: bool = True


class TransitGuardCheckResponse(BaseModel):
    journey_id: Optional[str]
    vehicle_id: str
    matched_segment_id: Optional[str]
    is_on_expected_route: bool
    deviation_distance_m: float
    expected_segment_risk: Optional[float]
    actual_segment_risk: Optional[float]
    risk_delta: float
    bus_compliance_score: Optional[float]
    bus_data_source_status: Optional[str]
    transit_state: SafetyState
    response_level: str
    reason: str
    evidence_ids: list[str]
