#!/usr/bin/env python3
"""Classify each size point in a capacity_validate summary CSV as part of a
flat plateau, a monotonic transition ramp, or a step, using only the
already-computed percentile columns (median/p5/q1/q3/p95) -- no hardware
cache-topology lookup, per Phase I discipline.

Method (deliberately simple, timing-only):
  - For each point, compare its median against the immediately adjacent
    points (by tested byte size, not by group) on both sides.
  - A point is flagged REJECTED (no sustained rise) if it is not part of a
    monotonic (allowing small noise via --tol) climb spanning at least
    --span points in one direction.
  - Consecutive points identified as part of the same monotonic climb are
    clustered into a single transition region, so a gradual ramp reports
    as one region rather than one "boundary" per point.
  - Run-to-run spread (p5-p95 as a fraction of median) is reported per
    point so a wide-percentile point can be told apart from a
    tightly-reproducible one.

Usage:
    python3 scripts/analyze_capacity_validate.py \\
        data_processed/sunbird/capacity_validate/{l1d,l2,l3,dram}_summary.csv \\
        --flag 26999993 --flag 149999845
"""
import argparse
import csv
import sys


def load(paths):
    points = []
    for path in paths:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                points.append({
                    "size_bytes": int(float(row["size_bytes"])),
                    "median": float(row["median"]),
                    "p5": float(row["p5"]),
                    "p95": float(row["p95"]),
                    "q1": float(row["q1"]),
                    "q3": float(row["q3"]),
                    "n": int(float(row["n"])),
                })
    dedup = {}
    for p in points:
        dedup[p["size_bytes"]] = p
    return sorted(dedup.values(), key=lambda p: p["size_bytes"])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary_csvs", nargs="+")
    ap.add_argument("--tol", type=float, default=0.03,
                     help="relative tolerance for 'not decreasing' when building a "
                          "monotonic climb (default 0.03 = allow up to 3%% dip as noise)")
    ap.add_argument("--flag", action="append", default=[], type=int,
                     help="a previously-reported candidate boundary (bytes) to call "
                          "out explicitly in the report, even if not an exact tested size")
    args = ap.parse_args()

    points = load(args.summary_csvs)
    if len(points) < 3:
        print("Not enough points to classify.", file=sys.stderr)
        sys.exit(1)

    print(f"{'bytes':>12} {'KiB/MiB':>12} {'median':>10} {'spread%':>8} {'trend':>10}")
    trends = []
    for i, p in enumerate(points):
        lo = points[i - 1]["median"] if i > 0 else None
        hi = points[i + 1]["median"] if i < len(points) - 1 else None
        spread_pct = 100.0 * (p["p95"] - p["p5"]) / p["median"] if p["median"] else 0.0
        if lo is not None and p["median"] < lo * (1 - args.tol):
            trend = "down"
        elif hi is not None and hi < p["median"] * (1 - args.tol):
            trend = "peak?"
        elif (lo is None or p["median"] >= lo * (1 - args.tol)) and \
             (hi is None or hi >= p["median"] * (1 - args.tol)):
            trend = "rising" if (lo is not None and p["median"] > lo * (1 + args.tol)) else "flat"
        else:
            trend = "?"
        trends.append(trend)
        b = p["size_bytes"]
        human = f"{b/1024:.1f} KiB" if b < 1 << 20 else f"{b/1024/1024:.4f} MiB"
        flagmark = "  <-- FLAGGED" if any(abs(b - f) < max(1, 0.001 * f) for f in args.flag) else ""
        print(f"{b:>12} {human:>12} {p['median']:>10.3f} {spread_pct:>7.1f}% {trend:>10}{flagmark}")

    # Cluster consecutive "rising" points into transition regions; a point
    # surrounded by "flat" on both sides that isn't itself part of a rise
    # is rejected (no sustained latency increase across wider surrounding
    # sizes).
    print()
    print("-- transition regions (consecutive monotonic rises clustered) --")
    i = 0
    n = len(points)
    in_region = False
    region_start = None
    for i in range(1, n):
        rising = points[i]["median"] > points[i - 1]["median"] * (1 + args.tol)
        if rising and not in_region:
            in_region = True
            region_start = i - 1
        elif not rising and in_region:
            lo_b, hi_b = points[region_start]["size_bytes"], points[i - 1]["size_bytes"]
            lo_m, hi_m = points[region_start]["median"], points[i - 1]["median"]
            print(f"  {lo_b:,} B -> {hi_b:,} B   (median {lo_m:.2f} -> {hi_m:.2f} ticks, "
                  f"+{100*(hi_m/lo_m - 1):.1f}%)")
            in_region = False
    if in_region:
        lo_b, hi_b = points[region_start]["size_bytes"], points[-1]["size_bytes"]
        lo_m, hi_m = points[region_start]["median"], points[-1]["median"]
        print(f"  {lo_b:,} B -> {hi_b:,} B   (median {lo_m:.2f} -> {hi_m:.2f} ticks, "
              f"+{100*(hi_m/lo_m - 1):.1f}%) [still rising at largest tested size]")

    print()
    print("-- flagged candidate boundaries --")
    for f in args.flag:
        nearest = min(points, key=lambda p: abs(p["size_bytes"] - f))
        idx = points.index(nearest)
        prev_m = points[idx - 1]["median"] if idx > 0 else None
        next_m = points[idx + 1]["median"] if idx < n - 1 else None
        verdict = "UNCLEAR"
        if prev_m is not None and next_m is not None:
            if nearest["median"] > prev_m * (1 + args.tol) and next_m > nearest["median"] * (1 - args.tol):
                verdict = "part of an ongoing/sustained rise (ramp), not an isolated step"
            elif abs(nearest["median"] - prev_m) < args.tol * prev_m and \
                 abs(nearest["median"] - next_m) < args.tol * next_m:
                verdict = "flat vs. both neighbors -- looks like plateau, not a transition"
            else:
                verdict = "ambiguous relative to neighbors -- inspect manually"
        print(f"  {f:,} B (nearest tested: {nearest['size_bytes']:,} B, median="
              f"{nearest['median']:.3f}): {verdict}")
        if prev_m is not None:
            print(f"    prev neighbor {points[idx-1]['size_bytes']:,} B: median={prev_m:.3f}")
        if next_m is not None:
            print(f"    next neighbor {points[idx+1]['size_bytes']:,} B: median={next_m:.3f}")


if __name__ == "__main__":
    main()
