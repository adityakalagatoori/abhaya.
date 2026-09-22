# CV Infrastructure Evidence Record Schema

> **UPDATE**: `backend/app/data_loader.py::load_cv_infrastructure_evidence`
> now exists and is authoritative. It expects `data/imagery/*.json` (or
> `*.jsonl`) files shaped exactly like:
> ```json
> [
>   {"lat": 21.1700, "lon": 72.8305, "timestamp": "2026-01-15T20:00:00",
>    "detections": [{"class": "streetlight_broken", "confidence": 0.85},
>                    {"class": "visibility_barrier", "confidence": 0.6}],
>    "model_version": "yolov8n-coco+heuristics-v1"}
> ]
> ```
> with `class` one of `streetlight_working`, `streetlight_broken`,
> `visibility_barrier`, `open_establishment`. `run_infrastructure_audit.py`
> writes exactly this shape to `data/imagery/cv_infrastructure_evidence.json`
> so the backend picks it up automatically with no backend code changes.
> The richer per-detection schema below (with bounding boxes, source image,
> per-detection ids) is written separately to `cv/output/infrastructure_evidence.json`
> for map/feature-panel display and CV-side debugging/traceability, and is
> the CV team's own extended record — the backend's simpler contract above
> is what actually gets consumed by `/infrastructure`.

This is the schema produced by the CV pipeline in `cv/` for consumption by
the ABHAYA backend's risk engine and the `GET /infrastructure` endpoint
(per spec sections 6.2 and 24.3: "the computer-vision model is not the
product; it is an evidence sensor for the product's existing risk
engine").

## Record shape (one JSON object per detection)

```json
{
  "evidence_id": "ev_000001",
  "value": "streetlight",
  "class_raw": "traffic light",
  "category": "lighting",
  "source": "cv_model",
  "confidence": 0.42,
  "timestamp": "2026-09-21T23:10:04Z",
  "location": {
    "lat": 21.185367,
    "lon": 72.810656
  },
  "image": {
    "filename": "surat_commons_000.jpg",
    "source_provider": "wikimedia_commons",
    "source_title": "File:Athwa Gate, Surat - panoramio.jpg",
    "source_url": "https://upload.wikimedia.org/..."
  },
  "model": {
    "name": "yolov8n",
    "weights": "yolov8n.pt (COCO-pretrained, Ultralytics)",
    "version": "ultralytics-8.x"
  },
  "bbox_xyxy": [123.4, 55.1, 210.9, 300.2]
}
```

## Fields

| Field | Type | Meaning |
|---|---|---|
| `evidence_id` | string | Stable id for this single detection/observation. |
| `value` | string | The ABHAYA-relevant factor this detection is evidence for. One of: `streetlight`, `visibility_barrier`, `open_establishment`. This is the field the risk engine should key on — it is NOT the raw COCO class name. |
| `class_raw` | string | The raw model class name that produced this record (e.g. `traffic light`, `fire hydrant`, `car`), kept for transparency/debugging. |
| `category` | string | One of `lighting`, `visibility`, `commercial`. Groups `value` into the three product factors from spec 6.2. |
| `source` | string | Always `"cv_model"` — matches the Evidence Record `source` enum used elsewhere in ABHAYA (vs. `"user_report"`, `"police_log"`, etc.). |
| `confidence` | float 0-1 | Model detection confidence (YOLO objectness * class score). For heuristic-only signals (see limitations), this is a heuristic confidence, not a learned-model confidence, and `model.name` will say `brightness_heuristic` instead of `yolov8n`. |
| `timestamp` | ISO 8601 UTC | When inference was run (observation time), NOT when the photo was taken — spec 24.3 requires "store observation time and confidence; allow later evidence to replace/qualify it." If the photo's own capture date is known it is additionally stored under `image.captured_at`. |
| `location.lat` / `location.lon` | float | WGS84 coordinates of the source image, from imagery metadata. |
| `image.filename` | string | File in `data/imagery/` that produced this detection. |
| `image.source_provider` | string | Where the source image came from (`mapillary` or `wikimedia_commons` in this prototype). |
| `model.name` / `model.weights` / `model.version` | string | Model identity + version, per spec 24.3 ("store the observation with timestamp/model version"). |
| `bbox_xyxy` | [float x4] | Pixel bounding box of the detection in the source image (for map/feature-panel overlay per spec 6.2 "show the detected evidence on the map"). Omitted for heuristic-only records (e.g. brightness) that have no bounding box. |

## `value` / `category` mapping (see README.md for full honesty notes)

| category | value | derived from |
|---|---|---|
| lighting | `streetlight` | COCO class `traffic light` detections used as a visual proxy for "there is street lighting infrastructure here" (see README limitations — YOLO/COCO has no `streetlight`/`lamp post` class) + a brightness heuristic (`streetlight_lit_heuristic` vs `streetlight_dark_heuristic`) computed from the image's mean pixel luminance, used only to qualify lit-vs-dark, never to invent a detection that isn't there. |
| visibility | `visibility_barrier` | Heuristic: high density / large area coverage of static occluding objects (COCO `bench`, `potted plant`, parked `truck`/`bus`/`car` walls, or large low-variance textured regions) covering a large fraction of the pedestrian sightline in frame. |
| commercial | `open_establishment` | COCO classes that plausibly indicate an open storefront/establishment in the frame (`umbrella`, `bench`, clusters of `person` + `car`/`motorcycle` outside a building) — see README for the honest caveat that COCO has no `shop`/`storefront` class either. |

## Output file

All records for a batch run are written to:

`cv/output/infrastructure_evidence.json` — a JSON array of the record
shape above, plus a sibling `.csv` with the same fields flattened.

## Query function for backend

`cv/infrastructure_api.py` exposes:

```python
def get_infrastructure_evidence(lat: float, lon: float, radius_m: float = 300) -> list[dict]:
    """Return evidence records within radius_m meters of (lat, lon)."""
```

This reads `cv/output/infrastructure_evidence.json`, computes haversine
distance, and returns matching records sorted by distance. The backend's
`GET /infrastructure?lat=&lon=&radius=` handler can call this directly or
shell out to `python cv/infrastructure_api.py --lat .. --lon .. --radius ..`
which prints the same list as JSON to stdout.
