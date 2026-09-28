"""
DEMO SEED DATA -- NOT REAL PEOPLE.

ABHAYA is a prototype with no real other users yet, so there is currently no
real pool of "other travellers" to match a requesting user's journey
against. The Fellow Traveller Matching algorithm itself (app/matching.py) is
real, working code -- real road-graph/haversine route-corridor overlap, real
time-interval overlap, real meeting-point haversine distance, real
verification-evidence scoring. What is a placeholder is ONLY this list of
hypothetical traveller *journey records* it is matched against, because no
real second user has ever created a journey in this system.

Every record below is fictional and clearly labeled as such. None of this
data, nor anything derived from it, should ever be presented anywhere in the
API, logs, or UI as if it described a real person. When ABHAYA has real
users with real journeys, this module is deleted and /companions/match reads
candidate journeys from the real JourneyState store (app/journey_store.py)
instead.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class DemoTravellerJourney:
    """One hypothetical traveller's planned journey. `phone_verified` is the
    real field the verification/trust-evidence term of the match score
    (spec 31.2, w4) is computed from -- for a real user this would be set by
    ABHAYA's actual phone-verification flow, not fabricated per-candidate."""
    candidate_id: str
    first_name_or_initial: str
    origin: tuple[float, float]       # NEVER exposed directly via the API
    destination: tuple[float, float]  # NEVER exposed directly via the API
    departure_time: float
    mode: str  # matches app.models.TravelMode values
    phone_verified: bool


def _ts(hour: float, day_offset: int = 0) -> float:
    """Helper: a timestamp `hour` hours from now, shifted by `day_offset`
    days, so the seed data's time windows stay realistic relative to
    whenever the tests/demo actually run."""
    return time.time() + day_offset * 86400 + hour * 3600


# Coordinates deliberately reuse the same small area as the backend's own
# synthetic test road-network fixture (tests/fixtures/road_network) --
# roughly lat 21.1700-21.1720, lon 72.8300-72.8320 -- plus a couple of
# journeys far outside that area, so tests can exercise both "overlapping
# corridor" and "no overlap" cases against a real geometry computation.
DEMO_TRAVELLER_JOURNEYS: list[DemoTravellerJourney] = [
    DemoTravellerJourney(
        candidate_id="demo_traveller_001",
        first_name_or_initial="R.",
        origin=(21.1700, 72.8300),
        destination=(21.1700, 72.8320),
        departure_time=_ts(1.0),
        mode="walk",
        phone_verified=True,
    ),
    DemoTravellerJourney(
        candidate_id="demo_traveller_002",
        first_name_or_initial="Aisha",
        origin=(21.1701, 72.8301),
        destination=(21.1701, 72.8319),
        departure_time=_ts(1.2),
        mode="walk",
        phone_verified=True,
    ),
    DemoTravellerJourney(
        candidate_id="demo_traveller_003",
        first_name_or_initial="K.",
        origin=(21.1710, 72.8300),
        destination=(21.1710, 72.8320),
        departure_time=_ts(6.0),
        mode="walk",
        phone_verified=False,
    ),
    DemoTravellerJourney(
        candidate_id="demo_traveller_004",
        first_name_or_initial="Meera",
        # Far outside the requester's corridor -- used to prove non-overlapping
        # journeys score materially lower / are excluded.
        origin=(22.5726, 88.3639),   # Kolkata -- unrelated city, no overlap
        destination=(22.5800, 88.3700),
        departure_time=_ts(1.0),
        mode="walk",
        phone_verified=True,
    ),
    DemoTravellerJourney(
        candidate_id="demo_traveller_005",
        first_name_or_initial="S.",
        origin=(21.1700, 72.8300),
        destination=(21.1720, 72.8300),
        departure_time=_ts(30.0),  # same corridor, but a day+ apart in time
        mode="walk",
        phone_verified=True,
    ),
]


def get_demo_traveller_journeys() -> list[DemoTravellerJourney]:
    return list(DEMO_TRAVELLER_JOURNEYS)
