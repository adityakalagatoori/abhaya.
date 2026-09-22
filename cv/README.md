# ABHAYA — Computer Vision Infrastructure Audit (spec 6.2 / 24.3)

This is the CV "evidence sensor" for ABHAYA's risk engine. It does **not**
decide whether a location is safe — per spec 6.2, it produces timestamped,
confidence-scored infrastructure evidence records that the routing/risk
engine (in `backend/`) combines with crime history, establishment data,
etc.

## What this actually does (run end to end, real data, real model)

1. `scripts/fetch_commons_images.py` — pulls REAL, geotagged street/urban
   photographs of Surat, India from the Wikimedia Commons public API (no
   API key required) into `data/imagery/`, with a `manifest.json` mapping
   each file to its real lat/lon.
   - This is a **stop-gap real-data source**. The task's primary intended
     source is Mapillary street-level imagery, fetched by a separate
     data-sourcing agent into `data/imagery/`. At the time this pipeline
     was built, `data/imagery/` was empty, so this script was run to
     unblock development with real (if less systematically street-level)
     geotagged photos. `run_infrastructure_audit.py` processes *whatever
     image files* are in `data/imagery/`, so if/when Mapillary imagery
     lands there, re-running the pipeline picks it up automatically — no
     code changes needed, as long as a `manifest.json` (or equivalent
     lat/lon metadata per file) is present. See "Known limitation" below.
2. `scripts/run_infrastructure_audit.py` — loads a small, pretrained
   **YOLOv8n** model (Ultralytics, COCO-pretrained, ~6MB, no training
   performed) and runs real object detection on every real image in
   `data/imagery/`. Converts detections + two additional real pixel-level
   heuristics into ABHAYA evidence records.
3. Output:
   - `data/imagery/cv_infrastructure_evidence.json` — matches the exact
     contract already implemented by `backend/app/data_loader.py`
     (`{lat, lon, timestamp, detections:[{class, confidence}], model_version}`),
     so the backend's existing `/infrastructure` endpoint consumes this
     with **zero backend changes**.
   - `cv/output/infrastructure_evidence.json` / `.csv` — a richer,
     per-detection record (bounding box, source image/URL, per-detection
     id) for map/feature-panel display and CV-side debugging. Schema
     documented in `evidence_schema.md`.
4. `infrastructure_api.py` — `get_infrastructure_evidence(lat, lon, radius_m)`
   reads the richer JSON and returns nearby records sorted by distance
   (haversine). Kept as the task-specified "function the backend can
   call," though the backend currently uses its own equivalent
   (`SpatialBucketIndex` over the simpler contract file) — see the note at
   the top of that file.

## Model choice — why YOLOv8n

- Small (6.2MB weights), fast CPU inference, no GPU required — appropriate
  for a hackathon prototype per spec 6.2/24.3 ("use a small, pre-trained
  object-detection/CNN model rather than training a huge model from
  scratch").
- Pretrained on COCO (80 classes) via Ultralytics — zero training time,
  zero risk of overfitting to a tiny custom dataset.
- No classes were added, removed, or fine-tuned. This is the stock
  `yolov8n.pt` checkpoint, unmodified.

## Classes used, and the honest gap: COCO has no streetlight/shop/barrier class

The spec's three product-relevant classes (streetlight, visibility
barrier, open commercial establishment) **do not exist as COCO classes**.
Stock YOLOv8n cannot literally detect a "streetlight," a "wall/fence," or
a "shop." Rather than fabricate confidence scores for classes the model
was never trained on, the pipeline is explicit about what is a real model
detection vs. a heuristic computed on real pixels, and labels every
record's `model.name` field accordingly:

