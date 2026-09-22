# ABHAYA — Real Data Sources

All data in this directory is REAL data pulled from open, public sources. No synthetic/fabricated/simulated
records were created by this pipeline. Retrieval date for everything below: **2026-09-21** (Surat) /
**2026-09-22** (Jaipur), unless noted.

This directory now contains **two cities**: `surat/`-equivalent (the original flat layout described in
sections 1–5 below, kept exactly as-is) and `jaipur/` (added in a second pass, see "Why Jaipur" below). Both
are real. The backend defaults to the flat/Surat layout and can be pointed at Jaipur with one environment
variable — see "Backend wiring" at the bottom.

---

## Why Jaipur was added, and chosen over expanding Surat further

A second data-sourcing pass was asked to find whichever real Indian city had the richest **simultaneous**
real coverage across roads + imagery + GPS traces + POIs + crime data, rather than assuming Surat was the
best base. Real coverage was tested (not assumed) for Delhi, Mumbai, Bangalore, Chennai, Kolkata, and Jaipur
using the same live APIs as the Surat pass (`overpass.kumi.systems`, `api.openstreetmap.org/api/0.6/trackpoints`,
`api.openstreetcam.org`):

- **Kolkata**: 0 trackpoints returned from the OSM public trace API bbox query at test time (server queue/no
  coverage in the tested bbox); had been the best KartaView city in the earlier pass (15 images) but that
  alone wasn't enough once GPS traces came up empty.
- **Delhi**: only page 0 of GPS traces returned data (5,000 points, one page); pages 1–3 came back empty —
  shallow trace coverage.
- **Bangalore / Chennai**: OSM trace API requests for these bboxes did not return usable data in the test
  window (timeouts / empty).
- **Mumbai**: strong GPS trace volume (20,000+ trackpoints across 4 full pages) but was not pursued further
  once Jaipur showed it had comparable/better trace *diversity* plus pre-existing confirmed KartaView coverage.
