#!/usr/bin/env python3
"""Classify inclusion/exclusion evidence from RAW --experiment
inclusion_policy data (per-trial rows, not a summarized median), by
comparing the target channel's per-trial reload latency against two
calibrated hit_latency classes already measured on this machine: the
"survived" class (the target's own upper-level hit latency) and the
"invalidated" class (the hit latency of whatever level lies beyond the
evicted lower level -- e.g. DRAM, if the eviction walk was LLC-scale).

Timing-only: this script never reads hardware topology; every number it
uses comes from this machine's own already-measured hit_latency data.

Why RAW per-trial data, not a summary: a single average can hide a
genuinely mixed/bimodal result. PROJECT 1.pdf explicitly warns not to claim
a global policy from one ambiguous case -- this script reports what
FRACTION of individual trials look like each class, not just where the
mean landed, and treats the control channel's own health (it should almost
always read survived-like, since it is never touched by the eviction walk
by construction -- see inclusion_policy.h) as a live check on whether the
result is trustworthy at all, not just background noise.

IMPORTANT -- calibrate with SINGLE-SHOT numbers, not batched ones:
inclusion_policy times one uncached load per trial with no batching, same
as miss_latency, and carries the same fixed single-shot measurement
overhead documented in latency.h's KNOWN LIMITATION (tens of ticks on top
of true latency, confirmed via a dedicated control test). hit_latency's
medians are BATCHED and do NOT include that overhead, so comparing a raw
inclusion_policy trial directly against a hit_latency median systematically
misclassifies everything as "invalidated" (the fixed overhead alone can
exceed a clean L1 hit_latency number). Calibrate --survived-ticks and
--invalidated-ticks from this machine's own SINGLE-SHOT measurements
instead: --survived-ticks from a dedicated inclusion_policy calibration run
with a trivially small evict_bytes (nothing gets evicted, so its
target/control median IS the single-shot "known resident" baseline), and
--invalidated-ticks from this machine's own miss_latency data for the
transition matching "beyond the evicted lower level" (e.g. LLC_to_DRAM's
median) -- both already single-shot, directly comparable.

Usage:
    python3 scripts/classify_inclusion_policy.py \\
        data_raw/sunbird/inclusion_policy/L1_vs_LLC/inclusion_policy_base_random_<ts>.csv.gz \\
        --survived-ticks 78.4 --invalidated-ticks 622.0
"""
import argparse
import csv
import gzip
import math
import statistics
import sys


