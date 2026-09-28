"""
Road graph construction + time-aware, multi-criteria weighted router.

Implements spec sections 6.1 / 24.2:
  - road network as a networkx graph
  - each edge carries real risk factors (crime history, CV infrastructure
    evidence, time-of-travel) rather than one static score
  - risk for an edge is recomputed for the *expected arrival time* at that
    edge (running clock along the path), not a fixed value
  - objective: R = w1*Safety - w2*TimeDelay - w3*InfrastructureRisk
    implemented as edge cost = w_time*travel_time_s + w_infra*infra_risk*W_INFRA_SEC
                                 + w_safety*crime_and_context_risk*W_SAFETY_SEC
    i.e. a Dijkstra/A*-compatible additive cost where higher safety weight
    means risk is penalized more, expressed in "equivalent seconds" so the
    algorithm can run a standard shortest-path search.
"""
from __future__ import annotations

import bisect
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import networkx as nx

from shapely.geometry import Point, shape
from shapely.prepared import prep

from app.config import DEFAULT_WEIGHTS, ROAD_NETWORK_DIR
from app.data_loader import (haversine_m, load_crime_records, load_cv_infrastructure_evidence,
                              load_district_crime_polygons)
from app.models import EvidenceRecord, EvidenceSource, RiskFactorBreakdown, RiskState

# Converts a normalized 0..1 risk unit into "equivalent seconds" of cost so
# it combines additively with real travel-time seconds in one shortest-path
# weight. Tunable; large enough that safety differences are meaningful
# against a walk of a few hundred meters.
RISK_TO_SECONDS = 400.0

WALK_SPEED_MPS = 1.35
DRIVE_SPEED_MPS = 8.3  # ~30 km/h urban default when road doesn't specify maxspeed

NIGHT_START_HOUR = 19
NIGHT_END_HOUR = 6

# Spatial index bucket size in degrees (~111m at equator per 0.001deg lat)
BUCKET_SIZE = 0.003


class SpatialBucketIndex:
    """Cheap grid-based spatial index over point evidence, used instead of
    PostGIS ST_DWithin (documented substitution, see app/config.py)."""

    def __init__(self):
        self._buckets: dict[tuple[int, int], list[dict]] = {}

    @staticmethod
    def _key(lat: float, lon: float) -> tuple[int, int]:
        return (int(lat / BUCKET_SIZE), int(lon / BUCKET_SIZE))

    def add(self, lat: float, lon: float, payload: dict):
        self._buckets.setdefault(self._key(lat, lon), []).append({**payload, "lat": lat, "lon": lon})

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[dict]:
        span = max(1, int(radius_m / (BUCKET_SIZE * 111_000)) + 1)
        kx, ky = self._key(lat, lon)
        results = []
        for dx in range(-span, span + 1):
            for dy in range(-span, span + 1):
                for item in self._buckets.get((kx + dx, ky + dy), []):
                    d = haversine_m(lat, lon, item["lat"], item["lon"])
                    if d <= radius_m:
                        results.append({**item, "distance_m": d})
        return results


