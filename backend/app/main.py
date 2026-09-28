from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import (companions, infrastructure, route, routeguard, safedrop, safehavens,
                          safety_insight, transitguard, walkguard)

app = FastAPI(
    title="ABHAYA Backend",
    description="Dynamic risk-aware navigation, SafeDrop, RouteGuard, WalkGuard API. "
                "See README.md for the data contract each endpoint expects.",
    version="0.1.0",
)

# The frontend is deployed on a different origin (Vercel) than this backend
# (Render), so the browser build (Expo web) needs CORS explicitly allowed.
# The native app (Expo Go / a built APK) isn't subject to CORS at all -- this
# only matters for the web deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # prototype-scope: no cookies/credentials are used, so a wildcard is safe here
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


app.include_router(route.router, tags=["route"])
app.include_router(infrastructure.router, tags=["infrastructure"])
app.include_router(safedrop.router, tags=["safedrop"])
app.include_router(routeguard.router, tags=["routeguard"])
app.include_router(walkguard.router, tags=["walkguard"])
app.include_router(safehavens.router, tags=["safe-havens"])
app.include_router(safety_insight.router, tags=["safety-insight"])
app.include_router(companions.router, tags=["companions"])
app.include_router(transitguard.router, tags=["transitguard"])


@app.get("/health")
def health():
    from app.graph import get_road_graph
    rg = get_road_graph()
    return {
        "status": "ok",
        "road_graph_edges": rg.graph.number_of_edges(),
        "road_graph_source": rg.source,
        "data_status": rg.load_status,
    }
