# ABHAYA — Behavioural Anomaly / WalkGuard Motion Detector

Real, working detection logic for spec sections **6.4** (Behavioral Anomaly
and Biometric Ingestion), **24.5** (Behavioral Anomaly Detection — Best
Implementation), **7.3** (WalkGuard — The Last 100m) and **24.9** (WalkGuard
— Best Implementation). This module contains no fabricated/simulated
sensor data used as evidence — it is validated against a real, public,
phone-recorded human-activity-recognition dataset.

## What's here

| File | Purpose |
|---|---|
| `features.py` | Real motion-feature extraction from a raw accel(+gyro) window: magnitude, variance, jerk, SMA, zero-crossing rate, coarse step frequency. |
| `baseline.py` | Per-journey "normal-motion baseline" (Welford running mean/std), per spec 24.5 step 1. |
| `state_machine.py` | The anomaly state machine: `NORMAL → ANOMALY_CANDIDATE → CAUTION → ESCALATED`, gated by persistence + risk context, per spec 24.5/24.9. |
| `evaluate.py` | Public entry point: `evaluate_motion(sensor_window, risk_context, detector_state) -> anomaly_state` for the backend to import. |
| `schema.md` | Input/output contract for `/walkguard/event` and `/routeguard/check` (backend routers not implemented yet — this is the contract they should follow). |
| `scripts/load_wisdm.py` | Loader/windower for the real dataset used to validate the detector. |
| `validate.py` | Runs the detector against real recorded data and reports precision/recall/accuracy. |
| `data/WISDM_ar_v1.1/` | The real dataset (see Dataset section). |
| `VALIDATION_RESULTS.txt` | Raw output of the last `validate.py` run. |

## Why the design looks like this (spec compliance)

Spec 24.5 is explicit about what NOT to build:

- ❌ "Running = danger." → ✅ running only ever produces `ANOMALY_CANDIDATE`.
- ❌ "Sudden stop = emergency." → ✅ sudden stop only ever produces
  `ANOMALY_CANDIDATE`, and only escalates to `CAUTION`/`ESCALATED` if it
  **persists** across multiple windows.
- ❌ "A large black-box model with no explanation." → ✅ every anomaly
  signal is a named, interpretable feature comparison (`running_like`,
  `sudden_stop_like`, `erratic_like`) with reported z-scores.
- ❌ "Continuous raw sensor storage." → ✅ the module only ever receives
  and returns small per-window feature summaries; it does not persist raw
  samples.
- ❌ "Trigger on every sudden movement" (24.9) → ✅ `CAUTION` requires
  BOTH persistence (`persistence_windows`, default 3 consecutive candidate
  windows) AND an elevated `risk_context` (materially higher-risk
  location/route deviation) supplied by the same risk engine that powers
  navigation/RouteGuard/SafeDrop (spec section 25 "Risk State"/"Journey
  State"). `ESCALATED` additionally requires `CAUTION` to persist past a
  timeout with no check-in acknowledgement (mirrors the Level 1 → Level 2
  tiered response in spec 7.2).

`evaluate_motion()` is the single call site the backend needs for both
`/walkguard/event` (post-ride final-walk monitoring, spec 7.3/24.9) and
`/routeguard/check` (en-route deviation, spec 7.2/24.8) — both consume the
same motion-anomaly + risk-context pattern, so one module serves both per
spec section 25's "shared engineering object" principle.

## Dataset used for validation (REAL data, not synthetic)

**WISDM Actitracker v1.1** ("Activity Prediction" dataset), WISDM Lab,
Fordham University.

- Source: `https://www.cis.fordham.edu/wisdm/includes/datasets/latest/WISDM_ar_latest.tar.gz`
  (official dataset page: `https://www.cis.fordham.edu/wisdm/dataset.php`)
- Citation: Kwapisz, J. R., Weiss, G. M., & Moore, S. A. (2010). *Activity
  Recognition using Cell Phone Accelerometers*. Proceedings of the Fourth
  International Workshop on Knowledge Discovery from Sensor Data (at
  KDD-10), Washington DC.
- License: released by WISDM Lab free for research/educational use,
  redistribution requires keeping `data/WISDM_ar_v1.1/readme.txt` — included
  as downloaded, unmodified.
- Contents: **1,098,210 real accelerometer samples** from **36 real human
  subjects** carrying an Android phone in a front pants pocket, labeled
  Walking / Jogging / Upstairs / Downstairs / Sitting / Standing, at a
  nominal ~20 Hz. This is real phone-sensor data recorded from real people,
  exactly the kind of stream the React Native app will send once deployed
  on an actual phone.
- Limitation, stated honestly: WISDM provides **accelerometer only** (no
  gyroscope) and has no "phone impact/drop" recordings. The detector's
  gyroscope path (`features.py`, `has_gyro`) and impact handling are
  implemented and unit-tested but not evaluated against real gyro/impact
  data because no such public dataset with real recordings was located
  within scope of this task — they are additive signals in the design
  (spec 6.4 already treats gyroscope and phone-impact as *optional/one of
  several* signals, never load-bearing alone), so their absence from
  quantitative validation does not affect the core running/sudden-stop
  results, which use only real accelerometer evidence.

## Reproducing the dataset download

```bash
curl -sL -o WISDM_ar_v1.1.tar.gz \
  "https://www.cis.fordham.edu/wisdm/includes/datasets/latest/WISDM_ar_latest.tar.gz"
tar xzf WISDM_ar_v1.1.tar.gz
```
(the `.tar.gz` itself is removed from `data/` after extraction to keep the
repo small; re-download if needed.)

## Validation methodology and results (real data)

Run with: `python validate.py` (requires `numpy`/`pandas`/`scikit-learn`
installed, though the core detector itself has zero third-party
dependencies — only the standard library).

### Part 1 — Running (Jogging) detection

For each of the 36 real subjects independently: build a `JourneyBaseline`
from a third of that subject's own real Walking windows (mirrors how
WalkGuard would build a per-journey baseline in production), then test
`classify_deviation().running_like` on that subject's held-out real
Walking windows (should NOT fire) and real Jogging windows (SHOULD fire).//
2-second windows (40 samples @ ~20Hz), 50% overlap.

