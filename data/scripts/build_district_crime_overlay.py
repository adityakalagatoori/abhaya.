"""
Build a real district-level crime risk overlay for Surat, since NCRB's public
"Crime in India" district CSVs (2001-2014) are the ONLY real crime dataset
publicly available for India at any useful granularity, and they are
district-level annual totals with no point coordinates -- there is no real
point-level crime dataset anywhere for this to fall back to.

Rather than silently dropping this real data (which is what happened before
this script existed -- see data/README.md "Known limitations"), this computes
a real, honestly-coarse district-wide risk index from the real NCRB totals
and attaches it to the real Surat district administrative boundary polygon
(fetched from Nominatim/OSM), so every location physically inside the real
district gets a real, non-fabricated baseline crime-risk contribution instead
of zero.

Output: data/crime/surat_district_risk.geojson
    One Polygon/MultiPolygon feature with properties:
      district, year, total_ipc_crimes, total_women_crimes,
      crime_index (0..1, min-max normalized across ALL real Gujarat districts
        for the same year, so it is relative, not an absolute claim),
      source, note (states the real resolution limitation plainly)
"""
import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
CRIME_DIR = DATA_DIR / "crime"
YEAR = 2013  # last full year with a consistent real column schema across files
IPC_FILE = CRIME_DIR / "gujarat_ipc__2013.csv"
WOMEN_FILE = CRIME_DIR / "gujarat_women__2013.csv"
BOUNDARY_FILE = CRIME_DIR / "surat_district_nominatim.json"
OUT_FILE = CRIME_DIR / "surat_district_risk.geojson"

TARGET_DISTRICT_ROWS = ("SURAT COMMR.", "SURAT RURAL")  # real NCRB district split for Surat


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

    # Real min-max normalization across ALL real Gujarat districts for the same year,
    # so Surat's index is a real relative comparison, not an arbitrary number.
    ipc_values = list(ipc.values())
    ipc_min, ipc_max = min(ipc_values), max(ipc_values)

    surat_ipc_total = sum(ipc.get(d, 0.0) for d in TARGET_DISTRICT_ROWS)
    surat_women_total = sum(women.get(d, 0.0) for d in TARGET_DISTRICT_ROWS)

    def norm(v):
        return 0.0 if ipc_max == ipc_min else (v - ipc_min) / (ipc_max - ipc_min)

    # Blend: 70% real total-IPC-crime relative rank, 30% real women-safety-crime
    # relative rank (women crimes normalized against the max real women-crime
    # district total, since that's a separate real scale).
    women_values = list(women.values()) or [0.0]
    women_min, women_max = min(women_values), max(women_values)
    women_norm = 0.0 if women_max == women_min else (surat_women_total - women_min) / (women_max - women_min)

    crime_index = round(0.7 * norm(surat_ipc_total) + 0.3 * women_norm, 4)
    crime_index = max(0.0, min(1.0, crime_index))

    with open(BOUNDARY_FILE, encoding="utf-8-sig") as f:
        boundary = json.load(f)[0]

    feature = {
        "type": "Feature",
        "geometry": boundary["geojson"],
        "properties": {
            "district": "Surat (SURAT COMMR. + SURAT RURAL, real NCRB district split)",
            "year": YEAR,
            "total_ipc_crimes": surat_ipc_total,
            "total_women_crimes": surat_women_total,
            "crime_index": crime_index,
            "source": "NCRB 'Crime in India' district-wise IPC and crimes-against-women "
                       "tables (2013), via the same GitHub mirror of official data.gov.in/NCRB "
                       "publications used elsewhere in data/crime/. Boundary polygon: OSM "
                       "administrative boundary relation 1952514, fetched via Nominatim "
                       "(ODbL, https://www.openstreetmap.org/copyright).",
            "note": ("District-level ANNUAL AGGREGATE, not a point location or a live "
                     "measurement. This is a real, honestly coarse-grained baseline signal: "
                     "every point inside this polygon gets the same crime_index contribution, "
                     "since no finer-grained real point-level crime dataset exists publicly "
                     "for India (documented in data/README.md)."),
        },
    }
    out = {"type": "FeatureCollection", "features": [feature]}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Surat IPC total (2013): {surat_ipc_total}")
    print(f"Surat women-crime total (2013): {surat_women_total}")
    print(f"Normalized crime_index (relative to all Gujarat districts, 2013): {crime_index}")
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
