"""
features.py -- Real motion-feature extraction for ABHAYA's behavioural-anomaly
module (spec sections 6.4 / 24.5, WalkGuard sections 7.3 / 24.9).

Consumes a short window of raw accelerometer (and optionally gyroscope)
samples -- exactly the shape a React Native app streams from
`DeviceMotion` / `Accelerometer` / `Gyroscope` (expo-sensors,
react-native-sensors, etc.) -- and produces the small set of interpretable
scalar features the spec calls for ("simple interpretable motion features",
"coarse features locally"). No black-box model, no raw-stream storage.

A window is a list of samples:
    {"t": <unix_ms float>, "ax": .., "ay": .., "az": ..,
     "gx": None, "gy": None, "gz": None}
gx/gy/gz may be omitted/None -- gyroscope is optional input per spec 6.4
("Optional heart rate" / gyroscope combined *when available*; the detector
must not require it).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass
class Sample:
    t: float  # unix ms
    ax: float
    ay: float
    az: float
    gx: Optional[float] = None
    gy: Optional[float] = None
    gz: Optional[float] = None

    @staticmethod
    def from_dict(d: dict) -> "Sample":
        return Sample(
            t=float(d["t"]),
            ax=float(d["ax"]), ay=float(d["ay"]), az=float(d["az"]),
            gx=(None if d.get("gx") is None else float(d["gx"])),
            gy=(None if d.get("gy") is None else float(d["gy"])),
            gz=(None if d.get("gz") is None else float(d["gz"])),
        )


@dataclass
class MotionFeatures:
    """Interpretable, per-window feature set (spec 24.5: 'simple
    interpretable motion features for the prototype')."""
    n_samples: int
    duration_s: float
    sample_rate_hz: float

    accel_mean_mag: float          # mean |a|, gravity included
    accel_std_mag: float           # variance/spread of |a|  -> "erratic pacing"
    accel_sma: float                # signal magnitude area (per-axis, |ax|+|ay|+|az| mean)
    accel_max_mag: float
    accel_min_mag: float

    jerk_mean: float                 # mean |d|a|/dt|  -> suddenness of change
    jerk_max: float                  # peak jerk -> candidate for "sudden stop" / impact
    jerk_std: float

    zero_crossing_rate: float        # cadence proxy on the gravity-removed signal
    dominant_step_freq_hz: float     # coarse step-frequency estimate (autocorrelation)

    gyro_mean_mag: Optional[float] = None
    gyro_std_mag: Optional[float] = None
    has_gyro: bool = False


def _mag(x: float, y: float, z: float) -> float:
    return math.sqrt(x * x + y * y + z * z)


def extract_features(window: Sequence[dict]) -> MotionFeatures:
    """Compute MotionFeatures from a raw sensor window.

    `window` is a chronologically ordered list of sample dicts (see module
    docstring). Requires >= 3 samples to compute jerk/variance meaningfully;
    raises ValueError otherwise so callers don't silently score empty data.
    """
    if len(window) < 3:
        raise ValueError("need at least 3 samples to extract motion features")

    samples = [Sample.from_dict(s) for s in window]
    samples.sort(key=lambda s: s.t)

    t0, tN = samples[0].t, samples[-1].t
    duration_s = max((tN - t0) / 1000.0, 1e-6)
    sample_rate_hz = (len(samples) - 1) / duration_s if duration_s > 0 else 0.0

    mags = [_mag(s.ax, s.ay, s.az) for s in samples]
    n = len(mags)
    mean_mag = sum(mags) / n
    var_mag = sum((m - mean_mag) ** 2 for m in mags) / n
    std_mag = math.sqrt(var_mag)

    sma = sum(abs(s.ax) + abs(s.ay) + abs(s.az) for s in samples) / (3 * n)

    # jerk = d(|a|)/dt between consecutive samples
    jerks = []
    for i in range(1, n):
        dt = (samples[i].t - samples[i - 1].t) / 1000.0
        if dt <= 0:
            continue
        jerks.append(abs(mags[i] - mags[i - 1]) / dt)
    if not jerks:
        jerks = [0.0]
    jerk_mean = sum(jerks) / len(jerks)
    jerk_max = max(jerks)
    jerk_mean_sq = sum((j - jerk_mean) ** 2 for j in jerks) / len(jerks)
    jerk_std = math.sqrt(jerk_mean_sq)

    # Zero-crossing rate of the gravity-removed magnitude (mean-centered)
    centered = [m - mean_mag for m in mags]
    crossings = sum(
        1 for i in range(1, n)
        if centered[i - 1] == 0 or (centered[i] * centered[i - 1] < 0)
    )
    zcr = crossings / duration_s

    # Coarse dominant step frequency via simple autocorrelation peak search
    dominant_step_freq_hz = _estimate_step_frequency(centered, sample_rate_hz)

    gyro_mean_mag = gyro_std_mag = None
    has_gyro = all(s.gx is not None and s.gy is not None and s.gz is not None for s in samples)
    if has_gyro:
        gmags = [_mag(s.gx, s.gy, s.gz) for s in samples]
        gyro_mean_mag = sum(gmags) / n
        gyro_std_mag = math.sqrt(sum((g - gyro_mean_mag) ** 2 for g in gmags) / n)

    return MotionFeatures(
        n_samples=n,
        duration_s=duration_s,
        sample_rate_hz=sample_rate_hz,
        accel_mean_mag=mean_mag,
        accel_std_mag=std_mag,
        accel_sma=sma,
        accel_max_mag=max(mags),
        accel_min_mag=min(mags),
        jerk_mean=jerk_mean,
        jerk_max=jerk_max,
        jerk_std=jerk_std,
        zero_crossing_rate=zcr,
        dominant_step_freq_hz=dominant_step_freq_hz,
        gyro_mean_mag=gyro_mean_mag,
        gyro_std_mag=gyro_std_mag,
        has_gyro=has_gyro,
    )


def _estimate_step_frequency(centered: Sequence[float], sample_rate_hz: float,
                              min_hz: float = 0.5, max_hz: float = 4.0) -> float:
    """Very coarse dominant-frequency estimate via autocorrelation, restricted
    to the plausible human-locomotion band (0.5-4 Hz: walk..sprint cadence).
    Avoids pulling in an FFT dependency for a small window."""
    n = len(centered)
    if sample_rate_hz <= 0 or n < 8:
        return 0.0
    min_lag = max(1, int(sample_rate_hz / max_hz))
    max_lag = min(n - 1, int(sample_rate_hz / min_hz))
    if max_lag <= min_lag:
        return 0.0
    best_lag, best_corr = 0, -1e18
    for lag in range(min_lag, max_lag + 1):
        corr = sum(centered[i] * centered[i - lag] for i in range(lag, n))
        if corr > best_corr:
            best_corr, best_lag = corr, lag
    if best_lag == 0:
        return 0.0
    return sample_rate_hz / best_lag
