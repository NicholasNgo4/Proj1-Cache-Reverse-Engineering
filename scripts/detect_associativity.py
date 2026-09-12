#!/usr/bin/env python3
"""Infer a cache level's associativity (ways per set) from a processed
associativity-sweep summary (output of summarize_raw.py on a
--experiment associativity raw CSV run at a single cache_bytes stride).

Timing-only: this script never reads /proc/cpuinfo cache fields, sysfs
cache-topology files, or vendor cache tables -- only the measured
median-latency-vs-num_ways curve, per the Homework I Phase-I discipline.
Treat its output as a starting hypothesis to confirm against the box plots,
not as the final answer to paste into the report.

=== Model ===

cache_bench's associativity sweep holds the node-to-node stride fixed at
cache_bytes (the target level's own capacity) and chases num_ways_probed
nodes that all collide into the same cache set (see associativity.h's
module docstring for why a stride of exactly cache_bytes guarantees this
regardless of the unknown line size / way count). For num_ways_probed <=
true associativity W, every probed tag still fits in the set: flat hit
latency. Once num_ways_probed > W, a cyclic dependent chase over N > W
distinct blocks with a W-way (or smaller-effective) LRU set thrashes on
*every* access, not gradually -- so this is a sharp step, not a ramp. This
is the same knee-finding shape as detect_cache_hierarchy.py's capacity
boundaries, just on an integer "ways probed" axis instead of a byte-size
axis, and expecting exactly one knee per run instead of one per cache
level (this script is run once per cache level, at that level's own
cache_bytes stride).

The reported associativity is the LAST num_ways_probed value still on the
flat baseline plateau before the jump -- i.e. the largest number of
simultaneous tags this set was observed to hold.

Usage:
    python3 scripts/detect_associativity.py \\
        data_processed/<machine>/associativity/<level>/summary.csv
"""
import argparse
import csv
import statistics
import sys


def load_points(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    points = [(int(float(row["num_ways_probed"])), float(row["median"])) for row in rows]
    points.sort(key=lambda p: p[0])
    cache_bytes = None
    if rows:
        try:
            cache_bytes = int(float(rows[0]["cache_bytes"]))
        except (KeyError, ValueError):
            cache_bytes = None
    return points, cache_bytes


def find_first_knee(points, rel_threshold, min_abs_ticks, confirm):
    """Same rolling-baseline knee search as detect_cache_hierarchy.py's
    find_knees(), but stops at the first confirmed knee -- an associativity
    run targets one cache level's own set, so there should be at most one
    real transition (flat hit plateau -> thrashing) in the whole sweep."""
    if len(points) < 2:
        return None
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
                     help="relative median-latency jump that flags the knee (default "
                          "0.25). The expected jump (hit -> thrashing) is typically "
                          "10x+, so this default has wide margin.")
    ap.add_argument("--min-abs-ticks", type=float, default=3.0,
                     help="minimum absolute tick jump to flag the knee (default 3.0)")
    ap.add_argument("--confirm", type=int, default=2,
                     help="consecutive points required to confirm the knee stays up "
                          "(default 2)")
    ap.add_argument("--machine-readable", action="store_true",
                     help="print only the estimated associativity (an integer), "
                          "nothing else -- for scripts to consume directly")
    args = ap.parse_args()

    points, cache_bytes = load_points(args.summary_csv)
    if len(points) < 3:
        print("Not enough swept num_ways points to infer associativity.", file=sys.stderr)
        sys.exit(1)

    knee_idx = find_first_knee(points, args.rel_threshold, args.min_abs_ticks, args.confirm)
    if knee_idx is None or knee_idx == 0:
        print("No thrashing knee detected -- either true associativity is at or above "
              "--max-ways (sweep further) or cache_bytes doesn't match this level's "
              "real capacity.", file=sys.stderr)
        sys.exit(1)

    # knee_idx indexes the FIRST thrashing point, i.e. num_ways_probed = A+1
    # for true associativity A (see module docstring: a cyclic chase over
    # N > A distinct same-set tags with an A-way set thrashes on every
    # access starting at N = A+1, not at N = A). points[knee_idx - 1][0] is
    # therefore the last num_ways_probed value still on the flat plateau,
    # i.e. A itself -- verified against Sunbird's hand-confirmed L1 result
    # (flat through num_ways=8, sharp step at num_ways=9 -> reported 8).
    associativity = points[knee_idx - 1][0]
    plateau_lat = statistics.median(lat for n, lat in points if n <= associativity)
    thrash_lat = points[knee_idx][1]

    if args.machine_readable:
        print(associativity)
        return

    cb_str = f"{cache_bytes:,} bytes" if cache_bytes else "unknown"
    print(f"Estimated associativity: {associativity}-way (tested at cache_bytes={cb_str})")
    print(f"  flat/hit plateau median (num_ways <= {associativity}): {plateau_lat:.2f} ticks")
    print(f"  first thrashing point (num_ways={points[knee_idx][0]}): {thrash_lat:.2f} ticks "
          f"({thrash_lat / plateau_lat:.1f}x)")
    print()
    print("Segments (num_ways range, median latency, #points):")
    bounds = [0, knee_idx, len(points)]
    labels = ["flat (all probed tags fit)", "thrashing (exceeds associativity)"]
    for k, (s, e) in enumerate(zip(bounds[:-1], bounds[1:])):
        seg = points[s:e]
        if not seg:
            continue
        lat_med = statistics.median(lat for _, lat in seg)
        print(f"  {labels[k]:<34} ways {seg[0][0]:>3}-{seg[-1][0]:<3}  "
              f"median={lat_med:.2f} ticks  n={len(seg)}")


if __name__ == "__main__":
    main()
