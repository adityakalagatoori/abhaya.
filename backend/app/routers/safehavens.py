from __future__ import annotations

import datetime
import time

from fastapi import APIRouter, Query

from app.data_loader import haversine_m, load_establishments
from app.models import SafeHaven, SafeHavensResponse

router = APIRouter()


def _is_open(open_hours: str, at_time: float) -> bool:
    if not open_hours or open_hours.lower() in ("unknown", ""):
        return False
    if open_hours.strip() == "24/7":
        return True
    try:
        start_s, end_s = open_hours.split("-")
        dt = datetime.datetime.fromtimestamp(at_time)
        start = dt.replace(hour=int(start_s.split(":")[0]), minute=int(start_s.split(":")[1]),
                            second=0, microsecond=0)
        end = dt.replace(hour=int(end_s.split(":")[0]), minute=int(end_s.split(":")[1]),
                         second=0, microsecond=0)
        return start <= dt <= end
    except (ValueError, IndexError):
        return False


@router.get("/safe-havens", response_model=SafeHavensResponse)
def get_safe_havens(lat: float = Query(...), lon: float = Query(...),
                     time_: float | None = Query(None, alias="time"),
                     radius: float = Query(400.0)):
    at_time = time_ or time.time()
    res = load_establishments()
    candidates = []
    for item in res.items:
        d = haversine_m(lat, lon, item["lat"], item["lon"])
        if d > radius:
            continue
        open_now = _is_open(item.get("open_hours", "unknown"), at_time)
        if not (item.get("verified") or open_now):
            continue
        candidates.append(SafeHaven(
            evidence_source=item["source_file"], name=item["name"], category=item["category"],
            lat=item["lat"], lon=item["lon"], distance_m=d,
            verified=bool(item.get("verified")), open_now=open_now,
        ))
    candidates.sort(key=lambda c: c.distance_m)
    return SafeHavensResponse(lat=lat, lon=lon, time=at_time, candidates=candidates,
                               data_source_status=res.status)
