"""
validate.py -- validates the anomaly detector against the REAL WISDM
Actitracker accelerometer dataset (real phones, real subjects; see
scripts/load_wisdm.py for provenance/license). No synthetic/fabricated
sensor data is used as evidence here.

What is measured, honestly, given what a public accel-only HAR dataset can
support:

  1. RUNNING DETECTION: does classify_deviation() flag real Jogging windows
     as `running_like` anomaly candidates, and correctly NOT flag real
     Walking windows? Reported as precision/recall/accuracy over held-out
     users (baseline built per-user from that same user's real Walking
     windows -- this mirrors how WalkGuard builds a per-journey baseline).

  2. SUDDEN-STOP DETECTION: WISDM has no synthetic "sudden stop" -- but real
     users' recordings contain real activity transitions (e.g. real
     Jogging/Walking segments followed by real Sitting/Standing segments).
     We scan real per-user timestamp-ordered streams for `sudden_stop_like`
     flags and check them against the real ground-truth label transitions
     (moving-activity -> stationary-activity) that actually occur in the
     recorded data, reporting precision/recall for that event-detection task.

Run: python validate.py
"""
from __future__ import annotations

import random
import statistics
from collections import defaultdict

from features import extract_features
from baseline import JourneyBaseline
from state_machine import classify_deviation
from scripts.load_wisdm import load_raw, make_windows

MOVING = {"Jogging", "Walking", "Upstairs", "Downstairs"}
STATIONARY = {"Sitting", "Standing"}
WINDOW = 40   # ~2s at ~20Hz
STEP = 20     # 50% overlap
MAX_DT_MS = 1000  # sanity cap: skip windows spanning a session/timestamp discontinuity


def sane_window(chunk):
    ts = sorted(s["t"] for s in chunk)
    return all((ts[i + 1] - ts[i]) < MAX_DT_MS for i in range(len(ts) - 1))


def part1_running_detection(by_user):
    """Per-user baseline from that user's own real Walking windows; test
    on that same user's held-out Walking + Jogging windows."""
    tp = fp = tn = fn = 0
    per_user_rows = []
    users = sorted(by_user.keys())
    for user in users:
        windows = make_windows(by_user[user], WINDOW, STEP)
        walking = [(lbl, c) for lbl, c in windows if lbl == "Walking" and sane_window(c)]
        jogging = [(lbl, c) for lbl, c in windows if lbl == "Jogging" and sane_window(c)]
        if len(walking) < 10 or len(jogging) < 5:
            continue  # not enough real data for this user to build+test a baseline

        random.Random(42).shuffle(walking)
        split = max(5, len(walking) // 3)
        baseline_windows, test_walk = walking[:split], walking[split:]

        bl = JourneyBaseline(min_samples_for_baseline=5)
        for _, c in baseline_windows:
            bl.update(extract_features(c))
        if not bl.is_ready:
            continue

        u_tp = u_fp = u_tn = u_fn = 0
        for _, c in test_walk:
            dev = classify_deviation(extract_features(c), bl)
            if dev.running_like:
                u_fp += 1
            else:
                u_tn += 1
        for _, c in jogging:
            dev = classify_deviation(extract_features(c), bl)
            if dev.running_like:
                u_tp += 1
            else:
                u_fn += 1

        tp += u_tp; fp += u_fp; tn += u_tn; fn += u_fn
        per_user_rows.append((user, u_tp, u_fp, u_tn, u_fn))

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    accuracy = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) else float("nan")
    print("\n=== Part 1: RUNNING (Jogging) detection vs held-out real Walking, per-user baseline ===")
    print(f"users evaluated: {len(per_user_rows)}")
    print(f"confusion: TP(jog flagged)={tp} FN(jog missed)={fn} "
          f"FP(walk flagged)={fp} TN(walk clear)={tn}")
    print(f"precision={precision:.3f} recall={recall:.3f} accuracy={accuracy:.3f}")
    return dict(tp=tp, fp=fp, tn=tn, fn=fn, precision=precision, recall=recall, accuracy=accuracy,
                n_users=len(per_user_rows))


