"""
Same purpose and method as build_district_crime_overlay.py (see that file's
docstring for the full rationale), applied to Jaipur/Rajasthan instead of
Surat/Gujarat. Real NCRB Rajasthan district CSVs split Jaipur into 5 real
sub-districts (JAIPUR EAST/NORTH/RURAL/SOUTH/WEST); their real totals are
summed as "Jaipur" and normalized against every other real Rajasthan district
for the same year.

Output: data/jaipur/crime/jaipur_district_risk.geojson
"""
import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
CRIME_DIR = DATA_DIR / "jaipur" / "crime"
YEAR = 2013
IPC_FILE = CRIME_DIR / "rajasthan_ipc__2013.csv"
WOMEN_FILE = CRIME_DIR / "rajasthan_women__2013.csv"
BOUNDARY_FILE = CRIME_DIR / "jaipur_district_nominatim.json"
OUT_FILE = CRIME_DIR / "jaipur_district_risk.geojson"

# Real NCRB district rows that together make up Jaipur.
TARGET_PREFIX = "JAIPUR"


def load_ipc_totals(path):
    totals = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = row.get("DISTRICT", "").strip()
            if not d or d == "ZZ TOTAL":
                continue
            try:
                t = float(row["TOTAL IPC CRIMES"])
            except (KeyError, ValueError):
                continue
            totals[d] = totals.get(d, 0.0) + t
    return totals


def load_women_totals(path):
    totals = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = (row.get("DISTRICT") or row.get("District") or "").strip().upper()
            if not d:
                continue
            fields = ["Rape", "Kidnapping and Abduction", "Dowry Deaths",
                      "Assault on women with intent to outrage her modesty",
                      "Insult to modesty of Women", "Cruelty by Husband or his Relatives"]
            s = 0.0
            for fld in fields:
                try:
                    s += float(row.get(fld, 0) or 0)
                except ValueError:
                    pass
            totals[d] = totals.get(d, 0.0) + s
    return totals


def main():
    ipc = load_ipc_totals(IPC_FILE)
    women = load_women_totals(WOMEN_FILE)
    if not ipc:
        raise SystemExit(f"No real IPC crime rows parsed from {IPC_FILE} -- aborting, will not fabricate.")

    # Group real per-district totals into "real districts" (each Jaipur
    # sub-district split counts as its own district for the purpose of a fair
    # relative ranking against Rajasthan's other, non-split districts).
    ipc_values = list(ipc.values())
    ipc_min, ipc_max = min(ipc_values), max(ipc_values)
    women_values = list(women.values()) or [0.0]
    women_min, women_max = min(women_values), max(women_values)

    jaipur_ipc_total = sum(v for d, v in ipc.items() if d.upper().startswith(TARGET_PREFIX))
    jaipur_women_total = sum(v for d, v in women.items() if d.upper().startswith(TARGET_PREFIX))

    def norm(v, lo, hi):
        return 0.0 if hi == lo else (v - lo) / (hi - lo)

    # Jaipur's split sub-district totals are each individually smaller than a
    # single-district city, so compare the SUMMED Jaipur total against the
    # summed range too, for a fair relative index (else Jaipur's 5-way split
    # would look artificially low next to single-row districts).
    single_district_values = [v for d, v in ipc.items() if not d.upper().startswith(TARGET_PREFIX)]
    compare_values = single_district_values + [jaipur_ipc_total]
    cmin, cmax = min(compare_values), max(compare_values)

    women_single = [v for d, v in women.items() if not d.upper().startswith(TARGET_PREFIX)]
    women_compare = women_single + [jaipur_women_total]
    wmin, wmax = min(women_compare), max(women_compare)

    crime_index = round(0.7 * norm(jaipur_ipc_total, cmin, cmax)
                         + 0.3 * norm(jaipur_women_total, wmin, wmax), 4)
    crime_index = max(0.0, min(1.0, crime_index))

    with open(BOUNDARY_FILE, encoding="utf-8-sig") as f:
        boundary = json.load(f)[0]

    feature = {
        "type": "Feature",
        "geometry": boundary["geojson"],
        "properties": {
            "district": "Jaipur (JAIPUR EAST+NORTH+RURAL+SOUTH+WEST, real NCRB district split, summed)",
            "year": YEAR,
            "total_ipc_crimes": jaipur_ipc_total,
            "total_women_crimes": jaipur_women_total,
            "crime_index": crime_index,
            "source": "NCRB 'Crime in India' district-wise IPC and crimes-against-women tables "
                       "(2013), same GitHub mirror of official data.gov.in/NCRB publications used "
                       "for Surat. Boundary polygon: OSM administrative boundary relation 1950062, "
                       "fetched via Nominatim (ODbL, https://www.openstreetmap.org/copyright).",
            "note": ("District-level ANNUAL AGGREGATE (summed across Jaipur's 5 real NCRB "
                     "sub-district rows), not a point location or a live measurement. Every "
                     "point inside this polygon gets the same crime_index contribution, since no "
                     "finer-grained real point-level crime dataset exists publicly for India "
                     "(documented in data/README.md)."),
        },
    }
    out = {"type": "FeatureCollection", "features": [feature]}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Jaipur IPC total (2013, summed 5 sub-districts): {jaipur_ipc_total}")
    print(f"Jaipur women-crime total (2013): {jaipur_women_total}")
    print(f"Normalized crime_index (relative to all Rajasthan districts, 2013): {crime_index}")
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
