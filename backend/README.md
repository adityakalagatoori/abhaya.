# ABHAYA Backend

FastAPI backend implementing the shared Risk State / Evidence Record / Journey
State architecture (spec section 25) and all 7 endpoints from spec section 17:
dynamic risk-aware routing, infrastructure evidence, SafeDrop, RouteGuard,
WalkGuard, verified safe-havens, and the safety-insight (RAG/LLM) contract.

## Run it

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health` — reports whether the real
road graph loaded, how many edges, and the exact status of each data source
(road network / crime / CV imagery / establishments), so you can see at a
glance what the data-sourcing agent still needs to drop in.

## Run tests

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest tests/ -v
```

Tests run against a small **synthetic, explicitly-labeled fixture graph**
(`backend/tests/fixtures/`) — a 3x3 street grid with a synthetic crime
incident and a synthetic CV "broken streetlight" detection — used only to
validate that the algorithms (time-aware risk, safety/time trade-off,
map-matching, anomaly gating) behave correctly. It is never read by the
production app; production always reads from `<repo_root>/data/`.

## Architecture decision: SQLite instead of PostGIS

The spec (section 9) calls for PostgreSQL + PostGIS. This dev environment has
no Postgres server available. We use SQLite (`app/db.py`) for the Evidence
Record / Journey State tables, and do spatial radius queries in Python
(haversine distance + a grid spatial index, `app/graph.py::SpatialBucketIndex`)
instead of PostGIS `ST_DWithin`. The schema is PostGIS-compatible (plain
lat/lon columns); swapping later means changing `ABHAYA_DB_URL` and moving
the Python-side radius filters into SQL. This is documented, not hidden.

## The three shared abstractions (`app/models.py`)

- **EvidenceRecord** — `{id, source, factor, value, confidence, timestamp, lat, lon}`.
  Every crime row, CV detection, and OSM road attribute becomes one of these.
- **RiskState** — a segment/point's risk, evaluated for a specific
  `evaluated_for_time` (not a permanent label), broken into
  `RiskFactorBreakdown` (crime_history, infrastructure_condition,
  activity_level, reports, time_of_travel, nearby_safety_context), plus the
  `evidence_ids` that produced it.
- **JourneyState** — persisted in SQLite, tracks the expected route, current
  location, mode, and `safety_state` (normal/level1_subtle/level2_critical)
  across RouteGuard and WalkGuard calls for the same `journey_id`.

All of navigation, SafeDrop, RouteGuard and WalkGuard call the *same*
`RoadGraph.edge_risk_state()` / `risk_engine.point_risk()` functions
(`app/graph.py`, `app/risk_engine.py`) — one risk engine, reused everywhere,
per spec section 24.1.

## Routing algorithm (`app/graph.py`)

- Road network loaded into a `networkx.MultiDiGraph`.
- A manual time-dependent Dijkstra (not `nx.dijkstra_path`, because edge cost
  depends on the *expected arrival time* at that edge, which changes as the
  path grows) computes, for each candidate edge:
  `cost = w_time * travel_time_s + w_infra * infra_risk * K + w_safety * risk_score * K`
  where `K = RISK_TO_SECONDS` converts normalized risk into comparable
  "equivalent seconds" so real time and risk trade off in one additive
  shortest-path weight — this is the same `R = w1*Safety - w2*TimeDelay -
  w3*InfraRisk` objective from spec 6.1/24.2, just expressed as a
  minimization-compatible cost.
- `/route` also computes a pure-fastest baseline (`w_safety=0`) and reports
  both, satisfying the "prove safety-aware routing differs from shortest
  route" evaluation in spec section 19.
- Weights are configurable per-request (`w_safety`, `w_time`, `w_infra`);
  defaults come from `ABHAYA_DEFAULT_W_*` env vars.

## Data contract (what the data-sourcing agent must drop into `../data/`)

See the module docstring in `app/data_loader.py` for the authoritative,
field-by-field spec. Summary:

| Folder | Expected files | Notes |
|---|---|---|
| `data/road_network/` | `*.graphml` (OSMnx-style) or `*.geojson` (LineString features with `highway`, `lit`, `name`) | Multiple files are merged |
| `data/crime/` | `*.csv` with `lat,lon,timestamp,category,severity,source` | severity 0..1 or 1..5 |
| `data/imagery/` | `*.json`/`*.jsonl`, **CV pipeline output**: `{"lat","lon","timestamp","detections":[{"class","confidence"}],"model_version"}` | classes: `streetlight_working`, `streetlight_broken`, `visibility_barrier`, `open_establishment`. A raw image *manifest* (filename/source/lat/lon, no `detections`) is not yet usable evidence — it is input to the `/cv` model, whose output must match this shape |
| `data/establishments/` | `*.geojson` (Point features) or `*.csv`: `name, category, lat, lon, verified, open_hours` | powers `/safe-havens` and SafeDrop candidates |
| `data/gps_traces/` | `*.csv` (`journey_id,timestamp,lat,lon,speed_mps`) or `*.gpx` (standard `<trk><trkseg><trkpt>`) | GPX `journey_id` defaults to `<trk><name>` |