@dataclass
class RoadGraph:
    graph: nx.MultiDiGraph = field(default_factory=nx.MultiDiGraph)
    crime_index: SpatialBucketIndex = field(default_factory=SpatialBucketIndex)
    cv_index: SpatialBucketIndex = field(default_factory=SpatialBucketIndex)
    district_crime_polygons: list[tuple[object, object, float, str]] = field(default_factory=list)
    evidence_store: dict[str, EvidenceRecord] = field(default_factory=dict)
    load_status: dict[str, str] = field(default_factory=dict)
    source: str = "none"
    # In-process route cache, lives for the server's lifetime. Real road/risk
    # data doesn't change while the process runs, so an identical (origin,
    # destination, mode, weights, minute-bucketed depart time) request is
    # genuinely the same computation -- caching it is not an approximation.
    # Added specifically because a real cross-city route was measured taking
    # 40s+ on a CPU-throttled free-tier host (0.6s locally); this doesn't fix
    # the first computation, but makes every repeat of the same demo route
    # (e.g. rehearsing/re-recording a walkthrough) instant afterward.
    _route_cache: dict = field(default_factory=dict)

    # ---------------- construction ----------------

    @classmethod
    def build(cls) -> "RoadGraph":
        rg = cls()
        rg._load_road_network()
        rg._load_crime()
        rg._load_district_crime()
        rg._load_cv_evidence()
        return rg

    def _load_road_network(self):
        files = sorted(list(ROAD_NETWORK_DIR.glob("*.graphml"))) if ROAD_NETWORK_DIR.exists() else []
        geo_files = sorted(list(ROAD_NETWORK_DIR.glob("*.geojson"))) if ROAD_NETWORK_DIR.exists() else []

        if files:
            for f in files:
                try:
                    g = nx.read_graphml(f)
                    self.graph = nx.compose(self.graph, nx.MultiDiGraph(g))
                except Exception as e:  # noqa: BLE001
                    self.load_status[str(f)] = f"FAILED_TO_PARSE: {e}"
            if self.graph.number_of_edges() > 0:
                self.source = "graphml"
                self._normalize_graphml_attrs()
                self.load_status["status"] = "ok"
                return

        if geo_files:
            for f in geo_files:
                try:
                    self._load_geojson_roads(f)
                except Exception as e:  # noqa: BLE001
                    self.load_status[str(f)] = f"FAILED_TO_PARSE: {e}"
            if self.graph.number_of_edges() > 0:
                self.source = "geojson"
                self.load_status["status"] = "ok"
                return

        self.load_status["status"] = (
            f"NO_ROAD_NETWORK_DATA: expected .graphml or .geojson files in {ROAD_NETWORK_DIR}. "
            "Router will return 503 on /route until real road network data is provided by the "
            "data-sourcing agent. See app/data_loader.py docstring for the exact expected format."
        )
        self.source = "none"

    def _normalize_graphml_attrs(self):
        """OSMnx graphml stores node coords as y/x; normalize to lat/lon and
        edge length/highway/lit attributes to consistent python types."""
        for n, data in self.graph.nodes(data=True):
            if "lat" not in data:
                if "y" in data and "x" in data:
                    data["lat"] = float(data["y"])
                    data["lon"] = float(data["x"])
        for u, v, k, data in self.graph.edges(keys=True, data=True):
            if "length" in data:
                try:
                    data["length"] = float(data["length"])
                except (TypeError, ValueError):
                    data["length"] = self._geo_length(u, v)
            else:
                data["length"] = self._geo_length(u, v)
            data.setdefault("highway", "unknown")
            data.setdefault("lit", "unknown")
            data.setdefault("name", data.get("name", "unnamed"))

    def _geo_length(self, u, v) -> float:
        try:
            nu, nv = self.graph.nodes[u], self.graph.nodes[v]
            return haversine_m(nu["lat"], nu["lon"], nv["lat"], nv["lon"])
        except KeyError:
            return 50.0

    def _load_geojson_roads(self, path: Path):
        # utf-8-sig strips a leading BOM if present (common in files saved by
        # some Windows/Overpass export tools) and behaves like plain utf-8
        # when there is no BOM, so this is safe for both cases.
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for i, feat in enumerate(data.get("features", [])):
            geom = feat.get("geometry", {})
            if geom.get("type") != "LineString":
                continue
            coords = geom["coordinates"]  # [ [lon,lat], ... ]
            props = feat.get("properties", {})
            for j in range(len(coords) - 1):
                lon1, lat1 = coords[j]
                lon2, lat2 = coords[j + 1]
                n1, n2 = f"{lat1:.6f},{lon1:.6f}", f"{lat2:.6f},{lon2:.6f}"
                self.graph.add_node(n1, lat=lat1, lon=lon1)
                self.graph.add_node(n2, lat=lat2, lon=lon2)
                length = haversine_m(lat1, lon1, lat2, lon2)
                attrs = dict(length=length, highway=props.get("highway", "unknown"),
                             lit=props.get("lit", "unknown"),
                             name=props.get("name", f"way_{i}"))
                self.graph.add_edge(n1, n2, **attrs)
                self.graph.add_edge(n2, n1, **attrs)

    def _load_crime(self):
        res = load_crime_records()
        self.load_status["crime"] = res.status
        for rec in res.items:
            ev = EvidenceRecord(
                source=EvidenceSource.CRIME_HISTORY, factor="crime_incident",
                value=rec["severity"], raw_value=rec["category"],
                confidence=0.6, timestamp=rec["timestamp"] or time.time(),
                lat=rec["lat"], lon=rec["lon"],
                description=f"{rec['category']} (source: {rec['source_file']})",
            )
            self.evidence_store[ev.id] = ev
            self.crime_index.add(ev.lat, ev.lon, {"evidence_id": ev.id, "severity": rec["severity"]})

    def _load_district_crime(self):
        res = load_district_crime_polygons()
        self.load_status["district_crime"] = res.status
        for rec in res.items:
            try:
                poly = shape(rec["geometry"])
            except (ValueError, AttributeError):
                continue
            # Real admin-boundary polygons from Nominatim/OSM can carry
            # thousands of vertices (Surat's is 7,517) -- a plain, unprepared
            # `.contains()` check is O(vertices) per call, and this function
            # is called for EVERY edge evaluated during routing (potentially
            # 100k+ times per /route request), which was measured to make a
            # real cross-city route request exceed 60s on a constrained CPU.
            # A light simplify (tolerance ~55m, negligible for a
            # district-level risk boundary) plus shapely's prepared geometry
            # (builds an internal spatial index once) fixes this: prepared
            # `.contains()` is effectively O(log n) per call instead of O(n).
            simplified = poly.simplify(0.0005, preserve_topology=True)
            prepared = prep(simplified)
            self.district_crime_polygons.append((prepared, simplified, rec["crime_index"], rec["district"]))

    def district_crime_factor(self, lat: float, lon: float) -> float:
        """Real, honestly coarse district-level baseline (see
        load_district_crime_polygons docstring): every point inside a real
        district boundary gets that district's real crime_index, since no
        finer-grained real point-level crime dataset exists publicly for
        India. Returns 0.0 for points outside every loaded district polygon.
        """
        if not self.district_crime_polygons:
            return 0.0
        pt = Point(lon, lat)
        for prepared, poly, idx, _district in self.district_crime_polygons:
            if prepared.contains(pt) or prepared.intersects(pt):
                return idx
        return 0.0

    def _load_cv_evidence(self):
        res = load_cv_infrastructure_evidence()
        self.load_status["cv_infrastructure"] = res.status
        risky_classes = {"streetlight_broken": 0.7, "visibility_barrier": 0.8}
        safe_classes = {"streetlight_working": -0.3, "open_establishment": -0.2}
        for rec in res.items:
            cls = rec["class"]
            weight = risky_classes.get(cls, safe_classes.get(cls, 0.0))
            ev = EvidenceRecord(
                source=EvidenceSource.CV_INFRASTRUCTURE, factor=cls,
                value=max(0.0, min(1.0, 0.5 + weight)), confidence=rec["confidence"],
                timestamp=rec["timestamp"] or time.time(), lat=rec["lat"], lon=rec["lon"],
                description=f"CV detection {cls} (model {rec['model_version']})",
            )
            self.evidence_store[ev.id] = ev
            self.cv_index.add(ev.lat, ev.lon, {"evidence_id": ev.id, "class": cls, "weight": weight,
                                                "confidence": rec["confidence"]})

    # ---------------- risk scoring ----------------

    def is_night(self, ts: float) -> bool:
        hour = time.localtime(ts).tm_hour
        return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR

    def edge_risk_state(self, u: str, v: str, key, data: dict, arrival_time: float) -> RiskState:
        """Time-aware risk for one edge, evaluated for `arrival_time`."""
        lat1, lon1 = self.graph.nodes[u]["lat"], self.graph.nodes[u]["lon"]
        lat2, lon2 = self.graph.nodes[v]["lat"], self.graph.nodes[v]["lon"]
        mid_lat, mid_lon = (lat1 + lat2) / 2, (lon1 + lon2) / 2

        evidence_ids: list[str] = []

        # crime_history factor: nearby POINT incidents (if any exist) weighted
        # by recency & severity, combined with the real district-level annual
        # baseline (see district_crime_factor) -- point evidence refines the
        # estimate above the district baseline rather than replacing it, since
        # both are real, just at different resolutions.
        crime_hits = self.crime_index.query_radius(mid_lat, mid_lon, 80.0)
        point_crime_factor = 0.0
        for h in crime_hits:
            recency_weight = 1.0  # timestamps may be historical; treat as base rate evidence
            point_crime_factor += h["severity"] * recency_weight / (1 + h["distance_m"] / 40.0)
            evidence_ids.append(h["evidence_id"])
        point_crime_factor = min(1.0, point_crime_factor)
        district_factor = self.district_crime_factor(mid_lat, mid_lon)
        crime_factor = min(1.0, max(point_crime_factor, district_factor))

        # infrastructure_condition / visibility factor from CV evidence
        cv_hits = self.cv_index.query_radius(mid_lat, mid_lon, 60.0)
        infra_factor = 0.0
        activity_factor = 0.0
        for h in cv_hits:
            contrib = max(0.0, h["weight"]) * h["confidence"]
            reduction = max(0.0, -h["weight"]) * h["confidence"]
            infra_factor += contrib / (1 + h["distance_m"] / 30.0)
            activity_factor += reduction / (1 + h["distance_m"] / 30.0)
            evidence_ids.append(h["evidence_id"])
        infra_factor = min(1.0, infra_factor)
        activity_factor = min(1.0, activity_factor)

        # OSM lit attribute as a weak infrastructure prior when no CV evidence exists
        lit = str(data.get("lit", "unknown")).lower()
        if lit == "no":
            infra_factor = min(1.0, infra_factor + 0.3)
        elif lit == "yes":
            infra_factor = max(0.0, infra_factor - 0.15)

        # time_of_travel factor: night penalty, compounds with low infra/activity
        night = self.is_night(arrival_time)
        time_factor = 0.35 if night else 0.05
        if night and infra_factor > 0.3:
            time_factor += 0.15  # dark + poor infra is worse than either alone

        factors = RiskFactorBreakdown(
            crime_history=crime_factor,
            infrastructure_condition=infra_factor,
            activity_level=activity_factor,
            reports=0.0,  # wired once user_report evidence source is populated
            time_of_travel=time_factor,
            nearby_safety_context=0.0,
        )
        risk_score = min(1.0, max(0.0,
            0.35 * factors.crime_history + 0.30 * factors.infrastructure_condition
            + 0.20 * factors.time_of_travel - 0.10 * factors.activity_level
            - 0.05 * factors.nearby_safety_context
        ))

        seg_id = f"{u}->{v}"
        return RiskState(
            segment_id=seg_id, lat=mid_lat, lon=mid_lon, evaluated_for_time=arrival_time,
            factors=factors, risk_score=risk_score, evidence_ids=list(dict.fromkeys(evidence_ids)),
        )

    def edge_speed_mps(self, data: dict, mode: str) -> float:
        if mode == "walk":
            return WALK_SPEED_MPS
        highway = str(data.get("highway", "unknown")).lower()
        base = {"motorway": 16.6, "trunk": 13.8, "primary": 11.1, "secondary": 9.7,
                "tertiary": 8.3, "residential": 6.9, "unknown": DRIVE_SPEED_MPS}
        return base.get(highway, DRIVE_SPEED_MPS)

    # ---------------- routing ----------------

    def route(self, origin: tuple[float, float], destination: tuple[float, float],
              depart_time: float, mode: str, w_safety: float, w_time: float,
              w_infra: float) -> Optional[dict]:
        if self.graph.number_of_edges() == 0:
            return None

        cache_key = (
            round(origin[0], 6), round(origin[1], 6),
            round(destination[0], 6), round(destination[1], 6),
            mode, round(w_safety, 4), round(w_time, 4), round(w_infra, 4),
            round(depart_time / 60.0),  # minute-bucketed -- see class docstring
        )
        if cache_key in self._route_cache:
            return self._route_cache[cache_key]

        o_node = self._nearest_node(*origin)
        d_node = self._nearest_node(*destination)
        if o_node is None or d_node is None:
            return None

        # We run a time-dependent Dijkstra manually (networkx's built-in
        # dijkstra assumes static weights) so that edge risk is evaluated
        # for the actual expected arrival time at that edge, per section 24.2.
        import heapq
        dist: dict[str, float] = {o_node: 0.0}
        arrival: dict[str, float] = {o_node: depart_time}
        risk_accum: dict[str, float] = {o_node: 0.0}
        time_accum: dict[str, float] = {o_node: 0.0}
        prev: dict[str, tuple[str, int, RiskState]] = {}
        visited: set[str] = set()
        pq = [(0.0, o_node)]

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == d_node:
                break
            for v in self.graph.successors(u):
                for k, edata in self.graph.get_edge_data(u, v).items():
                    speed = self.edge_speed_mps(edata, mode)
                    length = edata.get("length", 50.0)
                    travel_s = length / max(speed, 0.1)
                    edge_arrival = arrival[u] + travel_s
                    rstate = self.edge_risk_state(u, v, k, edata, edge_arrival)
                    cost = (w_time * travel_s
                            + w_infra * rstate.factors.infrastructure_condition * RISK_TO_SECONDS
                            + w_safety * rstate.risk_score * RISK_TO_SECONDS)
                    nd = d + cost
                    if nd < dist.get(v, math.inf):
                        dist[v] = nd
                        arrival[v] = edge_arrival
                        risk_accum[v] = risk_accum[u] + rstate.risk_score
                        time_accum[v] = time_accum[u] + travel_s
                        prev[v] = (u, k, rstate)
                        heapq.heappush(pq, (nd, v))

        if d_node not in prev and d_node != o_node:
            return None

        # reconstruct path
        path_nodes = [d_node]
        edge_states: list[tuple[str, str, RiskState, dict]] = []
        cur = d_node
        while cur != o_node:
            if cur not in prev:
                return None
            u, k, rstate = prev[cur]
            edata = self.graph.get_edge_data(u, cur)[k]
            edge_states.append((u, cur, rstate, edata))
            path_nodes.append(u)
            cur = u
        edge_states.reverse()
        path_nodes.reverse()

        total_distance = sum(e[3].get("length", 0.0) for e in edge_states)
        total_time = time_accum.get(d_node, 0.0)
        total_risk = risk_accum.get(d_node, 0.0)
        objective = w_safety * (1 - (total_risk / max(1, len(edge_states)))) \
            - w_time * total_time - w_infra * total_risk

        computed = {
            "edge_states": edge_states,
            "total_distance_m": total_distance,
            "total_time_s": total_time,
            "total_risk": total_risk,
            "objective_value": objective,
        }
        self._route_cache[cache_key] = computed
        return computed

    def route_fastest(self, origin, destination, mode: str) -> Optional[dict]:
        """Comparison baseline: pure shortest-time route, ignoring risk,
        used by /route to show the safety/time trade-off (section 19)."""
        return self.route(origin, destination, time.time(), mode,
                           w_safety=0.0, w_time=1.0, w_infra=0.0)

    def _nearest_node(self, lat: float, lon: float) -> Optional[str]:
        best, best_d = None, math.inf
        for n, data in self.graph.nodes(data=True):
            if "lat" not in data:
                continue
            d = haversine_m(lat, lon, data["lat"], data["lon"])
            if d < best_d:
                best, best_d = n, d
        return best

    # ---------------- explainability helpers ----------------

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        return self.evidence_store.get(evidence_id)


_ROAD_GRAPH_SINGLETON: Optional[RoadGraph] = None


def get_road_graph() -> RoadGraph:
    global _ROAD_GRAPH_SINGLETON
    if _ROAD_GRAPH_SINGLETON is None:
        _ROAD_GRAPH_SINGLETON = RoadGraph.build()
    return _ROAD_GRAPH_SINGLETON


def reload_road_graph() -> RoadGraph:
    global _ROAD_GRAPH_SINGLETON
    _ROAD_GRAPH_SINGLETON = RoadGraph.build()
    return _ROAD_GRAPH_SINGLETON
