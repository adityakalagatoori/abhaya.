"""
Runs generate_safety_insight() against a few realistic route_risk_context
examples (shaped like backend/app/models.py::RouteResponse's high_risk_factors /
total_risk fields) and writes side-by-side retrieved-text + generated-explanation
output to rag/examples/example_outputs.json and .md, per spec section 19
("show retrieved text and generated explanation side-by-side").
"""
from __future__ import annotations

import json
from pathlib import Path

from generate import generate_safety_insight

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "examples"

CASES = [
    {
        "label": "Night walk near Athwa riverfront, Surat (high structured risk)",
        "location": "Athwa Lines riverfront service road, Surat",
        "time": "2026-09-21T21:30:00+05:30",
        "route_risk_context": {
            "segments": [{"segment_id": "seg-4821", "description": "riverfront service road near Athwa, low commercial density, low lighting reported"}],
            "total_risk": 0.71,
            "high_risk_factors": ["low_lighting_reported_zone", "isolated_after_dark", "low_foot_traffic"],
        },
    },
    {
        "label": "Route near Surat railway station at night",
        "location": "Surat railway station approach road",
        "time": "2026-09-21T22:15:00+05:30",
        "route_risk_context": {
            "segments": [{"segment_id": "seg-1190", "description": "station approach road, moderate foot traffic, unverified lighting"}],
            "total_risk": 0.55,
            "high_risk_factors": ["station_adjacent", "night_travel"],
        },
    },
    {
        "label": "Daytime route in a well-documented low-risk area (should trigger uncertainty / low-grounding path)",
        "location": "Gopi Talav area, Surat",
        "time": "2026-09-21T11:00:00+05:30",
        "route_risk_context": {
            "segments": [{"segment_id": "seg-0042", "description": "family park frontage road, daytime, high foot traffic"}],
            "total_risk": 0.12,
            "high_risk_factors": [],
        },
    },
    {
        "label": "Different city (Bengaluru) -- corpus is India/Gujarat-crime themed so generic passages still clear threshold; shown to demonstrate the model is NOT told this is Surat-specific",
        "location": "MG Road, Bengaluru",
        "time": "2026-09-21T23:00:00+05:30",
        "route_risk_context": {
            "segments": [{"segment_id": "seg-9999", "description": "unmapped segment, no local evidence available"}],
            "total_risk": 0.4,
            "high_risk_factors": ["no_local_evidence"],
        },
    },
    {
        "label": "Fully out-of-domain query (must return honest uncertainty, no fabrication -- proves MIN_RELEVANCE_SCORE guardrail actually fires)",
        "location": "unspecified location",
        "time": "2026-09-21T12:00:00+05:30",
        "route_risk_context": {
            "segments": [{"segment_id": "seg-0000", "description": "restaurant menu pricing and weather forecast"}],
            "total_risk": 0.0,
            "high_risk_factors": ["cheese_supply_shortage", "average_rainfall_variance"],
        },
    },
]


def main():
    EXAMPLES_DIR.mkdir(exist_ok=True)
    outputs = []
    md_lines = ["# ABHAYA RAG — Example Outputs (retrieved text side-by-side with generated explanation)\n"]

    for case in CASES:
        result = generate_safety_insight(case["route_risk_context"], case["location"], case["time"])
        outputs.append({"case": case, "result": result})

        md_lines.append(f"## {case['label']}")
        md_lines.append(f"- **Location**: {case['location']}")
        md_lines.append(f"- **Time**: {case['time']}")
        md_lines.append(f"- **Structured risk context**: `{json.dumps(case['route_risk_context'])}`")
        md_lines.append(f"- **Generation backend used**: {result.get('_generation_backend', 'n/a (uncertainty path, no generation called)')}")
        md_lines.append(f"- **Grounded**: {result['grounded']}")
        md_lines.append("")
        md_lines.append("**Retrieved evidence (side A):**")
        if result["sources_used"]:
            for s in result["sources_used"]:
                md_lines.append(f"> [{s['score']:.3f}] {s['source']} ({s['timestamp']}, retrieved {s['retrieved']})")
                md_lines.append(f"> \"{s['text'][:300]}...\"")
                md_lines.append(">")
        else:
            md_lines.append("> (none above relevance threshold)")
        md_lines.append("")
        md_lines.append("**Generated explanation (side B):**")
        md_lines.append(f"> {result['explanation']}")
        if result["uncertainty_note"]:
            md_lines.append("")
            md_lines.append(f"**Uncertainty note:** {result['uncertainty_note']}")
        md_lines.append("\n---\n")

    (EXAMPLES_DIR / "example_outputs.json").write_text(
        json.dumps(outputs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (EXAMPLES_DIR / "example_outputs.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote {len(outputs)} examples to {EXAMPLES_DIR}")


if __name__ == "__main__":
    main()