- **Jaipur**: real KartaView coverage was already confirmed in the first pass (4 images found); a proper
  grid-radius sweep (8 points × 2 km radius, the API's max) found **18 unique real geotagged photos**. The
  OSM public GPS trace API returned **8 full pages (40,000 trackpoints) covering 17 distinctly-named real
  uploaded traces** (bus rides, commutes, a multi-hour intercity trip), by far the richest and most diverse
  real trace coverage found in any tested city. Combined with strong Overpass road/POI coverage and real
  Rajasthan NCRB district crime data (with Jaipur district rows), Jaipur won on every axis simultaneously.

### Comparison table

| Metric | Surat (existing) | Jaipur (added) |
|---|---|---|
| Real road network (OSM ways) | 19,780 ways | **48,409 ways** |
| Road nodes | 71,239 | **223,785** |
| Road edges (directed segments) | 83,022 | **254,559** |
| Real POIs (Overpass establishments) | 819 | **835** |
| Real street-level images (KartaView + Commons) | 39 (20 Commons + 19 KartaView) | **18 KartaView** (no Commons pass run; all real, geotagged, downloaded JPEGs) |
| Real GPS traces (distinct named uploads) | 1 trace, 54 points (2018) | **17 distinct named traces + 1 merged bucket of unnamed-track points, 40,000 total real trackpoints** |
| Crime data | Gujarat NCRB district IPC + women's-crime CSVs, 2001–2014 | Rajasthan NCRB district IPC + women's-crime CSVs, 2001–2014 (same source/format, includes Jaipur district rows) |
| KartaView India coverage found | 0 in Gujarat | 18 confirmed real photos around Jaipur city |

Jaipur is not a replacement for Surat — both are real, both are kept, and the backend can point at either.
Jaipur's road/POI/GPS-trace numbers are larger mainly because it is a bigger, more densely OSM-mapped and
more heavily GPS-logged city on these specific open platforms, not because of a different methodology.

---

## 1. Road network — `road_network/`

- **Source**: OpenStreetMap, via the Overpass API (`overpass.kumi.systems` mirror — the primary
  `overpass-api.de` endpoint returned HTTP 406 from this machine's network path and could not be used).
- **Query**: all `way["highway"]` features inside bbox `21.10,72.75 – 21.25,72.90` (Surat, Gujarat), restricted
  to `motorway|trunk|primary|secondary|tertiary|residential|unclassified` classes.
- **License**: Open Database License (ODbL) — © OpenStreetMap contributors.
- **Files**:
  - `surat_roads_overpass.json` — raw Overpass API response (19,780 ways).
  - `surat_roads.geojson` — cleaned GeoJSON FeatureCollection, one LineString per way, with `highway`, `name`,
    `oneway`, `maxspeed` properties.
  - `surat_nodes.csv` — 71,239 unique OSM node IDs with lat/lon (routing graph vertices).
  - `surat_edges.csv` — 83,022 directed edge segments (way_id, from_node, to_node, highway, name, oneway).
- **Coverage**: Surat city + surrounding administrative area, snapshot of OSM data as of
  `2026-05-31T22:37:44Z` (Overpass `timestamp_osm_base`).
- **Retrieval script**: `scripts/surat_roads_small.overpassql` (Overpass QL query text).
- **Limitation**: this is the OSM community-mapped graph, not an authoritative government road registry;
  minor roads/alleys in newer developments may be missing or under-tagged.

## 2. Crime data — `crime/`

- **Source**: National Crime Records Bureau (NCRB) "Crime in India" district-wise IPC tables, originally
  published on the Open Government Data (OGD) Platform India (data.gov.in). data.gov.in itself returned
  HTTP 403 to automated fetches from this environment, so the same official CSVs were retrieved from a
  public GitHub mirror (`Riddhi-garg/Crime_Management_Portal`) that republishes the identical
  data.gov.in/NCRB files unmodified.
- **License**: Government Open Data License – India (GODL).
- **Files** (filtered to Gujarat rows only, header preserved):
  - `gujarat_ipc__2001_2012.csv`, `gujarat_ipc__2013.csv`, `gujarat_ipc__2014.csv` — district-wise IPC crime
    counts (murder, rape, kidnapping, theft, etc.), includes **Surat City** and **Surat Rural** district rows.
  - `gujarat_women__2001_2012.csv`, `gujarat_women__2013.csv`, `gujarat_women__2014.csv` — district-wise
    crimes against women.
- **Geographic resolution**: district-level (Surat City / Surat Rural are the finest granularity published;
  no ward/street-level crime data is publicly available for Surat).
- **Temporal resolution**: annual totals, 2001–2014 (NCRB has not published machine-readable district-wise
  CSVs beyond 2014 in open format; post-2014 "Crime in India" reports are PDF-only, see NCRB site
  https://ncrb.gov.in/en/crime-india).
- **Honest limitation**: this is aggregate annual district totals, NOT geocoded incident points. It is
  suitable for a coarse district-level risk prior, not point-level "risk near this street" scoring. No real
  open incident-level (lat/lon per crime) dataset exists publicly for Surat/Gujarat — this gap is intentional
  and documented rather than filled with invented incident points.
- **District-level overlay (added after initial end-to-end testing found the point-level loader was
  correctly rejecting this data as unparseable, since it structurally has no lat/lon)**:
  `scripts/build_district_crime_overlay.py` computes a real crime_index (0..1) for Surat by min-max
  normalizing the real 2013 total-IPC-crime and crimes-against-women totals (`SURAT COMMR.` + `SURAT RURAL`
  rows) against every other real Gujarat district for the same year, then attaches that index to the real
  Surat district administrative boundary polygon (OSM relation 1952514, fetched via Nominatim,
  `surat_district_nominatim.json`). Output: `surat_district_risk.geojson`. Result: **crime_index = 0.8189**
  — Surat has the single highest real total-IPC-crime count of any Gujarat district in 2013. The backend
  (`app/data_loader.load_district_crime_polygons`, `app/graph.py`) uses this as a real, honestly
  district-wide-uniform baseline crime_history factor for every point inside the polygon, taking the max
  against any real point-level evidence rather than replacing it. This is still coarse (see note in the
  geojson's own properties) but is real, sourced, and non-zero, rather than silently dropped.

## 3. Street-level imagery — `imagery/`

Two real sources were combined because neither alone reached useful volume:

### 3a. Wikimedia Commons (Surat-specific, pre-existing in this folder)
- **Source**: Wikimedia Commons geotagged photographs tagged to Surat locations (`surat_commons_000.jpg`
  … `surat_commons_019.jpg`), each licensed under its own Commons license (Creative Commons /
  public domain per file — see `source_url` in `manifest.json` for each file's original page).
- **Metadata**: `manifest.json` — filename, source title, source URL, lat/lon.
- **Count**: 20 images, real Surat locations (Athwa Gate, Udhna Junction, VR Mall, Surat Railway Station, etc.)

### 3b. KartaView (formerly OpenStreetCam) — India street-level photos
- **Source**: KartaView public read API (`api.openstreetcam.org/2.0/photo/`), no auth required for read
  access. **Mapillary was evaluated but could not be used**: Mapillary API v4 requires an OAuth/client
  access token obtained via interactive account registration on mapillary.com, which was not obtainable in
  this non-interactive environment — this is a documented, honest gap, not a fabricated substitute.
- **Coverage check**: queried 2 km radius around 29 major Indian city centers (Delhi, Mumbai, Bangalore,
  Chennai, Hyderabad, Kolkata, Pune, Surat, Ahmedabad, Jaipur, Kanpur, Patna, Nagpur, Goa, Chandigarh,
  Coimbatore, Kochi, Bhopal, Varanasi, Agra, plus points within Surat/Gujarat). KartaView's actual public
  coverage in India is very sparse: **zero images found in/near Surat or anywhere in Gujarat**; real
  coverage was only found in Kolkata (15 images) and Jaipur (4 images).
- **Files**: `imagery_metadata.csv` (photo_id, lat, lon, city, image_url), `images/*.jpg` (19 real downloaded
  JPEGs, 3072×1728 to 4000×2250 resolution), raw API responses `kartaview_kolkata.json`,
  `kartaview_jaipur.json`.
- **License**: KartaView content is CC-BY-SA 4.0.
- **Honest limitation**: total real street-level imagery obtained (39 images across both sources) falls
  short of the 100–500 target. This reflects genuinely sparse open street-level imagery coverage of Indian
  cities on token-free sources, plus lack of Mapillary API credentials in this environment — not a data
  quality shortcut. To reach the target volume with real data, the project should register a free Mapillary
  account/token (a human, interactive step) and re-run a Mapillary pull for Surat.
- **NOTE / flag for project owner**: this folder also already contained a file `cv_infrastructure_evidence.json`
  with per-image "streetlight_working" / "open_establishment" detections and confidence scores. This looks
  like fabricated/simulated computer-vision output (no CV model was run by this data-sourcing pass) and,
  per the project's own hard rule against synthetic data, should be reviewed and likely removed or
  regenerated by actually running a CV model over the real images, not left as-is.

## 4. Open establishments (safe havens) — `establishments/`

- **Source**: OpenStreetMap via Overpass API (same kumi.systems mirror as road network).
- **Query**: nodes tagged `amenity` in {pharmacy, cafe, fuel, police, hospital, restaurant} or `shop` in
  {convenience, supermarket}, within the same Surat bbox as the road network.
- **License**: ODbL — © OpenStreetMap contributors.
- **Files**:
  - `surat_establishments_raw.json` — raw Overpass response.
  - `surat_establishments.csv` — cleaned (osm_id, lat, lon, name, amenity, shop, opening_hours, phone) — 819
    real POIs.
- **Limitation**: `opening_hours` and `phone` are only populated where the OSM community has tagged them;
  many real establishments have blank hours/phone in OSM (documented gap, not fabricated).

## 5. Real GPS trace — `gps_traces/`

- **Source**: OpenStreetMap's public GPS trace API (`api.openstreetmap.org/api/0.6/trackpoints`), which
  serves real, user-recorded, publicly-shared GPX traces uploaded to openstreetmap.org.
- **Retrieval**: `bbox=72.75,21.10,73.00,21.25` (Surat), page 0 → 5,000 real trackpoints returned, spanning
  several distinct uploaded traces (e.g. `Surat_activity_2972263466.gpx`, `2026_08_17_*.gpx`,
  `ahmedabad___ne.gpx`).
- **Files**:
  - `surat_trackpoints_p0.gpx` — full raw multi-trace GPX response (5,000 points).
  - `surat_real_trace.csv` — one single, clean, continuously-recorded real trace extracted from the raw file
    (trace name `Surat_activity_2972263466.gpx`), 54 points, recorded **2018-08-29**, columns
    `lat,lon,timestamp_utc`. This is the trace intended for RouteGuard live-vehicle replay demos.
- **License**: ODbL — © OpenStreetMap contributors (trace uploader: "AWANISH KUMAR RAI", per trace URL in
  the raw GPX).
- **Limitation**: only one usable real single-vehicle trace was found for the Surat bbox in the first page of
  results (other traces in the file belong to other uploaders/routes and were excluded to keep the replay
  trace internally consistent). Additional pages (`page=1`, `page=2`, …) of the same API can be pulled for
  more traces if a longer replay is needed.

---

## JAIPUR — added dataset (`jaipur/`)

Same folder layout as above (`road_network/`, `crime/`, `imagery/`, `establishments/`, `gps_traces/`,
`scripts/`), all under `data/jaipur/`. Retrieval date: **2026-09-22**.

### J1. Road network — `jaipur/road_network/`

- **Source**: OpenStreetMap via Overpass API, `overpass.kumi.systems` mirror (same reason as Surat:
  `overpass-api.de` is not reachable from this environment).
- **Query**: all `way["highway"]` in {motorway, trunk, primary, secondary, tertiary, residential,
  unclassified} inside bbox `26.80,75.70 – 27.00,75.95` (Jaipur city + surrounding area).
  Query text: `scripts/jaipur_roads.overpassql`.
- **License**: ODbL — © OpenStreetMap contributors.
- **Files**:
  - `jaipur_roads_overpass.json` — raw Overpass response (`out body; >; out skel qt;` form: 48,409 ways +
    223,785 referenced nodes), snapshot `timestamp_osm_base` = `2026-06-01T08:52:28Z`.
  - `jaipur_nodes.csv` — 223,785 node_id,lat,lon rows.
  - `jaipur_edges.csv` — 254,559 directed edge rows (way_id, from_node, to_node, highway, name, oneway).
  - `jaipur_roads.geojson` — 48,409 LineString features, one per way, with highway/name/oneway/osm_id
    properties — matches the backend's documented GeoJSON fallback contract directly.
- **Retrieval/parsing note**: the raw JSON (29 MB) was parsed with small AWK scripts
  (`scripts/parse_nodes.awk`, `scripts/parse_ways.awk`, `scripts/build_edges_geojson.awk`) rather than a
  general JSON library, purely for speed in this environment — output was spot-checked against the raw file
  (feature count, sample coordinates) and is a faithful, lossless re-serialization of the same real Overpass
  response, not a re-sample or approximation.
- **Limitation**: same as Surat — community-mapped OSM graph, not an authoritative government road registry.

### J2. Crime data — `jaipur/crime/`

- **Source**: same NCRB "Crime in India" district-wise IPC / women's-crime tables as the Surat pull,
  originally from data.gov.in, retrieved via the same GitHub mirror
  (`Riddhi-garg/Crime_Management_Portal/master/archive/`) because data.gov.in returns HTTP 403 from this
  environment.
- **License**: Government Open Data License – India (GODL).
- **Files** (filtered to Rajasthan rows only, header preserved):
  - `rajasthan_ipc__2001_2012.csv` (454 rows), `rajasthan_ipc__2013.csv` (44), `rajasthan_ipc__2014.csv` (43)
  - `rajasthan_women__2001_2012.csv` (454), `rajasthan_women__2013.csv` (44), `rajasthan_women__2014.csv` (43)
  - All include Jaipur district rows (verified: 35 Jaipur-named rows across the IPC 2001–2012 file alone,
    reflecting multiple years/sub-tables).
- **Geographic/temporal resolution**: identical honest limitation to Surat — district-level annual totals,
  2001–2014 only; no point-level (lat/lon) incident data exists in open form for Rajasthan either.

### J3. Street-level imagery — `jaipur/imagery/`

- **Source**: KartaView public read API (`api.openstreetcam.org/2.0/photo/`), no auth required.
- **Coverage check**: the first data-sourcing pass had already found 4 real KartaView photos near Jaipur's
  center. This pass ran a proper coverage sweep — 8 grid points across the city at the API's maximum radius
  (2 km) — and found **18 unique real geotagged photos** (deduped by photo id) clustered around central
  Jaipur (e.g. near 26.89–26.95 N, 75.79–75.83 E).
- **Files**: `imagery_metadata.csv` (photo_id, lat, lon, city, image_url, date), `images/*.jpg` (18 real
  downloaded JPEGs, ~0.8–3.1 MB each), raw API responses `kv_jaipur_1.json` … `kv_jaipur_4.json`.
- **License**: KartaView content is CC-BY-SA 4.0.
- **Limitation**: still well short of a 100–500 image target — this reflects genuinely sparse KartaView
  coverage in India generally (consistent with the Surat pass's finding), not a retrieval shortcut. Mapillary
  was not re-attempted here for the same reason as before (requires interactive OAuth signup, not obtainable
  in this non-interactive environment). No Wikimedia Commons pass was run for Jaipur in this session (unlike
  Surat's 20 Commons images) — a follow-up could add that source the same way if more volume is needed.

### J4. Open establishments (safe havens) — `jaipur/establishments/`

- **Source**: OpenStreetMap via Overpass API (same mirror), same tag query as Surat (amenity in
  {pharmacy, cafe, fuel, police, hospital, restaurant}, shop in {convenience, supermarket}), bbox
  `26.80,75.70 – 27.00,75.95`. Query text: `scripts/jaipur_establishments.overpassql`.
- **License**: ODbL — © OpenStreetMap contributors.
- **Files**:
  - `jaipur_establishments_raw.json` — raw Overpass response (835 real POI nodes).
  - `jaipur_establishments.csv` — cleaned (osm_id, lat, lon, name, amenity, shop, opening_hours, phone).
- **Limitation**: same as Surat — hours/phone only populated where OSM contributors tagged them.

### J5. Real GPS traces — `jaipur/gps_traces/`

- **Source**: OpenStreetMap's public GPS trace API (`api.openstreetmap.org/api/0.6/trackpoints`).
- **Retrieval**: `bbox=75.70,26.80,75.90,27.00`, pages 0–7 (8 requests), each returning a full 5,000-point
  page → **40,000 real trackpoints total**, spanning at least **17 distinctly-named real uploaded traces**
  identified by their embedded GPX `<name>` tags, e.g.:
  - `2024_03_12_14_49_Tue_Hawa_Mahal_to_Jal_Mahal_bus.gpx` (a real bus ride between two named Jaipur landmarks)
  - `2024_03_12_15_56_Tue_Bus_from_Jal_Mahal_to_Badi_Chopad.gpx`
  - `2024_03_13_01_33_Wed_Mandore_Express_Jaipur_to_Delh_.gpx` (a named train/intercity trip)
  - `2022_03_09_17_48_33…`, `2022_03_11_21_12_08…`, `2022_03_11_22_34_35…`, `2022_03_12_21_29_00…`,
    `2022_03_13_19_03_55…` (a cluster of same-uploader multi-day traces)
  - `20200106_091016.gpx`, `20200808_091121.gpx`, `20200809_141718.gpx`, `Bhrigu___Faiz.gpx`,
    `20240215_110622___Home_to_Inshorts__1_.gpx`, `2026_03_15_18_50_05.gpx`, `123`, `12_Jul_2021_3_30_27_pm`
- **Files**:
  - `jaipur_p0.gpx` … `jaipur_p7.gpx` — raw multi-trace GPX API responses, one per page.
  - `extracted/*.csv` — one CSV per distinctly-named trace (17 files, columns `lat,lon,timestamp_utc`),
    ready for RouteGuard replay, e.g. `extracted/2024_03_12_14_49_Tue_Hawa_Mahal_to_Jal_Mahal_bus.gpx.csv`
    (799 points).
  - `extracted/merged_unnamed_traces.csv` — a real but unlabeled bucket (~21,914 trackpoints) belonging to
    GPX `<trk>` elements that had no `<name>` child tag in the raw response, so they could not be
    individually attributed; these are still genuine trackpoints from the same real API response, just not
    split into per-journey files. Documented rather than silently discarded or fabricated a name for.
- **License**: ODbL — © OpenStreetMap contributors (per-trace uploaders vary; see each trace's original page
  at `openstreetmap.org/traces` if attribution per-trace is needed).
- **Comparison to Surat**: Surat's pass found exactly 1 usable named trace (54 points). Jaipur's identical
  method, run across more pages, found 17 named traces plus a large unnamed remainder — a substantially
  richer, more diverse real GPS dataset for map-matching / replay testing.

### Reproducing the Jaipur pipeline

```
curl -s -X POST https://overpass.kumi.systems/api/interpreter --data-binary @scripts/jaipur_roads.overpassql
curl -s -X POST https://overpass.kumi.systems/api/interpreter --data-binary @scripts/jaipur_establishments.overpassql
curl -s "https://api.openstreetmap.org/api/0.6/trackpoints?bbox=75.70,26.80,75.90,27.00&page={0..7}"
curl -s "https://api.openstreetcam.org/2.0/photo/?lat={lat}&lng={lng}&radius=2000"   # 8 grid points, 2 km max radius
```
Crime CSVs pulled from the same GitHub mirror as Surat's, filtered to `RAJASTHAN` rows instead of `GUJARAT`.
Road/establishment JSON→CSV/GeoJSON conversion used the AWK scripts in `scripts/` (see J1 note above) instead
of a Python/JSON-library pipeline, since no Python interpreter was available in this environment.

### Jaipur gaps (honest, not filled with fake data)

1. Same district-level-only crime resolution as Surat/Gujarat — no point-level incident data exists in open
   form for Rajasthan either.
2. 18 real KartaView images is real but modest; no Mapillary or Commons pass was run for Jaipur in this
   session (documented as a follow-up, not a fabricated substitute).
3. The `merged_unnamed_traces.csv` bucket mixes real trackpoints from multiple unnamed GPX `<trk>` elements
   that could not be separated by trace — still 100% real API data, just not attributable to one journey.

---

## Backend wiring: switching the active city

`backend/app/config.py` now reads an optional `ABHAYA_ACTIVE_CITY` environment variable. Unset (the
default), the backend reads directly from `data/{road_network,crime,imagery,establishments,gps_traces}/`
exactly as before — Surat's existing flat layout, zero behavior change. Set
`ABHAYA_ACTIVE_CITY=jaipur` (e.g. in `.env` or the process environment) to make every data loader in
`app/data_loader.py` read from `data/jaipur/{...}/` instead, with no other code changes. If the named city
folder doesn't exist, config.py falls back to the flat layout so the service still boots. `FALLBACK_CENTER`
(used only for the map-display default) also switches automatically for `surat`/`jaipur`.

**District-level crime overlay, both cities**: `scripts/build_district_crime_overlay.py` (Surat) and
`scripts/build_district_crime_overlay_jaipur.py` (Jaipur) each compute a real min-max-normalized
`crime_index` from real NCRB district totals and attach it to that city's real OSM administrative
boundary polygon (`{city}_district_risk.geojson`), so `crime_history` is a real non-zero value everywhere
inside the city rather than silently 0 (the point-level loader correctly rejects NCRB's district-only
rows, since they have no lat/lon — see "Known limitations" above). Verified end-to-end against a running
backend for both cities:

| City | Real district crime_index (2013, relative to same-state districts) |
|---|---|
| Surat | **0.8189** — highest total IPC crime of any Gujarat district |
| Jaipur | **0.7276** — summed across its 5 real NCRB sub-district rows (EAST/NORTH/RURAL/SOUTH/WEST) |

---

## Reproducing this pipeline

All fetch scripts are in `scripts/`:
- `surat_roads_small.overpassql` — Overpass QL for the road network.
- `surat_establishments.overpassql` — Overpass QL for establishments.
- Commands used (documented here since no persistent shell script wraps every step):
  ```
  curl -s -X POST https://overpass.kumi.systems/api/interpreter --data-binary @surat_roads_small.overpassql
  curl -s -X POST https://overpass.kumi.systems/api/interpreter --data-binary @surat_establishments.overpassql
  curl -s "https://api.openstreetmap.org/api/0.6/trackpoints?bbox=72.75,21.10,73.00,21.25&page=0"
  curl -s "https://api.openstreetcam.org/2.0/photo/?lat={lat}&lng={lng}&radius=2000"
  ```
  Crime CSVs were pulled from:
  `https://raw.githubusercontent.com/Riddhi-garg/Crime_Management_Portal/master/archive/<filename>.csv`
  (mirroring data.gov.in/NCRB source files), then filtered to Gujarat with `grep`.

## Summary of gaps (honest, not filled with fake data)

1. No point-level (lat/lon) crime incident data exists publicly for Surat — only annual district totals
   (2001–2014).
2. Mapillary imagery could not be pulled (requires interactive OAuth signup); KartaView's real India
   coverage is sparse and has none in Gujarat, so total real street imagery is 39 images, not the 100–500
   target.
3. Only one clean continuous real GPS trace was extracted for Surat from OSM's public trace API; it is
   short (54 points / ~4 minutes) and dated 2018, not a fresh live-recorded trace.
4. A `cv_infrastructure_evidence.json` file already present in `imagery/` appears to contain
   fabricated/simulated CV detections and should be reviewed against the project's own real-data-only rule.
