"""
Demo bus fleet compliance records -- NO real bus operator telemetry
integration exists anywhere for this project. No public data source
publishes real-time, per-vehicle tracking-device status, panic-button
status, curtain/visibility compliance or lighting status for individual
buses -- state transport departments publish only the *policy* (see
rag/corpus/008_delhi_bus_safety_2026_nhrc_transport_dept.txt for the real,
sourced Delhi Transport Department directive text), not machine-readable
per-vehicle telemetry.

These records are CLEARLY LABELED demo/placeholder data (per the task's
hard rule and the existing app/data_loader.py honesty pattern: real data
where real data can exist, honestly-labeled demo data only where it
cannot). The field *names* are real -- they map directly onto the real
compliance categories named in the Delhi Transport Department's
September 2026 directive (tracking devices, panic buttons, no curtains/
obstructive films, adequate lighting, authorised stops) -- but the
*values* for any specific vehicle_id below are fabricated placeholders,
structured exactly as a real operator/RTO telemetry API would be expected
to shape them, so that swapping in a real integration later requires no
schema change.

GET /bus/safety-status must always set data_source_status to a string
that makes this explicit (see app/routers/transitguard.py) -- it must
never be presented as live data.
"""
from __future__ import annotations

DEMO_BUS_FLEET: dict[str, dict] = {
    "DL1PC1234": {
        "vehicle_id": "DL1PC1234",
        "operator": "Demo Transport Co-op",
        "route_name": "Greater Noida - Kashmere Gate (demo)",
        "tracking_active": True,
        "panic_button_functional": True,
        "visibility_compliant": True,   # no curtains/tinted film reported
        "lighting_adequate": True,
        "authorised_stops": ["Pari Chowk", "Sector 62", "Akshardham", "Kashmere Gate"],
        "last_inspected": "2026-09-15",
    },
    "UP16XX9988": {
        "vehicle_id": "UP16XX9988",
        "operator": "Demo Sleeper Lines",
        "route_name": "Mainpuri - Delhi (demo, sleeper class)",
        "tracking_active": False,   # demo: tracking device reported non-functional
        "panic_button_functional": False,
        "visibility_compliant": False,  # demo: curtains present, non-compliant
        "lighting_adequate": False,
        "authorised_stops": ["Mainpuri", "Etah", "Ghaziabad", "Kashmere Gate"],
        "last_inspected": "2026-07-02",
    },
    "DL1PD5566": {
        "vehicle_id": "DL1PD5566",
        "operator": "Demo City Transit",
        "route_name": "Dwarka - Connaught Place (demo)",
        "tracking_active": True,
        "panic_button_functional": True,
        "visibility_compliant": True,
        "lighting_adequate": False,   # demo: one internal light reported broken
        "authorised_stops": ["Dwarka Sec 21", "Rajouri Garden", "Connaught Place"],
        "last_inspected": "2026-09-20",
    },
    "HR26AB4321": {
        "vehicle_id": "HR26AB4321",
        "operator": "Demo Intercity Coaches",
        "route_name": "Gurugram - Noida (demo)",
        "tracking_active": True,
        "panic_button_functional": False,  # demo: panic button reported non-functional
        "visibility_compliant": True,
        "lighting_adequate": True,
        "authorised_stops": ["Gurugram Sec 29", "Ambience Mall", "Noida Sector 18"],
        "last_inspected": "2026-08-30",
    },
}

DEMO_DATA_SOURCE_STATUS = (
    "DEMO_BUS_FLEET_DATA: no real bus-operator telemetry integration exists; "
    "these are clearly-labeled placeholder compliance records (structure matches "
    "what a real operator/RTO API would provide) for demo vehicle_ids only. "
    "The compliance categories are drawn from the real Delhi Transport Department "
    "September 2026 directive (see rag/corpus/008_delhi_bus_safety_2026_nhrc_transport_dept.txt); "
    "the per-vehicle values are fabricated for demonstration and must never be "
    "treated as live safety data."
)
