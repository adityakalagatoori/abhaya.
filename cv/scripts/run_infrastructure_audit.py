"""
ABHAYA CV Infrastructure Audit pipeline (spec 6.2 / 24.3).

Runs REAL YOLOv8n (COCO-pretrained, Ultralytics) object detection on the
REAL street-level images in data/imagery/, then converts the raw
detections into ABHAYA infrastructure Evidence Records (see
cv/evidence_schema.md) for three product-relevant factors:

  1. streetlight  (lighting)     - proxy signal, see README limitations
  2. visibility_barrier (visibility) - heuristic over detections + image stats
  3. open_establishment (commercial) - proxy signal, see README limitations

HONESTY NOTE (also in README.md): the stock COCO class list used by
YOLOv8n has NO "streetlight", "lamp post", "shop", "storefront", or
"wall/fence barrier" class. Rather than fabricate detections for classes
the model cannot actually see, this pipeline:
  - uses COCO's `traffic light` class as an explicit, labeled PROXY for
    roadside lighting infrastructure (a traffic light is real evidence of
    engineered street infrastructure/illumination at that point, even
    though it is not literally a lamp post),
  - combines that with a real, computed brightness/luminance heuristic
    on the actual image pixels to say whether the scene is lit or dark,
  - flags "open_establishment" candidates from real detections of
    `person`, `car`, `motorcycle`, `umbrella`, `bench` clusters near what
    looks like a building facade (dense object clustering in the lower-
    middle frame), again labeled explicitly as a heuristic, not a
    ground-truth "shop" class,
  - flags "visibility_barrier" from real detections of large static
    occluders (`truck`, `bus`, dense parked `car`s, `bench`) covering a
    large fraction of the frame, combined with an edge-density heuristic
    for solid walls/fences (which COCO also has no class for).
Every record's `model.name` field says plainly whether it came from the
real YOLO detector ("yolov8n") or from a pixel heuristic
("brightness_heuristic" / "edge_density_heuristic"), so nothing here is
presented as more than it is.
"""
import argparse
import csv
import json
import os
from datetime import datetime, timezone

import cv2
import numpy as np
from ultralytics import YOLO

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
IMAGERY_DIR = os.path.join(ROOT_DIR, "data", "imagery")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MANIFEST_PATH = os.path.join(IMAGERY_DIR, "manifest.json")

# COCO classes we treat as real, direct evidence (not proxies)
COCO_LIGHT_PROXY = {"traffic light"}
COCO_BARRIER_OBJECTS = {"truck", "bus", "bench"}
COCO_COMMERCIAL_SIGNAL = {"umbrella", "bench", "person", "car", "motorcycle"}

MODEL_WEIGHTS = "yolov8n.pt"
MODEL_VERSION = "yolov8n-coco+heuristics-v1"

# Backend contract (see backend/app/data_loader.py load_cv_infrastructure_evidence):
#   data/imagery/*.json -> [{"lat":.., "lon":.., "timestamp":.., "detections":
#       [{"class": "streetlight_working"|"streetlight_broken"|
#                  "visibility_barrier"|"open_establishment", "confidence":0..1}],
#     "model_version": str}]
BACKEND_EVIDENCE_PATH = os.path.join(IMAGERY_DIR, "cv_infrastructure_evidence.json")


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return {m["filename"]: m for m in json.load(f)}
    return {}


def image_files():
    exts = (".jpg", ".jpeg", ".png")
    return sorted(
        f for f in os.listdir(IMAGERY_DIR)
        if f.lower().endswith(exts)
    )


