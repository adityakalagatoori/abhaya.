"""
Query function for the ABHAYA backend's GET /infrastructure endpoint.

Reads the evidence file produced by scripts/run_infrastructure_audit.py
(cv/output/infrastructure_evidence.json, the CV team's richer per-detection
record with bounding boxes and source-image references) and returns real
CV evidence records near a given coordinate. No network calls, no live
model inference here -- this is the fast read path the backend calls per
request; the (slower) detection pipeline is run offline/periodically by
run_infrastructure_audit.py and refreshes the JSON file it reads.

NOTE: as of this writing, backend/app/data_loader.py::load_cv_infrastructure_evidence
+ backend/app/graph.py's SpatialBucketIndex already implement an equivalent
radius query directly against data/imagery/*.json (the simpler
{lat, lon, timestamp, detections:[{class, confidence}], model_version}
contract also produced by run_infrastructure_audit.py). The backend's
GET /infrastructure endpoint uses that path today and does not need to
call this module. This function is kept as (a) a convenience for anyone
who wants the richer bbox/source-image detail this file carries, and
(b) a documented fallback/reference implementation matching the original
task spec ("a script/API function the backend's GET /infrastructure
endpoint can call").

Usage as a library (what the backend should do):

    from cv.infrastructure_api import get_infrastructure_evidence
    records = get_infrastructure_evidence(21.1854, 72.8106, radius_m=300)

Usage as a CLI (if the backend prefers to shell out):

    python cv/infrastructure_api.py --lat 21.1854 --lon 72.8106 --radius 300
"""
import argparse
import json
import math
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "infrastructure_evidence.json")


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def get_infrastructure_evidence(lat: float, lon: float, radius_m: float = 300.0, path: str = OUTPUT_PATH):
    """
    Return CV infrastructure evidence records within radius_m meters of
    (lat, lon), sorted nearest-first. Each record matches the schema in
    cv/evidence_schema.md, with an added `distance_m` field.

    Returns [] if the evidence file does not exist yet (e.g. the
    detection pipeline has not been run) rather than raising, so the
    backend can treat "no CV evidence yet" as a normal, empty result.
    """
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)

    out = []
    for r in records:
        loc = r.get("location") or {}
        rlat, rlon = loc.get("lat"), loc.get("lon")
        if rlat is None or rlon is None:
            continue
        dist = _haversine_m(lat, lon, rlat, rlon)
        if dist <= radius_m:
            rec = dict(r)
            rec["distance_m"] = round(dist, 1)
            out.append(rec)

    out.sort(key=lambda r: r["distance_m"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--radius", type=float, default=300.0)
    args = ap.parse_args()
    result = get_infrastructure_evidence(args.lat, args.lon, args.radius)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
