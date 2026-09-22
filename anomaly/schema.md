# Behavioural-Anomaly Module — Input/Output Schema

The ABHAYA backend (`backend/app/routers`) does not yet expose
`/walkguard/event` or `/routeguard/check` implementations (checked at
build time — only `backend/app/routers` scaffolding exists, no schema to
match against). This document is therefore the **authoritative contract**
this module expects those routers to use when they call
`evaluate.evaluate_motion`.

## Function

```python
from evaluate import evaluate_motion

result = evaluate_motion(sensor_window, risk_context, detector_state)
```

## Input

### `sensor_window: list[dict]` (required)

A chronologically-ordered batch of raw samples from ONE journey's live
sensor stream, as sent by the React Native app (`expo-sensors` /
`react-native-sensors` Accelerometer + Gyroscope). Recommended batch size:
2-5 seconds of samples per call (e.g. WalkGuard/RouteGuard polling
cadence), minimum 3 samples.

```jsonc
[
  {
    "t": 1732000000123,       // unix ms, required
    "ax": 0.21, "ay": 9.79, "az": 0.31,   // accelerometer, m/s^2, required
    "gx": 0.01, "gy": -0.02, "gz": 0.00   // gyroscope, rad/s, OPTIONAL
  },
  ...
]
```

Gyroscope fields are optional per spec 6.4 ("combine with accelerometer"
when available) — the detector runs on accelerometer alone if `gx/gy/gz`
are absent, and simply does not populate `gyro_*` features.

### `risk_context: dict | None` (optional, defaults to "no elevated risk")

Supplied by the SAME risk engine that powers navigation / RouteGuard /
SafeDrop (spec section 25 "Risk State" / "Journey State" shared objects).
This module does **not** compute risk itself — it only asks whether the
current segment/location is materially worse.

```jsonc
{
  "risk_score": 0.35,               // 0..1 current-segment risk, from Risk State
  "route_deviation": false,          // RouteGuard: vehicle/user left expected corridor
  "on_expected_walk_route": true,    // WalkGuard: still on the expected final-walk path
  "checkin_acknowledged": false,     // user answered the discreet check-in prompt
  "seconds_since_candidate": 0       // wall-clock seconds since the candidate streak began
}
```

### `detector_state: dict | None` (optional; None on a journey's first call)

Opaque state blob returned by the previous call for this journey (journey
id keyed by the caller, e.g. stored alongside the existing Journey State
record). Passing it back lets a stateless FastAPI handler continue the same
baseline + persistence streak across HTTP requests.

## Output

```jsonc
{
  "anomaly_state": "NORMAL",   // NORMAL | ANOMALY_CANDIDATE | CAUTION | ESCALATED
  "reasons": [],                 // subset of ["running_like","sudden_stop_like","erratic_like"]
  "consecutive_candidate_windows": 0,
  "baseline_ready": true,
  "z_scores": { "accel_mean_mag": 0.1, "...": "..." },
  "risk_context_elevated": false,
  "features": { "...": "MotionFeatures fields, for logging/debugging" },
  "detector_state": { "...": "pass back verbatim on the next call" }
}
```

### `anomaly_state` values and what the backend should do

| State | Meaning | Suggested backend action |
|---|---|---|
| `NORMAL` | Motion matches this journey's baseline | none |
| `ANOMALY_CANDIDATE` | This window (or a short streak) deviates from baseline (running-like / sudden-stop-like / erratic), but has not persisted, or risk context does not align | log only; do not notify |
| `CAUTION` | Deviation has persisted for >= `persistence_windows` consecutive windows AND risk context is elevated | trigger the existing discreet one-tap check-in flow (spec 7.2 Level 1) |
| `ESCALATED` | `CAUTION` persisted past `escalation_timeout_s` with no `checkin_acknowledged` | trigger the existing critical alert/telemetry-share workflow (spec 7.2 Level 2) |

`/walkguard/event` and `/routeguard/check` should call `evaluate_motion`
once per incoming sensor batch, persist the returned `detector_state`
against the journey record, and act on `anomaly_state` using the table
above. Neither endpoint needs its own copy of the persistence/risk-gating
logic — that is the point of this shared module.