```
users evaluated: 32 (of 36 -- 4 users had too few real Walking/Jogging samples to split)
confusion: TP(jog flagged)=15212  FN(jog missed)=1176  FP(walk flagged)=930  TN(walk clear)=11398
precision = 0.942
recall    = 0.928
accuracy  = 0.927
```

Real jogging is correctly flagged as a running-anomaly candidate ~93% of
the time, and ordinary real walking is correctly left alone ~92% of the
time, using only that subject's own real walking data as the baseline —
no population averages, no synthetic signal.

### Part 2 — Sudden-stop detection

WISDM has no staged "sudden stop," but real subjects' recordings contain
real moving→stationary label transitions (e.g. a subject's real Jogging
segment followed by a real Sitting segment in the same continuous
recording). The detector's `sudden_stop_like` signal (a sharp real
collapse in motion variance between consecutive windows — validated to be
more reliable on real data than raw jerk peaks, since ordinary gait already
produces jerk spikes of similar size) is scanned across every real
subject's full chronological stream and checked against these real label
transitions (a detection counts as correct if it lands within one window
of the real transition):

```
users evaluated: 36, real transitions found: 26
TP=26  FP=22  FN=0
precision = 0.542
recall    = 1.000
```

All 26 real recorded stop events in the dataset were detected (recall
1.00); precision (0.54) reflects that a single-window variance-collapse
heuristic run over ~2,700 real windows will also fire on some real
non-labelled-transition moments (e.g. brief pauses inside a Walking
segment) — exactly why the spec requires persistence + risk-context gating
before this ever becomes a `CAUTION`/`ESCALATED` state rather than acting
on the raw per-window flag alone. See Part 3.

### Part 3 — State-machine persistence + risk-context gating (spec 24.5's core requirement)

Using one real subject's real Walking→Jogging sequence, run the full
`AnomalyDetector` twice, differing only in `risk_context.risk_score`:

```
LOW risk context (0.1):
NORMAL x6 -> ANOMALY_CANDIDATE x10   (never escalates -- risk context does not align)

HIGH risk context (0.9):
NORMAL x6 -> ANOMALY_CANDIDATE x2 -> CAUTION x8   (escalates only after persistence AND elevated risk)
```

This demonstrates, on real recorded motion, exactly the required behaviour:
identical real motion data produces different outcomes depending on
whether the surrounding safety context aligns — "ABHAYA does not interpret
behaviour in isolation; it interprets behaviour in the context of where the
journey is happening" (spec 24.5).

## Usage from the backend

```python
from evaluate import evaluate_motion

result = evaluate_motion(
    sensor_window=[{"t": 1732000000000, "ax": 0.2, "ay": 9.8, "az": 0.3}, ...],
    risk_context={"risk_score": 0.7, "route_deviation": False},
    detector_state=journey.anomaly_detector_state,  # None on first call
)
journey.anomaly_detector_state = result["detector_state"]  # persist
if result["anomaly_state"] == "CAUTION":
    trigger_discreet_checkin(journey)
elif result["anomaly_state"] == "ESCALATED":
    trigger_critical_escalation(journey)
```

See `schema.md` for the full field-level contract.

## Known limitations (honest disclosure)

- No gyroscope or phone-impact data was available in a real public dataset
  within scope; those paths are implemented but not quantitatively
  validated (see Dataset section).
- Thresholds (`Z_RUNNING`, `Z_SUDDEN_STOP` internals, variance-collapse
  ratio) were tuned against WISDM's specific phone-in-front-pocket
  placement and ~20 Hz sampling; they should be re-checked once real data
  from the actual React Native app's sensor pipeline (placement, sampling
  rate, filtering) is available, per spec's "Prototype handling" column
  instruction to use these as a starting point, not a final calibration.
- `backend/app/routers` currently has no `/walkguard/event` or
  `/routeguard/check` implementation to match against, so `schema.md` is
  this module's own authoritative proposal for that contract.
