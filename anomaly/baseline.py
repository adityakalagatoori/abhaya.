"""
baseline.py -- per-journey normal-motion baseline (spec 24.5:
"Create a normal-motion baseline for the current journey. Measure deviation
from that baseline.")

This is intentionally a simple running-statistics model (mean/std of a few
features), not a black box, per spec 24.5 ("Avoid a large black-box model
with no explanation. Use instead: simple interpretable motion features.").

Usage:
    baseline = JourneyBaseline()
    baseline.update(features)              # feed early "known normal" windows
    deviation = baseline.deviation(features)  # z-score-like deviation report
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

from features import MotionFeatures

# Features used to characterise "normal walking" for this journey.
_TRACKED = (
    "accel_mean_mag", "accel_std_mag", "accel_sma",
    "jerk_mean", "jerk_max", "zero_crossing_rate", "dominant_step_freq_hz",
)


@dataclass
class FeatureStat:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0  # for Welford's online variance

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2

    @property
    def std(self) -> float:
        if self.n < 2:
            return 0.0
        return math.sqrt(self.m2 / (self.n - 1))


@dataclass
class JourneyBaseline:
    """Accumulates a rolling normal-motion baseline for one journey.

    Call `update()` with windows the caller believes represent ordinary
    walking (e.g. the first N windows of WalkGuard, or windows the state
    machine has not flagged) so the baseline adapts to *this* user's normal
    gait rather than a population average.
    """
    min_samples_for_baseline: int = 5
    max_history: int = 240  # ~20 min at one feature-window per 5s
    stats: Dict[str, FeatureStat] = field(default_factory=lambda: {k: FeatureStat() for k in _TRACKED})
    _count: int = 0

    def update(self, feats: MotionFeatures) -> None:
        if self._count >= self.max_history:
            return  # keep baseline stable once journey's normal pattern is established
        for k in _TRACKED:
            self.stats[k].update(getattr(feats, k))
        self._count += 1

    @property
    def is_ready(self) -> bool:
        return self._count >= self.min_samples_for_baseline

    def deviation(self, feats: MotionFeatures) -> Dict[str, float]:
        """Return a z-score per tracked feature: (value - baseline_mean) / baseline_std.

        If the baseline is not ready yet, returns zeros (no deviation can be
        claimed without a baseline) -- callers must check `is_ready`.
        """
        if not self.is_ready:
            return {k: 0.0 for k in _TRACKED}
        out = {}
        for k in _TRACKED:
            stat = self.stats[k]
            val = getattr(feats, k)
            std = stat.std if stat.std > 1e-6 else 1e-6
            out[k] = (val - stat.mean) / std
        return out

    def summary(self) -> Dict[str, Dict[str, float]]:
        return {k: {"mean": s.mean, "std": s.std, "n": s.n} for k, s in self.stats.items()}
