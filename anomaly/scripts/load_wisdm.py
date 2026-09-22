"""
load_wisdm.py -- loader for the real WISDM Actitracker v1.1 accelerometer
dataset (Kwapisz, Weiss & Moore 2010; Fordham University WISDM Lab).
Source: https://www.cis.fordham.edu/wisdm/dataset.php
File used: WISDM_ar_v1.1_raw.txt (downloaded into anomaly/data/).
License: free for research/educational use, redistribute with the included
readme.txt (see anomaly/data/WISDM_ar_v1.1/readme.txt).

Format per line: user,activity,timestamp_ns,x,y,z;
(timestamps are per-device nanosecond counters, ~20Hz nominal sample rate,
real recordings collected by 36 real subjects carrying an Android phone in
their front pants pocket while performing Walking/Jogging/Upstairs/
Downstairs/Sitting/Standing.)

Some lines in the raw file are malformed (missing z-value, stray commas) --
this loader skips those defensively rather than fabricating a value.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from typing import Dict, List, Tuple

RAW_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "WISDM_ar_v1.1", "WISDM_ar_v1.1_raw.txt")


def load_raw(path: str = RAW_PATH) -> Dict[int, List[dict]]:
    """Returns {user_id: [ {t, activity, ax, ay, az}, ... ]} in file order
    (which is chronological per user for this dataset)."""
    by_user: Dict[int, List[dict]] = defaultdict(list)
    n_ok, n_bad = 0, 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip().rstrip(";")
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 6:
                n_bad += 1
                continue
            try:
                user = int(parts[0])
                activity = parts[1]
                ts_ns = float(parts[2])
                ax, ay, az = float(parts[3]), float(parts[4]), float(parts[5])
            except ValueError:
                n_bad += 1
                continue
            if ts_ns <= 0:
                n_bad += 1
                continue
            ts_ms = ts_ns / 1e6  # device nanosecond counter -> ms, matches features.py's t-in-ms contract
            by_user[user].append({"t": ts_ms, "activity": activity, "ax": ax, "ay": ay, "az": az})
            n_ok += 1
    print(f"[load_wisdm] parsed {n_ok} samples ok, skipped {n_bad} malformed lines, {len(by_user)} users")
    return by_user


def make_windows(samples: List[dict], window_size: int = 40, step: int = 20) -> List[Tuple[str, List[dict]]]:
    """Slide a fixed-size window (default 40 samples ~ 2s at 20Hz, 50% overlap)
    over one user's chronological sample list. Each window is labelled with
    the majority activity label within it (ground truth for validation only
    -- the detector itself never sees these labels)."""
    out = []
    n = len(samples)
    i = 0
    while i + window_size <= n:
        chunk = samples[i:i + window_size]
        labels = [s["activity"] for s in chunk]
        majority = max(set(labels), key=labels.count)
        out.append((majority, chunk))
        i += step
    return out
