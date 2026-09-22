"""
Fetch REAL geotagged street-level-ish photographs from Wikimedia Commons
near Surat, India, to use as sample imagery for the CV infrastructure
pipeline, in case the dedicated data-sourcing agent has not yet populated
data/imagery/ with Mapillary images.

This uses Wikimedia Commons' public GeoSearch + imageinfo API (no API key
required) to find real images with real lat/lon coordinates within a
radius of central Surat. It is a stop-gap real-data source, not a
replacement for Mapillary street-level imagery.
"""
import json
import os
import re
import time
import urllib.request
import urllib.parse

HEADERS = {"User-Agent": "ABHAYA-CV-prototype/0.1 (contact: adityakalagatoori9@gmail.com)"}

# Central Surat coordinate
CENTER_LAT, CENTER_LON = 21.1702, 72.8311
RADIUS_M = 10000
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "imagery")
OUT_DIR = os.path.abspath(OUT_DIR)

# Keywords suggesting a street-level / urban infrastructure scene
# (roads, gates, stations, markets, junctions, buildings) as opposed to
# wildlife/food/flora close-ups that also happen to be geotagged in Surat.
KEYWORDS = [
    "street", "road", "gate", "station", "junction", "market", "bazaar",
    "chowk", "circle", "bridge", "building", "market", "town", "city",
    "mosque", "masjid", "temple", "fort", "railway", "square", "avenue",
    "colony", "housing", "complex", "tower", "mall", "shop",
]


def api_get(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def geosearch():
    params = {
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{CENTER_LAT}|{CENTER_LON}",
        "gsradius": RADIUS_M,
        "gslimit": 500,
        "gsnamespace": 6,
        "format": "json",
    }
    data = api_get(params)
    return data["query"]["geosearch"]


def looks_relevant(title):
    t = title.lower()
    return any(k in t for k in KEYWORDS)


def get_imageinfo(titles_batch):
    params = {
        "action": "query",
        "titles": "|".join(titles_batch),
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "format": "json",
    }
    return api_get(params)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = geosearch()
    print(f"geosearch returned {len(results)} geotagged Commons files near Surat")

    relevant = [r for r in results if looks_relevant(r["title"])]
    print(f"{len(relevant)} look like street/urban-infrastructure scenes by title keyword")

    # cap to a reasonable sample size for a hackathon prototype
    relevant = relevant[:25]

    manifest = []
    titles = [r["title"] for r in relevant]
    # batch imageinfo lookups (max 50 titles per call is fine here)
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        info = get_imageinfo(batch)
        pages = info.get("query", {}).get("pages", {})
        for _, page in pages.items():
            title = page.get("title")
            imageinfo = page.get("imageinfo")
            if not imageinfo:
                continue
            url = imageinfo[0]["url"]
            mime = imageinfo[0].get("mime", "")
            if not mime.startswith("image/"):
                continue
            match = next((r for r in relevant if r["title"] == title), None)
            if not match:
                continue
            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", title.replace("File:", ""))
            ext = os.path.splitext(safe_name)[1] or ".jpg"
            fname = f"surat_commons_{len(manifest):03d}{ext}"
            fpath = os.path.join(OUT_DIR, fname)
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=30) as resp, open(fpath, "wb") as f:
                    f.write(resp.read())
                manifest.append({
                    "filename": fname,
                    "source": "wikimedia_commons",
                    "source_title": title,
                    "source_url": url,
                    "lat": match["lat"],
                    "lon": match["lon"],
                })
                print(f"downloaded {fname}  ({title})  lat={match['lat']} lon={match['lon']}")
            except Exception as e:
                print(f"failed to download {title}: {e}")
            time.sleep(0.3)

    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"wrote {len(manifest)} images + manifest to {OUT_DIR}")


if __name__ == "__main__":
    main()
