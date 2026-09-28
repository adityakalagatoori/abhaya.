"""
Real place-name search proxy for the web frontend.

Nominatim (OpenStreetMap's free geocoder) doesn't send CORS headers, so the
web-deployed frontend's browser blocks direct fetch() calls to it outright
(confirmed live: curl succeeds, browser fetch does not -- this is a browser
CORS policy, not a Nominatim outage). Native builds aren't subject to CORS
and could call Nominatim directly, but routing everything through this
backend proxy keeps one code path for both. This endpoint does nothing but
forward the query and results -- no fabrication, same real Nominatim data,
same usage-policy identifying User-Agent.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ABHAYA-safety-navigation-app/1.0 (hackathon prototype)"


@router.get("/geocode/search")
async def geocode_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=10),
    bias_lat: float | None = Query(None),
    bias_lon: float | None = Query(None),
):
    params = {"q": q, "format": "jsonv2", "limit": str(limit), "addressdetails": "0"}
    if bias_lat is not None and bias_lon is not None:
        delta = 0.5
        params["viewbox"] = f"{bias_lon - delta},{bias_lat + delta},{bias_lon + delta},{bias_lat - delta}"
        params["bounded"] = "0"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(NOMINATIM_SEARCH_URL, params=params, headers={"User-Agent": USER_AGENT})
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach the place-search service: {e}")

    if res.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Place search failed: {res.status_code}")

    data = res.json()
    return [
        {"label": r.get("display_name"), "lat": float(r["lat"]), "lon": float(r["lon"])}
        for r in data
    ]
