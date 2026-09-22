"""
Central configuration for the ABHAYA backend.

DATA STORAGE CHOICE
--------------------
The spec (section 9) calls for PostgreSQL + PostGIS. PostGIS is not available
in this development environment (no Postgres server, no ability to install
system packages). We therefore use SQLite for the Evidence Record / journey
state store, with plain lat/lon columns and Python-side (shapely) spatial
predicates instead of PostGIS spatial SQL functions.

This is a documented substitution, not a simulation of the data itself:
- Same schema shape as would exist in PostGIS (lat/lon + attributes)
- Real spatial math (haversine distance, shapely geometry) done in Python
- Swapping to PostGIS later only requires replacing `app/db.py`'s engine URL
  and moving the point-in-radius filters from Python into PostGIS SQL
  (ST_DWithin), because the SQLAlchemy models below don't hardcode SQLite-only
  features.

Environment variables (all optional, sensible defaults for local dev):
  ABHAYA_DB_URL           SQLAlchemy URL, default sqlite:///./abhaya.db
  ABHAYA_DATA_DIR         Root of the shared data lake, default ../data
  ABHAYA_ACTIVE_CITY      Optional city subfolder under ABHAYA_DATA_DIR to load
                           data from, e.g. "jaipur". When unset (default), the
                           backend reads directly from ABHAYA_DATA_DIR/{road_network,
                           crime,imagery,establishments,gps_traces}/ exactly as
                           before (Surat's flat layout) — fully backward compatible.
                           When set, it reads from
                           ABHAYA_DATA_DIR/<ABHAYA_ACTIVE_CITY>/{...}/ instead, so the
                           backend can be pointed at e.g. data/jaipur/ without any
                           code changes. If the named city subfolder doesn't exist,
                           falls back to the flat layout so the service still boots.
  ABHAYA_DEFAULT_W_SAFETY     w1 in R = w1*Safety - w2*TimeDelay - w3*InfraRisk
  ABHAYA_DEFAULT_W_TIME       w2
  ABHAYA_DEFAULT_W_INFRA      w3
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = Path(os.environ.get("ABHAYA_DATA_DIR", PROJECT_ROOT / "data")).resolve()

# ACTIVE_CITY: if set and the subfolder exists, scope all data lookups to it
# (data/<city>/road_network/, data/<city>/crime/, ...). Default (unset, or a
# subfolder that doesn't exist) keeps the original flat data/ layout used by
# Surat, so existing deployments and this repo's default behavior are unaffected.
ACTIVE_CITY = os.environ.get("ABHAYA_ACTIVE_CITY", "").strip()
_CITY_ROOT = (DATA_DIR / ACTIVE_CITY) if ACTIVE_CITY else DATA_DIR
if ACTIVE_CITY and not _CITY_ROOT.is_dir():
    _CITY_ROOT = DATA_DIR  # honest fallback: named city has no data yet

ROAD_NETWORK_DIR = _CITY_ROOT / "road_network"
CRIME_DIR = _CITY_ROOT / "crime"
IMAGERY_DIR = _CITY_ROOT / "imagery"
ESTABLISHMENTS_DIR = _CITY_ROOT / "establishments"
GPS_TRACES_DIR = _CITY_ROOT / "gps_traces"

DB_URL = os.environ.get("ABHAYA_DB_URL", f"sqlite:///{BACKEND_DIR / 'abhaya.db'}")

DEFAULT_WEIGHTS = {
    "w_safety": float(os.environ.get("ABHAYA_DEFAULT_W_SAFETY", 1.0)),
    "w_time": float(os.environ.get("ABHAYA_DEFAULT_W_TIME", 0.4)),
    "w_infra": float(os.environ.get("ABHAYA_DEFAULT_W_INFRA", 0.6)),
}

# Fallback city center used when no road network file is found at all, so the
# service still boots and documents itself instead of crashing. Real routing
# will only work once real road_network files are present.
# Set ABHAYA_ACTIVE_CITY=jaipur to point the backend at data/jaipur/ instead
# (see config docstring above); this constant is only the map-display default
# and does not need to change for that to work.
FALLBACK_CENTER = {"lat": 21.1702, "lon": 72.8311, "name": "Surat, Gujarat"}
FALLBACK_CENTERS_BY_CITY = {
    "surat": {"lat": 21.1702, "lon": 72.8311, "name": "Surat, Gujarat"},
    "jaipur": {"lat": 26.9124, "lon": 75.7873, "name": "Jaipur, Rajasthan"},
}
if ACTIVE_CITY and ACTIVE_CITY.lower() in FALLBACK_CENTERS_BY_CITY:
    FALLBACK_CENTER = FALLBACK_CENTERS_BY_CITY[ACTIVE_CITY.lower()]

# RouteGuard tiered response thresholds
ROUTEGUARD_LEVEL1_RISK_DELTA = 0.15   # absolute risk increase to trigger Level 1
ROUTEGUARD_LEVEL2_RISK_DELTA = 0.35   # absolute risk increase to trigger Level 2
ROUTEGUARD_LEVEL1_DEVIATION_M = 60.0  # meters from expected corridor
ROUTEGUARD_LEVEL2_PERSIST_SEC = 90.0  # seconds a Level1 state must persist

# WalkGuard
WALKGUARD_DURATION_SEC = 300  # 5 minutes, per spec section 7.3 / 24.9
