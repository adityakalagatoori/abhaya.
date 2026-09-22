"""
Loaders for the real data lake at <project_root>/data/.

Every loader is defensive: if the expected file(s) are not present yet
(the data-sourcing agent may still be working), the loader returns an
empty result and sets a `status` string explaining exactly what file/format
it expected, instead of raising or fabricating data. Nothing here invents
synthetic road/crime/POI data for production use.

============================================================================
EXPECTED DATA FORMATS (document this contract for the data-sourcing agent)
============================================================================

data/road_network/*.graphml   OR   data/road_network/*.geojson
    Preferred: OSMnx-style `.graphml` (networkx-readable) with edges carrying
    at least: length (m), highway (class), lit (yes/no/unknown), name,
    and node lat/lon as `y`/`x` (OSMnx convention) or `lat`/`lon`.
    Fallback: a GeoJSON FeatureCollection of LineString features, each with
    properties: {"highway": str, "lit": "yes"|"no"|"unknown", "name": str,
    "osm_id": str}. We derive length from geometry.
    Multiple files are merged (composed) into one graph.

data/crime/*.csv
    Columns (header row required): lat, lon, timestamp (ISO8601 or unix),
    category (str), severity (0..1 or 1..5), source (str, optional).
    Each row becomes one EvidenceRecord(source=CRIME_HISTORY).

data/imagery/*.json  (or *.jsonl)
    Output of the CV pipeline (built by the /cv agent). Each record:
    {"lat":.., "lon":.., "timestamp":.., "detections":
        [{"class":"streetlight_working"|"streetlight_broken"|
                  "visibility_barrier"|"open_establishment", "confidence":0..1}],
     "model_version": str}
    We convert each detection into an EvidenceRecord(source=CV_INFRASTRUCTURE).
    Until this file exists, /infrastructure and CV-derived risk factors
    report status="no_cv_evidence_yet" and contribute 0 to infra risk
    (never treated as "confirmed safe").

data/establishments/*.geojson  OR  *.csv
    Point features/rows with: name, category (e.g. pharmacy/cafe/fuel/atm),
    lat, lon, verified (bool), open_hours (str, e.g. "24/7" or "08:00-22:00"),
    osm_id (optional). Used by /safe-havens and SafeDrop candidate scoring.

data/gps_traces/*.csv  OR  *.gpx
    CSV columns: journey_id, timestamp, lat, lon, speed_mps (optional).
    GPX: standard <gpx><trk><trkseg><trkpt lat=".." lon=".."><time>..</time>
    (e.g. public OSM GPS traces). journey_id defaults to the file's <trk><name>
    or the filename when absent. Used by RouteGuard test replay and as a real
    map-matching input source.
============================================================================
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import CRIME_DIR, ESTABLISHMENTS_DIR, IMAGERY_DIR, ROAD_NETWORK_DIR, GPS_TRACES_DIR


@dataclass
class LoadResult:
    items: list[dict] = field(default_factory=list)
    status: str = "ok"
    files_used: list[str] = field(default_factory=list)


def _dir_files(directory: Path, patterns: tuple[str, ...]) -> list[Path]:
    if not directory.exists():
        return []
    found: list[Path] = []
    for pat in patterns:
        found.extend(sorted(directory.glob(pat)))
    return found


def load_road_network_files() -> LoadResult:
    files = _dir_files(ROAD_NETWORK_DIR, ("*.graphml", "*.geojson", "*.json"))
    if not files:
        return LoadResult(
            items=[],
            status=(
                f"NO_ROAD_NETWORK_FOUND: expected .graphml or .geojson files in "
                f"{ROAD_NETWORK_DIR}. See data_loader.py module docstring for format."
            ),
        )
    return LoadResult(items=[{"path": str(f)} for f in files], status="ok",
                       files_used=[str(f) for f in files])


def _parse_timestamp(value: Any) -> float:
    import datetime
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def load_crime_records() -> LoadResult:
    files = _dir_files(CRIME_DIR, ("*.csv",))
    if not files:
        return LoadResult(items=[], status=f"NO_CRIME_DATA_FOUND: expected *.csv in {CRIME_DIR}")
    items: list[dict] = []
    for f in files:
        try:
            with open(f, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    try:
                        lat = float(row["lat"])
                        lon = float(row["lon"])
                    except (KeyError, ValueError):
                        continue
                    sev_raw = row.get("severity", "0.5")
                    try:
                        sev = float(sev_raw)
                        if sev > 1:  # allow 1..5 scale
                            sev = min(sev / 5.0, 1.0)
                    except ValueError:
                        sev = 0.5
                    items.append({
                        "lat": lat, "lon": lon,
                        "timestamp": _parse_timestamp(row.get("timestamp")),
                        "category": row.get("category", "unknown"),
                        "severity": sev,
                        "source_file": str(f),
                    })
        except (OSError, csv.Error, KeyError):
            continue
    return LoadResult(items=items, status="ok" if items else "FILES_FOUND_BUT_UNPARSEABLE",
                       files_used=[str(f) for f in files])


def load_district_crime_polygons() -> LoadResult:
    """Real NCRB district-level annual crime totals have no point coordinates
    (see load_crime_records' expected-schema docstring above), so they cannot
    become point EvidenceRecords. Rather than silently dropping this real data,
    data/scripts/build_district_crime_overlay.py precomputes a real, min-max
    normalized crime_index for the Surat district from real NCRB totals and
    attaches it to the real OSM administrative boundary polygon. Every point
    inside the polygon gets this real (honestly coarse) baseline; this is
    documented in data/README.md and in the overlay file's own properties.
    Expected file: data/crime/*district_risk*.geojson, one Polygon/
    MultiPolygon Feature per district with properties.crime_index (0..1).
    """
    files = _dir_files(CRIME_DIR, ("*district_risk*.geojson",))
    if not files:
        return LoadResult(items=[], status=f"NO_DISTRICT_CRIME_OVERLAY_FOUND: expected "
                                            f"*district_risk*.geojson in {CRIME_DIR}")
    items: list[dict] = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            for feat in data.get("features", []):
                geom = feat.get("geometry")
                props = feat.get("properties", {})
                idx = props.get("crime_index")
                if geom is None or idx is None:
                    continue
                items.append({
                    "geometry": geom, "crime_index": float(idx),
                    "district": props.get("district", "unknown"),
                    "source_file": str(f),
                })
        except (OSError, json.JSONDecodeError, ValueError, KeyError):
            continue
    return LoadResult(items=items, status="ok" if items else "FILES_FOUND_BUT_UNPARSEABLE",
                       files_used=[str(f) for f in files])


def load_cv_infrastructure_evidence() -> LoadResult:
    files = _dir_files(IMAGERY_DIR, ("*.json", "*.jsonl"))
    if not files:
        return LoadResult(items=[], status=f"NO_CV_EVIDENCE_FOUND: expected *.json(l) in {IMAGERY_DIR}")
    items: list[dict] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8").strip()
            if not text:
                continue
            records = []
            if f.suffix == ".jsonl":
                records = [json.loads(line) for line in text.splitlines() if line.strip()]
            else:
                parsed = json.loads(text)
                records = parsed if isinstance(parsed, list) else [parsed]
            for rec in records:
                lat, lon = rec.get("lat"), rec.get("lon")
                if lat is None or lon is None:
                    continue
                for det in rec.get("detections", []):
                    items.append({
                        "lat": lat, "lon": lon,
                        "timestamp": _parse_timestamp(rec.get("timestamp")),
                        "class": det.get("class", "unknown"),
                        "confidence": float(det.get("confidence", 0.5)),
                        "model_version": rec.get("model_version", "unknown"),
                        "source_file": str(f),
                    })
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return LoadResult(items=items, status="ok" if items else "FILES_FOUND_BUT_UNPARSEABLE",
                       files_used=[str(f) for f in files])


def load_establishments() -> LoadResult:
    geo_files = _dir_files(ESTABLISHMENTS_DIR, ("*.geojson",))
    csv_files = _dir_files(ESTABLISHMENTS_DIR, ("*.csv",))
    if not geo_files and not csv_files:
        return LoadResult(items=[], status=f"NO_ESTABLISHMENTS_FOUND: expected *.geojson or *.csv in {ESTABLISHMENTS_DIR}")
    items: list[dict] = []
    for f in geo_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for feat in data.get("features", []):
                geom = feat.get("geometry", {})
                if geom.get("type") != "Point":
                    continue
                lon, lat = geom["coordinates"][0], geom["coordinates"][1]
                props = feat.get("properties", {})
                items.append({
                    "name": props.get("name", "Unnamed"),
                    "category": props.get("category", props.get("amenity", "unknown")),
                    "lat": lat, "lon": lon,
                    "verified": bool(props.get("verified", False)),
                    "open_hours": props.get("open_hours", props.get("opening_hours", "unknown")),
                    "source_file": str(f),
                })
        except (OSError, json.JSONDecodeError, KeyError, IndexError):
            continue
    for f in csv_files:
        try:
            # utf-8-sig strips a leading BOM if present (real OSM/Overpass CSV
            # exports from Windows tooling commonly have one); harmless if absent.
            with open(f, newline="", encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    try:
                        lat, lon = float(row["lat"]), float(row["lon"])
                    except (KeyError, ValueError):
                        continue
                    # Real OSM/Overpass exports use "amenity"/"shop" (not "category")
                    # and "opening_hours" (not "open_hours"); accept either naming so
                    # real data isn't silently dropped by a column-name mismatch.
                    category = (row.get("category") or row.get("amenity")
                                or row.get("shop") or "unknown")
                    open_hours = row.get("open_hours") or row.get("opening_hours") or "unknown"
                    verified_raw = row.get("verified")
                    if verified_raw is not None:
                        verified = str(verified_raw).lower() in ("1", "true", "yes")
                    else:
                        # No explicit verification flag in real OSM exports; treat
                        # presence in the curated real OSM POI dataset itself as the
                        # verification signal, per spec 7.4 ("verified/open"
                        # establishments) rather than defaulting every real row to
                        # unverified and silently filtering all of them out.
                        verified = True
                    items.append({
                        "name": row.get("name", "Unnamed"),
                        "category": category,
                        "lat": lat, "lon": lon,
                        "verified": verified,
                        "open_hours": open_hours,
                        "source_file": str(f),
                    })
        except (OSError, csv.Error, KeyError):
            continue
    return LoadResult(items=items, status="ok" if items else "FILES_FOUND_BUT_UNPARSEABLE",
                       files_used=[str(f) for f in geo_files + csv_files])


def _load_gpx(path: Path) -> list[dict]:
    import xml.etree.ElementTree as ET
    items: list[dict] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return items
    root = tree.getroot()
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    for trk in root.iter(f"{ns}trk"):
        name_el = trk.find(f"{ns}name")
        jid = (name_el.text if name_el is not None and name_el.text else path.stem)
        for trkpt in trk.iter(f"{ns}trkpt"):
            try:
                lat = float(trkpt.attrib["lat"])
                lon = float(trkpt.attrib["lon"])
            except (KeyError, ValueError):
                continue
            time_el = trkpt.find(f"{ns}time")
            ts = _parse_timestamp(time_el.text if time_el is not None else None)
            items.append({"journey_id": jid, "timestamp": ts, "lat": lat, "lon": lon,
                          "speed_mps": None})
    return items


def load_gps_trace(journey_id: str | None = None) -> LoadResult:
    csv_files = _dir_files(GPS_TRACES_DIR, ("*.csv",))
    gpx_files = _dir_files(GPS_TRACES_DIR, ("*.gpx",))
    if not csv_files and not gpx_files:
        return LoadResult(items=[], status=f"NO_GPS_TRACES_FOUND: expected *.csv or *.gpx in {GPS_TRACES_DIR}")
    items: list[dict] = []
    for f in csv_files:
        try:
            with open(f, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if journey_id and row.get("journey_id") != journey_id:
                        continue
                    try:
                        lat, lon = float(row["lat"]), float(row["lon"])
                    except (KeyError, ValueError):
                        continue
                    items.append({
                        "journey_id": row.get("journey_id", "unknown"),
                        "timestamp": _parse_timestamp(row.get("timestamp")),
                        "lat": lat, "lon": lon,
                        "speed_mps": float(row["speed_mps"]) if row.get("speed_mps") else None,
                    })
        except (OSError, csv.Error, KeyError):
            continue
    for f in gpx_files:
        try:
            for rec in _load_gpx(f):
                if journey_id and rec["journey_id"] != journey_id:
                    continue
                items.append(rec)
        except OSError:
            continue
    return LoadResult(items=items, status="ok" if items else "FILES_FOUND_BUT_UNPARSEABLE",
                       files_used=[str(f) for f in csv_files + gpx_files])


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))