def part2_sudden_stop_detection(by_user):
    """Scan each user's real chronological stream for `sudden_stop_like`
    flags; ground truth = a real recorded transition from a moving activity
    to a stationary activity within the dataset's own labels."""
    tp = fp = fn = 0
    n_transitions = 0
    n_users_used = 0
    for user, samples in by_user.items():
        windows = make_windows(samples, WINDOW, STEP)
        windows = [(lbl, c) for lbl, c in windows if sane_window(c)]
        if len(windows) < 20:
            continue

        # Build a baseline from this user's first moving windows (Walking/Jogging)
        bl = JourneyBaseline(min_samples_for_baseline=5)
        seeded = 0
        for lbl, c in windows:
            if lbl in MOVING and seeded < 15:
                bl.update(extract_features(c))
                seeded += 1
            if seeded >= 15:
                break
        if not bl.is_ready:
            continue
        n_users_used += 1

        flags = []
        labels = [lbl for lbl, _ in windows]
        prev_std = None
        for lbl, c in windows:
            f = extract_features(c)
            dev = classify_deviation(f, bl, prev_std)
            flags.append(dev.sudden_stop_like)
            prev_std = f.accel_std_mag

        # ground-truth transition index: moving[i-1] -> stationary[i]
        gt_transition = [False] * len(labels)
        for i in range(1, len(labels)):
            if labels[i - 1] in MOVING and labels[i] in STATIONARY:
                gt_transition[i] = True
                n_transitions += 1

        # a detection counts as a true positive if a sudden_stop_like flag
        # occurs within +/-1 window of a real ground-truth transition
        matched_gt = set()
        for i, flagged in enumerate(flags):
            if not flagged:
                continue
            hit = False
            for j in range(max(0, i - 1), min(len(gt_transition), i + 2)):
                if gt_transition[j] and j not in matched_gt:
                    matched_gt.add(j)
                    hit = True
                    break
            if hit:
                tp += 1
            else:
                fp += 1
        fn += sum(1 for i, g in enumerate(gt_transition) if g and i not in matched_gt)

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    print("\n=== Part 2: SUDDEN-STOP detection vs real moving->stationary label transitions ===")
    print(f"users evaluated: {n_users_used}, real transitions found: {n_transitions}")
    print(f"TP={tp} FP={fp} FN={fn}")
    print(f"precision={precision:.3f} recall={recall:.3f}")
    return dict(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall,
                n_transitions=n_transitions, n_users=n_users_used)


def part3_state_machine_persistence(by_user):
    """Demonstrate that a SINGLE anomalous window never reaches CAUTION, and
    that CAUTION/ESCALATED require both persistence AND elevated risk
    context -- run on a real Jogging sequence from one real user under two
    risk_context conditions."""
    from state_machine import AnomalyDetector, RiskContext

    user = sorted(by_user.keys())[0]
    windows = make_windows(by_user[user], WINDOW, STEP)
    windows = [(lbl, c) for lbl, c in windows if sane_window(c)]
    walk = [(lbl, c) for lbl, c in windows if lbl == "Walking"][:15]
    jog = [(lbl, c) for lbl, c in windows if lbl == "Jogging"][:10]
    if len(walk) < 6 or not jog:
        print("\n=== Part 3 skipped: insufficient real data for chosen user ===")
        return

    for risk_score, label in [(0.1, "LOW risk context"), (0.9, "HIGH risk context")]:
        det = AnomalyDetector()
        states = []
        for lbl, c in walk[:6]:
            r = det.step(extract_features(c), RiskContext(risk_score=risk_score))
            states.append(r["anomaly_state"])
        for lbl, c in jog:
            r = det.step(extract_features(c), RiskContext(risk_score=risk_score))
            states.append(r["anomaly_state"])
        print(f"\n=== Part 3 ({label}), real user {user}, real Walking->Jogging sequence ===")
        print("state sequence:", states)


if __name__ == "__main__":
    by_user = load_raw()
    r1 = part1_running_detection(by_user)
    r2 = part2_sudden_stop_detection(by_user)
    part3_state_machine_persistence(by_user)