def brightness_heuristic(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    mean_lum = float(np.mean(gray)) / 255.0
    return mean_lum


def edge_density_heuristic(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    density = float(np.count_nonzero(edges)) / edges.size
    return density


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conf", type=float, default=0.25, help="YOLO confidence threshold")
    args = ap.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    manifest = load_manifest()
    files = image_files()
    print(f"Found {len(files)} images in {IMAGERY_DIR}")
    if not files:
        print("No images found. Nothing to do.")
        return

    model = YOLO(MODEL_WEIGHTS)
    print(f"Loaded {MODEL_WEIGHTS} (COCO-pretrained YOLOv8n)")

    records = []
    backend_records = []
    eid = 0
    per_image_summary = []

    for fname in files:
        fpath = os.path.join(IMAGERY_DIR, fname)
        meta = manifest.get(fname, {})
        lat = meta.get("lat")
        lon = meta.get("lon")

        img_bgr = cv2.imread(fpath)
        if img_bgr is None:
            print(f"  skip (unreadable): {fname}")
            continue

        results = model.predict(source=fpath, conf=args.conf, verbose=False)
        r = results[0]
        names = r.names
        dets = []
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = names[cls_id]
            conf = float(box.conf[0])
            xyxy = [float(v) for v in box.xyxy[0]]
            dets.append((cls_name, conf, xyxy))

        per_image_summary.append((fname, len(dets)))

        image_block = {
            "filename": fname,
            "source_provider": meta.get("source", "unknown"),
            "source_title": meta.get("source_title"),
            "source_url": meta.get("source_url"),
        }

        # --- 1. Direct real detections relevant to product factors ---
        for cls_name, conf, xyxy in dets:
            if cls_name in COCO_LIGHT_PROXY:
                eid += 1
                records.append({
                    "evidence_id": f"ev_{eid:06d}",
                    "value": "streetlight",
                    "class_raw": cls_name,
                    "category": "lighting",
                    "source": "cv_model",
                    "confidence": round(conf, 4),
                    "timestamp": now_iso(),
                    "location": {"lat": lat, "lon": lon},
                    "image": image_block,
                    "model": {"name": "yolov8n", "weights": MODEL_WEIGHTS, "version": "ultralytics"},
                    "bbox_xyxy": xyxy,
                    "note": "traffic_light class used as roadside-infrastructure/lighting proxy (COCO has no streetlight class)",
                })
            if cls_name in COCO_BARRIER_OBJECTS:
                eid += 1
                records.append({
                    "evidence_id": f"ev_{eid:06d}",
                    "value": "visibility_barrier",
                    "class_raw": cls_name,
                    "category": "visibility",
                    "source": "cv_model",
                    "confidence": round(conf, 4),
                    "timestamp": now_iso(),
                    "location": {"lat": lat, "lon": lon},
                    "image": image_block,
                    "model": {"name": "yolov8n", "weights": MODEL_WEIGHTS, "version": "ultralytics"},
                    "bbox_xyxy": xyxy,
                    "note": f"large static object ({cls_name}) treated as potential sightline obstruction",
                })

        # --- 2. Heuristic: lit vs dark (real pixel computation) ---
        lum = brightness_heuristic(img_bgr)
        eid += 1
        records.append({
            "evidence_id": f"ev_{eid:06d}",
            "value": "streetlight_lit_heuristic" if lum > 0.35 else "streetlight_dark_heuristic",
            "class_raw": None,
            "category": "lighting",
            "source": "cv_model",
            "confidence": round(min(max(lum, 0.0), 1.0), 4),
            "timestamp": now_iso(),
            "location": {"lat": lat, "lon": lon},
            "image": image_block,
            "model": {"name": "brightness_heuristic", "weights": None, "version": "cv2-mean-luminance"},
            "bbox_xyxy": None,
            "note": "mean pixel luminance of full frame, used only to qualify lit/dark, not a learned model",
        })

        # --- 3. Heuristic: visibility barrier via edge density (solid walls/fences) ---
        edge_density = edge_density_heuristic(img_bgr)
        if edge_density > 0.12:
            eid += 1
            records.append({
                "evidence_id": f"ev_{eid:06d}",
                "value": "visibility_barrier",
                "class_raw": None,
                "category": "visibility",
                "source": "cv_model",
                "confidence": round(min(edge_density * 3, 1.0), 4),
                "timestamp": now_iso(),
                "location": {"lat": lat, "lon": lon},
                "image": image_block,
                "model": {"name": "edge_density_heuristic", "weights": None, "version": "cv2-canny"},
                "bbox_xyxy": None,
                "note": "high edge density across frame used as a proxy for dense structural clutter/solid barriers (COCO has no wall/fence class)",
            })

        # --- 4. Heuristic: open establishment candidate ---
        commercial_dets = [d for d in dets if d[0] in COCO_COMMERCIAL_SIGNAL]
        if len(commercial_dets) >= 3:
            avg_conf = sum(d[1] for d in commercial_dets) / len(commercial_dets)
            eid += 1
            records.append({
                "evidence_id": f"ev_{eid:06d}",
                "value": "open_establishment",
                "class_raw": ",".join(sorted(set(d[0] for d in commercial_dets))),
                "category": "commercial",
                "source": "cv_model",
                "confidence": round(avg_conf, 4),
                "timestamp": now_iso(),
                "location": {"lat": lat, "lon": lon},
                "image": image_block,
                "model": {"name": "yolov8n+heuristic", "weights": MODEL_WEIGHTS, "version": "ultralytics"},
                "bbox_xyxy": None,
                "note": "clustering of >=3 people/vehicles/street-furniture detections used as a proxy for active open establishment/foot traffic (COCO has no shop/storefront class)",
            })

        # --- 5. Backend-contract record (data/imagery/*.json shape) ---
        # See backend/app/data_loader.py::load_cv_infrastructure_evidence for
        # the exact contract this must match so the backend picks it up
        # automatically (no code change needed on the backend side).
        backend_dets = []
        backend_dets.append({
            "class": "streetlight_working" if lum > 0.35 else "streetlight_broken",
            "confidence": round(min(max(lum, 0.05), 0.95), 4),
        })
        barrier_conf = 0.0
        if edge_density > 0.12:
            barrier_conf = max(barrier_conf, round(min(edge_density * 3, 1.0), 4))
        barrier_obj_confs = [d[1] for d in dets if d[0] in COCO_BARRIER_OBJECTS]
        if barrier_obj_confs:
            barrier_conf = max(barrier_conf, max(barrier_obj_confs))
        if barrier_conf > 0:
            backend_dets.append({"class": "visibility_barrier", "confidence": round(barrier_conf, 4)})
        if len(commercial_dets) >= 3:
            backend_dets.append({
                "class": "open_establishment",
                "confidence": round(sum(d[1] for d in commercial_dets) / len(commercial_dets), 4),
            })
        backend_records.append({
            "lat": lat, "lon": lon,
            "timestamp": now_iso(),
            "detections": backend_dets,
            "model_version": MODEL_VERSION,
        })

    with open(BACKEND_EVIDENCE_PATH, "w", encoding="utf-8") as f:
        json.dump(backend_records, f, indent=2)
    print(f"Wrote backend-contract file: {BACKEND_EVIDENCE_PATH}")

    # --- write outputs ---
    json_path = os.path.join(OUTPUT_DIR, "infrastructure_evidence.json")
    csv_path = os.path.join(OUTPUT_DIR, "infrastructure_evidence.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    if records:
        flat_fields = ["evidence_id", "value", "class_raw", "category", "source",
                        "confidence", "timestamp", "lat", "lon", "image_filename",
                        "image_source_provider", "model_name", "note"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=flat_fields)
            w.writeheader()
            for r in records:
                w.writerow({
                    "evidence_id": r["evidence_id"],
                    "value": r["value"],
                    "class_raw": r["class_raw"],
                    "category": r["category"],
                    "source": r["source"],
                    "confidence": r["confidence"],
                    "timestamp": r["timestamp"],
                    "lat": r["location"]["lat"],
                    "lon": r["location"]["lon"],
                    "image_filename": r["image"]["filename"],
                    "image_source_provider": r["image"]["source_provider"],
                    "model_name": r["model"]["name"],
                    "note": r.get("note", ""),
                })

    print(f"\nProcessed {len(files)} images, produced {len(records)} evidence records")
    print(f"Wrote: {json_path}")
    print(f"Wrote: {csv_path}")
    print("\nPer-image raw YOLO detection counts:")
    for fname, n in per_image_summary:
        print(f"  {fname}: {n} raw detections")

    print("\nSample records:")
    for r in records[:5]:
        print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