| ABHAYA factor | What we actually compute | Real signal used | Honest label |
|---|---|---|---|
| Streetlight / lighting condition | `streetlight_working` / `streetlight_broken` | **Brightness heuristic**: mean grayscale pixel luminance of the whole frame (OpenCV). We treat "is this street scene adequately illuminated" as an observable proxy for "is there working street lighting here," since we cannot see individual lamp posts as a class. This is the record shipped to the backend's `streetlight_working`/`streetlight_broken` classes. | `model.name = "brightness_heuristic"` |
| Streetlight (secondary, richer output only) | evidence that roadway lighting *infrastructure* exists at all | Real YOLO detections of COCO's `traffic light` class, used as an explicit, labeled proxy for engineered roadside lighting infrastructure (not literally a streetlight, but real evidence of managed road infrastructure at that point) | `model.name = "yolov8n"`, `class_raw = "traffic light"`, with a note field |
| Visibility barrier | `visibility_barrier` | Two real signals, either of which can trigger it: (a) YOLO detections of large static occluders — `truck`, `bus`, `bench` — that can block sightlines; (b) **edge-density heuristic**: Canny edge density across the full frame, as a proxy for dense structural clutter / solid walls / fences that COCO has no class for | `model.name = "yolov8n"` or `"edge_density_heuristic"` |
| Open commercial establishment | `open_establishment` | Heuristic: clustering of ≥3 real YOLO detections of `person`, `car`, `motorcycle`, `umbrella`, `bench` in one frame, used as a proxy for active foot traffic / an open establishment nearby (COCO has no `shop`/`storefront` class) | `model.name = "yolov8n+heuristic"` |

**Nothing here is a fabricated detection.** Every confidence value traces
back to either a real YOLOv8n forward pass on a real image, or a real,
deterministic pixel computation (brightness, edge density) on that same
real image. What is *not* real is the semantic label "streetlight" or
"open establishment" being a literal, trained class — that mapping is a
documented heuristic/proxy, not a lie about the underlying computation.

## Known limitations (read before trusting this in a demo)

1. **Imagery source is not Mapillary (yet).** 20 real, geotagged Wikimedia
   Commons photos of Surat were used because `data/imagery/` was empty
   when this pipeline needed to run. These are a mix of street-level shots
   (gates, railway stations, road scenes) and some less relevant geotagged
   photos (temples, malls, a spider on an office wall) that a proper
   Mapillary street-view crawl would not include. Detection *counts* below
   are real for these specific 20 images; they are not representative of
   citywide streetlight/barrier/shop prevalence in Surat.
2. **No "broken vs. working" ground truth exists anywhere in this
   pipeline** — `streetlight_working`/`streetlight_broken` is entirely a
   brightness-heuristic proxy, not a model that has ever seen a labeled
   broken streetlight. A photo taken at midday will always read as
   "working" by this heuristic regardless of actual streetlight condition.
3. **Small sample size.** 20 images produced 32 evidence records total.
   This is enough to prove the pipeline is real and wired end-to-end, not
   enough for statistically meaningful city coverage.
4. **No temporal/lighting control.** Photos were taken at unknown, varying
   times of day by different photographers for different purposes (not a
   systematic street survey), so the brightness heuristic conflates
   "photographed at night" with "poorly lit street."
5. **CV is not authoritative.** Per spec 6.2, none of this ever asserts a
   location is "safe" — it only emits evidence records with a confidence
   value for the risk engine to weigh with other independent evidence
   sources (crime history, establishment verification, etc).

## Actual results from this run (2026-09-21)

- 20 real images processed (0 skipped/unreadable).
- Raw YOLOv8n detections per image ranged 0–15 (COCO classes: mostly
  `person`, `car`, `truck`, `motorcycle`, `bench`, `traffic light`).
- 32 total evidence records produced across the 3 ABHAYA categories
  (lighting / visibility / commercial); every image contributes at least
  one lighting record (the brightness heuristic always fires).
- Example: `surat_commons_000.jpg` (Athwa Gate, Surat — lat 21.185367,
  lon 72.810656) → 15 raw YOLO detections → 1 `open_establishment`
  evidence record (confidence 0.56, from a person/car/motorcycle cluster)
  + 1 lighting record (`streetlight_working`, confidence 0.51 from
  brightness).
- Example: `surat_commons_001.JPG` → 1 real `truck` detection at bbox
  `[187.5, 1655.5, 544.1, 1934.7]` → `visibility_barrier` evidence record,
  confidence 0.53.
- Full output: `cv/output/infrastructure_evidence.json`,
  `data/imagery/cv_infrastructure_evidence.json`.

## Re-running

```
cv/pyenv/python.exe cv/scripts/fetch_commons_images.py      # only if data/imagery/ is still empty
cv/pyenv/python.exe cv/scripts/run_infrastructure_audit.py  # real inference + evidence generation
```

`cv/pyenv/` is a self-contained embeddable Python 3.11 + pip environment
(with torch/ultralytics/opencv installed) created for this task because no
system Python was available on this machine; it is not meant to be
committed as-is for other environments — swap for a normal venv where one
is available and `pip install ultralytics opencv-python-headless requests`.
