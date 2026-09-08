#!/usr/bin/env python3
"""Infer cache-level boundaries from a processed capacity-sweep summary
(output of summarize_raw.py on a --experiment capacity raw CSV).

Timing-only: this script never reads /proc/cpuinfo cache fields, sysfs
cache-topology files, or vendor cache tables -- only the measured
median-latency-vs-size curve, per the Homework I Phase-I discipline. Treat
its output as a starting hypothesis to confirm against the box plots, not
as the final answer to paste into the report.

Usage:
    python3 scripts/detect_cache_hierarchy.py data_processed/<machine>/capacity/summary.csv
"""
import argparse
import csv
import statistics
import sys


def load_points(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        points = [(int(float(row["size_bytes"])), float(row["median"])) for row in reader]
    points.sort(key=lambda p: p[0])
    return points


def find_knees(points, rel_threshold, min_abs_ticks, confirm):
    """Return indices in `points` where a new latency plateau begins."""
    knees = []
    baseline_window = [points[0][1]]
    baseline = points[0][1]
    i = 1
    while i < len(points):
        _, lat = points[i]
        jump = lat - baseline
        rel = jump / baseline if baseline > 0 else 0.0
        if rel >= rel_threshold and jump >= min_abs_ticks:
            ok = True
            for k in range(1, confirm):
                if i + k >= len(points) or points[i + k][1] < baseline + jump * 0.5:
                    ok = False
                    break
            if ok:
                knees.append(i)
                baseline_window = [lat]
                baseline = lat
                i += 1
                continue
        baseline_window.append(lat)
        if len(baseline_window) > 5:
            baseline_window.pop(0)
        baseline = statistics.median(baseline_window)
        i += 1
    return knees


def segments_from_knees(points, knees):
    bounds = [0] + knees + [len(points)]
    segments = []
    for s, e in zip(bounds[:-1], bounds[1:]):
        seg = points[s:e]
        if not seg:
            continue
        lat_med = statistics.median(l for _, l in seg)
        segments.append((seg[0][0], seg[-1][0], lat_med, len(seg)))
    return segments


def level_name(i, n):
    if i == n - 1:
        return "Memory (DRAM)"
    names = ["L1", "L2", "L3 (LLC)"]
    return names[i] if i < len(names) else f"L{i + 1}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary_csv")
    ap.add_argument("--rel-threshold", type=float, default=0.25,
                     help="relative median-latency jump that flags a knee (default 0.25)")
    ap.add_argument("--min-abs-ticks", type=float, default=3.0,
                     help="minimum absolute tick jump to flag a knee (default 3.0)")
    ap.add_argument("--confirm", type=int, default=2,
                     help="consecutive points required to confirm a knee (default 2)")
    ap.add_argument("--freq-ghz", type=float, default=None,
                     help="self-calibrated counter frequency in GHz, to also report "
                          "latency in ns (do not use a vendor-listed clock speed)")
    ap.add_argument("--machine-readable", action="store_true",
                     help="print only the detected boundary sizes in bytes, one per "
                          "line, nothing else -- for scripts to consume directly "
                          "(e.g. `mapfile -t boundaries < <(detect_cache_hierarchy.py "
                          "... --machine-readable)`)")
    args = ap.parse_args()

    points = load_points(args.summary_csv)
    if len(points) < 3:
        print("Not enough swept points to infer a hierarchy.", file=sys.stderr)
        sys.exit(1)

    knees = find_knees(points, args.rel_threshold, args.min_abs_ticks, args.confirm)
    segments = segments_from_knees(points, knees)

    if args.machine_readable:
        for _, hi, _, _ in segments[:-1]:
            print(hi)
        return

    ns_header = "ns/access" if args.freq_ghz else ""
    print(f"{'Level':<14}{'Size range (bytes)':<28}{'Median latency (ticks)':<26}"
          f"{ns_header:<12}{'#points'}")
    for i, (lo, hi, lat, n) in enumerate(segments):
        name = level_name(i, len(segments))
        size_range = f"{lo:,} - {hi:,}"
        ns = f"{lat / args.freq_ghz:.2f}" if args.freq_ghz else ""
        print(f"{name:<14}{size_range:<28}{lat:<26.2f}{ns:<12}{n}")

    print()
    print("Estimated capacity boundaries (largest working set still served mostly")
    print("by that level -- treat as a hypothesis to confirm with box plots):")
    for i, (_, hi, _, _) in enumerate(segments[:-1]):
        print(f"  {level_name(i, len(segments))}: <= {hi:,} bytes ({hi / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
