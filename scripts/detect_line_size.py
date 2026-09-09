#!/usr/bin/env python3
"""Infer the cache line size from a processed line_size-sweep summary
(output of summarize_raw.py on a --experiment line_size raw CSV).

Timing-only: this script never reads /proc/cpuinfo cache fields, sysfs
cache-topology files, or vendor cache tables -- only the measured
median-latency-vs-stride curve, per the Homework I Phase-I discipline. Treat
its output as a starting hypothesis to confirm against the plotted curve, not
as the final answer to paste into the report.

Why the polarity is inverted relative to detect_cache_hierarchy.py: the
line_size sweep holds a FIXED virtual footprint and varies the byte stride
between nodes. Real cache occupancy is (distinct lines touched) *
true_line_size. For stride <= true_line_size, occupancy is flat and equal to
footprint_bytes (every stride packs the same footprint into the same number
of lines); once stride exceeds true_line_size, occupancy falls off as
footprint_bytes * (true_line_size / stride), since each 8-byte node now
wastes most of an oversized line. So if footprint_bytes was chosen just
ABOVE a known capacity boundary, small/at-line-size strides spill (elevated
latency) and latency DROPS back down once stride grows past the real line
size -- the opposite shape from detect_cache_hierarchy.py's "latency rises
past a capacity boundary".

Because the sweep's footprint_bytes = m * boundary_bytes for some multiplier
m > 1 (see scripts/run_line_size_full.sh), the raw drop point is biased high
by that same factor: the drop occurs at stride* = m * true_line_size. Pass
--boundary-bytes (the actual capacity boundary used to build the sweep) to
get a corrected estimate; without it, only the uncorrected (biased-high) raw
value is available.

Usage:
    python3 scripts/detect_line_size.py data_processed/<machine>/line_size/summary.csv \\
        --boundary-bytes 32768
"""
import argparse
import csv
import statistics
import sys


def load_points(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    points = [(int(float(row["stride_bytes"])), float(row["median"])) for row in rows]
    points.sort(key=lambda p: p[0])
    footprint_bytes = None
    if rows:
        try:
            footprint_bytes = int(float(rows[0]["footprint_bytes"]))
        except (KeyError, ValueError):
            footprint_bytes = None
    return points, footprint_bytes


def find_drop(points, rel_threshold, min_abs_ticks, confirm):
    """Mirror image of detect_cache_hierarchy.py's find_knees(): tracks a
    rolling HIGH baseline (latency starts elevated, in the spill/at-line-size
    regime) and returns the index of the first point where latency falls
    below that baseline by at least rel_threshold, confirmed by `confirm`
    consecutive points staying down. Returns None if no drop is found."""
    if len(points) < 2:
        return None
    baseline_window = [points[0][1]]
    baseline = points[0][1]
    i = 1
    while i < len(points):
        _, lat = points[i]
        drop = baseline - lat
        rel = drop / baseline if baseline > 0 else 0.0
        if rel >= rel_threshold and drop >= min_abs_ticks:
            ok = True
            for k in range(1, confirm):
                if i + k >= len(points) or points[i + k][1] > baseline - drop * 0.5:
                    ok = False
                    break
            if ok:
                return i
        baseline_window.append(lat)
        if len(baseline_window) > 5:
            baseline_window.pop(0)
        baseline = statistics.median(baseline_window)
        i += 1
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary_csv")
    ap.add_argument("--rel-threshold", type=float, default=0.25,
                     help="relative median-latency drop that flags the line-size "
                          "transition (default 0.25)")
    ap.add_argument("--min-abs-ticks", type=float, default=3.0,
                     help="minimum absolute tick drop to flag the transition (default 3.0)")
    ap.add_argument("--confirm", type=int, default=2,
                     help="consecutive points required to confirm the drop (default 2)")
    ap.add_argument("--boundary-bytes", type=float, default=None,
                     help="the capacity boundary (bytes) that footprint_bytes was built "
                          "from (footprint_bytes = m * boundary_bytes) -- required to "
                          "correct the raw knee stride by dividing out m; without it, "
                          "only the uncorrected, biased-high raw stride is reported")
    ap.add_argument("--machine-readable", action="store_true",
                     help="print only the estimated line size in bytes (corrected if "
                          "--boundary-bytes given, otherwise raw), nothing else -- for "
                          "scripts to consume directly")
    args = ap.parse_args()

    points, footprint_bytes = load_points(args.summary_csv)
    if len(points) < 3:
        print("Not enough swept stride points to infer a line size.", file=sys.stderr)
        sys.exit(1)

    idx = find_drop(points, args.rel_threshold, args.min_abs_ticks, args.confirm)
    if idx is None:
        print("No line-size transition detected in this sweep.", file=sys.stderr)
        sys.exit(1)

    raw_knee_stride = points[idx - 1][0]
    next_stride = points[idx][0]

    corrected = None
    m = None
    if args.boundary_bytes is not None:
        if footprint_bytes is None:
            print("summary_csv has no footprint_bytes column; cannot correct.",
                  file=sys.stderr)
        elif args.boundary_bytes <= 0:
            print("--boundary-bytes must be > 0; cannot correct.", file=sys.stderr)
        else:
            m = footprint_bytes / args.boundary_bytes
            corrected = raw_knee_stride / m

    if args.machine_readable:
        print(int(round(corrected)) if corrected is not None else raw_knee_stride)
        return

    print(f"Raw knee: last elevated stride = {raw_knee_stride} bytes, "
          f"first dropped stride = {next_stride} bytes")
    print("(the real transition lies somewhere in this window -- narrow it with a "
          "denser --stride-step 1 sweep bracketing it)")
    if corrected is not None:
        print(f"footprint_bytes={footprint_bytes}, boundary_bytes={args.boundary_bytes:g}, "
              f"m={m:.3f}")
        print(f"Corrected line-size estimate: {corrected:.1f} bytes "
              f"(raw {raw_knee_stride} / m)")
    else:
        print("No --boundary-bytes given: this raw value is UNCORRECTED and biased "
              "high by the unknown footprint_bytes/boundary_bytes ratio -- do not "
              "treat it as the final estimate.", file=sys.stderr)

    print()
    print("Segments (stride range, median latency, #points):")
    bounds = [0, idx, len(points)]
    for s, e in zip(bounds[:-1], bounds[1:]):
        seg = points[s:e]
        if not seg:
            continue
        lat_med = statistics.median(lat for _, lat in seg)
        label = "elevated (spill)" if s == 0 else "low (fit)"
        print(f"  {label:<18} {seg[0][0]:>6}-{seg[-1][0]:<6} bytes  "
              f"median={lat_med:.2f} ticks  n={len(seg)}")


if __name__ == "__main__":
    main()