def open_maybe_gzip(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", newline="")
    return open(path, newline="")


def load_channel_ticks(paths, channel):
    values = []
    for path in paths:
        with open_maybe_gzip(path) as f:
            lines = [line for line in f if not line.lstrip().startswith("#") and line.strip()]
        reader = csv.DictReader(lines)
        if reader.fieldnames is None or "channel" not in reader.fieldnames or "ticks" not in reader.fieldnames:
            raise ValueError(f"{path}: missing 'channel'/'ticks' columns -- is this raw "
                              f"inclusion_policy output?")
        for row in reader:
            if row.get("channel") == channel:
                values.append(float(row["ticks"]))
    return values


def classify(values, survived_ticks, invalidated_ticks):
    """Buckets each value as survived-like, invalidated-like, or ambiguous,
    using the geometric mean of the two calibrated class medians as the
    decision boundary (appropriate for latency data spanning a wide
    multiplicative range), with a +/-15% ambiguous band around it so a
    value right on the fence isn't force-classified either way."""
    boundary = math.sqrt(survived_ticks * invalidated_ticks)
    lo, hi = boundary * 0.85, boundary * 1.15
    survived = sum(1 for v in values if v < lo)
    invalidated = sum(1 for v in values if v > hi)
    ambiguous = len(values) - survived - invalidated
    return survived, ambiguous, invalidated, boundary


def verdict(frac_invalidated, frac_survived):
    if frac_invalidated >= 0.80:
        return "INCLUSIVE (lower-level eviction consistently removed the upper-level copy)"
    if frac_survived >= 0.80:
        return "EXCLUSIVE / NON-INCLUSIVE (upper-level copy consistently survived lower-level eviction)"
    return "UNCERTAIN (mixed result -- do not claim a global policy from this alone)"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw_csvs", nargs="+",
                     help="one or more raw --experiment inclusion_policy CSVs (.csv or .csv.gz)")
    ap.add_argument("--survived-ticks", required=True, type=float,
                     help="this machine's single-shot 'known resident' calibration median "
                          "(e.g. from a trivially-small-evict_bytes inclusion_policy "
                          "calibration run) -- NOT a batched hit_latency number, see above")
    ap.add_argument("--invalidated-ticks", required=True, type=float,
                     help="this machine's single-shot 'known evicted beyond the lower level' "
                          "calibration median (e.g. this machine's own miss_latency median "
                          "for the matching transition) -- NOT a batched hit_latency number")
    ap.add_argument("--machine-readable", action="store_true",
                     help="print only 'verdict<TAB>frac_target_invalidated<TAB>"
                          "frac_control_invalidated'")
    args = ap.parse_args()

    survived_ticks = args.survived_ticks
    invalidated_ticks = args.invalidated_ticks
    if invalidated_ticks <= survived_ticks * 1.2:
        print(f"WARNING: invalidated-class median ({invalidated_ticks:.1f}) is not clearly "
              f"above survived-class median ({survived_ticks:.1f}) -- classification below "
              f"will be unreliable; check you picked the right hit_latency summaries.",
              file=sys.stderr)

    target_vals = load_channel_ticks(args.raw_csvs, "target")
    control_vals = load_channel_ticks(args.raw_csvs, "control")
    if not target_vals:
        print("No target-channel rows found.", file=sys.stderr)
        return 1

    t_surv, t_amb, t_inval, boundary = classify(target_vals, survived_ticks, invalidated_ticks)
    if control_vals:
        c_surv, c_amb, c_inval, _ = classify(control_vals, survived_ticks, invalidated_ticks)
    else:
        c_surv = c_amb = c_inval = 0

    n_t, n_c = len(target_vals), len(control_vals)
    frac_t_inval = t_inval / n_t if n_t else 0.0
    frac_t_surv = t_surv / n_t if n_t else 0.0
    frac_c_inval = c_inval / n_c if n_c else 0.0

    # The control channel is never touched by the eviction walk by
    # construction -- if it doesn't read survived-like almost every time,
    # that's evidence the avoidance construction (or DTLB pressure from a
    # large eviction footprint -- see inclusion_policy.h's KNOWN LIMITATION)
    # is contaminating the result, not evidence about inclusion policy.
    confound_suspected = frac_c_inval >= 0.20

    t_med, t_mean = statistics.median(target_vals), statistics.mean(target_vals)
    c_med = statistics.median(control_vals) if control_vals else float("nan")
    c_mean = statistics.mean(control_vals) if control_vals else float("nan")

    # Distribution-free corroborating signal, independent of the class-
    # boundary tuning above: pairs target/control by position (both are
    # printed target-then-control per trial, in trial order, by the same
    # cache_bench run -- see inclusion_policy.c) and asks what fraction of
    # INDIVIDUAL trials read target slower than its own paired control. This
    # doesn't depend on where the survived/invalidated classes sit, only on
    # target and control being measured under identical conditions each
    # trial, so it's a useful cross-check when the class-fraction verdict
    # above comes out ambiguous/uncertain.
    frac_target_slower = None
    if len(target_vals) == len(control_vals) and target_vals:
        slower = sum(1 for tv, cv in zip(target_vals, control_vals) if tv > cv)
        frac_target_slower = slower / len(target_vals)

    if args.machine_readable:
        if confound_suspected:
            tag = "uncertain"
        elif frac_t_inval >= 0.80:
            tag = "inclusive"
        elif frac_t_surv >= 0.80:
            tag = "exclusive"
        else:
            tag = "uncertain"
        fts = f"{frac_target_slower:.3f}" if frac_target_slower is not None else "NA"
        print(f"{tag}\t{frac_t_inval:.3f}\t{frac_c_inval:.3f}\t{fts}")
        return 0

    print(f"Survived-class (upper-level hit) median:       {survived_ticks:.2f} ticks")
    print(f"Invalidated-class (beyond-lower-level) median: {invalidated_ticks:.2f} ticks")
    print(f"Classification boundary (geometric mean):      {boundary:.2f} ticks")
    print()
    print(f"TARGET channel  (n={n_t}): median={t_med:.1f} mean={t_mean:.1f} ticks -- "
          f"{t_surv} survived-like ({frac_t_surv:.1%}), {t_amb} ambiguous, "
          f"{t_inval} invalidated-like ({frac_t_inval:.1%})")
    print(f"CONTROL channel (n={n_c}): median={c_med:.1f} mean={c_mean:.1f} ticks -- "
          f"{c_surv} survived-like ({(c_surv / n_c if n_c else 0):.1%}), {c_amb} ambiguous, "
          f"{c_inval} invalidated-like ({frac_c_inval:.1%})")
    if frac_target_slower is not None:
        print(f"Paired check: target read slower than its own trial's control in "
              f"{frac_target_slower:.1%} of trials (distribution-free, independent of the "
              f"class boundary above)")
    print()
    if confound_suspected:
        print(f"WARNING: control channel shows {frac_c_inval:.1%} invalidated-like trials, but "
              f"control is never touched by the eviction walk by construction -- this suggests "
              f"the avoidance construction is compromised on this machine/level (e.g. DTLB "
              f"pressure from a large eviction footprint, or the upper level's index range "
              f"exceeding one page -- see inclusion_policy.h's KNOWN LIMITATION). Treat the "
              f"target verdict below as UNCERTAIN regardless of its own fraction.",
              file=sys.stderr)
    final = "UNCERTAIN (confound suspected -- see warning above)" if confound_suspected else verdict(frac_t_inval, frac_t_surv)
    print(f"VERDICT: {final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