Every loader in `app/data_loader.py` is defensive: missing/malformed files
never crash the app or fabricate data — they report an explicit `status`
string (e.g. `NO_ROAD_NETWORK_DATA: expected ...`) that is surfaced through
`/health` and through each endpoint's `data_source_status` field.

As of this writing, `data/road_network/` and `data/imagery/manifest.json`
contain in-progress/placeholder content from the data-sourcing agent (an
Overpass fetch that returned HTTP 406, and a raw image manifest without CV
detections yet) — the backend already handles both gracefully (falls back to
"no road network" / "no CV evidence" status rather than crashing).
`data/gps_traces/surat_trackpoints_p0.gpx` is a real, already-usable OSM
public GPS trace (5000 points) and parses correctly today.

## API contract (spec section 17)

### `POST /route`
Request: `{origin:{lat,lon}, destination:{lat,lon}, time?, mode, w_safety?, w_time?, w_infra?}`
Response: `{journey_id, segments:[{segment_id, risk_score, factors, evidence_ids, ...}], total_risk, total_time_s, alternative_fastest_time_s, alternative_fastest_risk, explanation}`
403/503 if no road network loaded yet; 422 if no path exists in the loaded graph.

### `GET /infrastructure?lat=&lon=&radius=`
Reads CV evidence (`data/imagery/`) within `radius` meters. Returns
`detections` (each traceable to an `evidence_id`) and an aggregate
`infrastructure_score`. `data_source_status` tells you if no CV evidence
exists yet for that area (never silently reports "safe").

### `POST /safedrop`
Request: `{destination:{lat,lon}, candidates?:[{lat,lon,label}], time?, max_extra_walk_m}`
If `candidates` omitted, real candidates are generated from actual road-graph
junctions within `max_extra_walk_m` of the destination (not arbitrary
offsets), plus the destination pin itself. Each is scored with the same risk
engine as `/route`, trading off `risk_score` against `walk_distance_m`.
Response includes every candidate's score and the evidence behind the pick.

### `POST /routeguard/check`
Request: `{journey_id?, expected_route_segment_ids:[...], current:{lat,lon}, current_time?, expected_time?}`
Map-matches the live GPS fix to the nearest real graph edge, compares its
risk (evaluated for now) against the expected route's risk (evaluated for
the expected arrival time), and returns a tiered
`normal` / `level1_subtle_checkin` / `level2_critical_escalation` state.
Level 2 requires the Level-1 condition to *persist* (`ROUTEGUARD_LEVEL2_PERSIST_SEC`)
— a single noisy GPS blip never immediately escalates.

### `POST /walkguard/event`
Request: coarse motion features only — `accel_magnitude, accel_variance,
gyro_magnitude, speed_mps?, impact_detected, baseline_accel_magnitude?` plus
`location`. Never accepts raw sensor streams (privacy constraint, spec 18).
An anomaly is only escalated when combined with `location_risk` from the same
risk engine (spec 24.5) — motion alone never reaches `level2_critical`.

### `GET /safe-havens?lat=&lon=&time=&radius=`
Real establishment data filtered to `verified == true` or currently
`open_now` (parsed from `open_hours`, supports `"24/7"` or `"HH:MM-HH:MM"`),
sorted by distance.

### `POST /safety-insight`
**Contract for the RAG/LLM agent** (see `app/models.py::SafetyInsightRequest`
docstring). Takes structured `route_context` (as produced by `/route` /
`/routeguard/check`) plus `retrieved_passages` already fetched by the RAG
retriever — this endpoint never calls an LLM or invents source text. Until
the RAG/LLM agent is wired in, it returns a deterministic template built only
from the supplied structured data, and reports `grounded:false` with an
`uncertainty_note` when no passages are supplied, rather than fabricating an
explanation.

## Explainability

Every `/route`, `/safedrop` and `/routeguard/check` response includes
`evidence_ids` traceable back to the exact `EvidenceRecord`s (crime rows / CV
detections / OSM `lit` tags) that produced each risk number, per spec
section 24.2 / 11.
