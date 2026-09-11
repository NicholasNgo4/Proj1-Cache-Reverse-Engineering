#!/usr/bin/env python3
"""Infer the cache line size from a processed line_size-sweep summary
(output of summarize_raw.py on a --experiment line_size raw CSV).

Timing-only: this script never reads /proc/cpuinfo cache fields, sysfs
cache-topology files, or vendor cache tables -- only the measured
median-latency-vs-stride curve, per the Homework I Phase-I discipline. Treat
its output as a starting hypothesis to confirm against the plotted curve, not
as the final answer to paste into the report.

=== Model (corrected -- see history for the earlier, wrong version) ===

The line_size sweep holds a FIXED virtual footprint and varies the byte
stride between nodes. For stride <= true_line_size, `line_size / stride`
distinct nodes share each cache line, so a random chase step has a
1/(line_size/stride) chance of landing back in the *already-resident*
current line -- a much cheaper hit than landing in a new line. As stride
grows from small values toward true_line_size, that same-line-hit chance
falls monotonically to zero, so median latency RISES with stride and then
goes flat once stride >= true_line_size (every node now owns its own line,
so growing the stride further changes nothing about that hit rate).

That rise-then-plateau shape is where the line size lives, and it does NOT
depend on footprint_bytes at all -- confirmed empirically across 32/64/128
KiB footprints on the same machine, all saturating at the same stride.

There is a SEPARATE, later effect in the same sweep: distinct cache lines
touched is ~constant (~footprint_bytes / line_size) while stride <=
line_size (packing more nodes per line as stride shrinks does not change
how many lines the footprint spans), then FALLS as
footprint_bytes * line_size / stride once stride exceeds line_size. If
footprint_bytes was chosen to spill out of a cache level (elevated
plateau), that falling occupancy eventually drops back under that level's
capacity C, producing a further latency DROP at
stride_drop = line_size * (footprint_bytes / C) -- scaled by the
footprint/capacity ratio, NOT equal to the line size. The previous version
of this script mistook that capacity-driven drop for the line-size knee
and then tried to divide out the ratio via --boundary-bytes; the ratio
correction can't fully undo it because C (the real capacity) is not
directly known -- only whatever capacity boundary the footprint was
multiplied from, and any error in that boundary passes straight through.
This version instead looks for the ramp SATURATION point, which needs no
such correction.

Because the sweep also contains isolated single-point spikes at strides
that slice the 4096B page into very few pieces (256/512/1024 in our data)
-- an artifact of how few distinct sets those strides touch, not a
cache-topology fact this script asserts -- points that spike sharply above
their neighbor(s) are excluded from the search (see is_spike()).

Usage:
    python3 scripts/detect_line_size.py data_processed/<machine>/line_size/summary.csv
"""
import argparse
import statistics
import sys
import csv


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
    """Locates the LATER capacity-driven fall-off (see module docstring) --
    tracks a rolling HIGH baseline and returns the index of the first point
    where latency falls below it by at least rel_threshold, confirmed by
    `confirm` consecutive points staying down. Returns None if no drop is
    found (e.g. footprint_bytes never actually spilled out of a cache
    level anywhere in the swept stride range). Used only to bound the
    search for the saturation point to the pre-drop (elevated) segment --
    NOT to report a line-size estimate itself."""
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


def is_spike(points, i, spike_rel_threshold):
    """True if points[i] sits sharply above its immediate neighbor(s) on
    every side that exists -- flagged by shape alone (an isolated point far
    above its neighbors), not by asserting a specific cache associativity
    or set count. In our sweeps this catches strides that slice the 4096B
    page into very few pieces (256/512/1024), which show single-point
    conflict spikes even deep in an otherwise-flat, already-dropped region.
    At the first/last swept point only one neighbor exists, so that one
    comparison alone decides it."""
    lat = points[i][1]
    neighbors = []
    if i > 0:
        neighbors.append(points[i - 1][1])
    if i < len(points) - 1:
        neighbors.append(points[i + 1][1])
    if not neighbors:
        return False
    return all(lat > n * (1 + spike_rel_threshold) for n in neighbors)


def find_saturation(points, flat_tolerance, confirm, spike_rel_threshold):
    """Finds the stride at which the rising sub-line ramp saturates into
    its flat high plateau -- see module docstring. `points` must already
    be restricted to the pre-drop (elevated) segment. Spike points (see
    is_spike) are excluded before the flat-run search so an isolated
    conflict-miss spike can't break, or falsely start, a flat run.
    Returns the stride at the start of the first run of `confirm`
    mutually-close points, or None if no such run exists."""
    clean = [(s, lat) for i, (s, lat) in enumerate(points)
             if not is_spike(points, i, spike_rel_threshold)]
    if len(clean) < confirm:
        return None
    for start in range(len(clean) - confirm + 1):
        window = clean[start:start + confirm]
        vals = [w[1] for w in window]
        med = statistics.median(vals)
        if med > 0 and (max(vals) - min(vals)) <= flat_tolerance * med:
            return window[0][0]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary_csv")
    ap.add_argument("--drop-rel-threshold", type=float, default=0.25,
                     help="relative median-latency drop that flags the LATER "
                          "capacity-driven fall-off, used only to bound the search "
                          "region (default 0.25)")
    ap.add_argument("--drop-min-abs-ticks", type=float, default=3.0,
                     help="minimum absolute tick drop for that fall-off (default 3.0)")
    ap.add_argument("--drop-confirm", type=int, default=2,
                     help="consecutive points required to confirm that fall-off (default 2)")
    ap.add_argument("--flat-tolerance", type=float, default=0.01,
                     help="max relative spread within a window for it to count as the "
                          "flat plateau (default 0.01, i.e. 1%%). Deliberately tight: "
                          "repeat runs on a quiet core reproduce the true plateau to "
                          "within ~0.2-0.6%%, while even a visually gentle ramp still "
                          "spans several percent over any --confirm-sized window, so a "
                          "loose tolerance (e.g. 4%%) false-triggers partway up the ramp")
    ap.add_argument("--confirm", type=int, default=5,
                     help="consecutive points required to confirm the plateau (default "
                          "5). Needs enough plateau length to fit before the "
                          "capacity-driven drop -- see run_line_size.sh's "
                          "footprint multiplier, which is sized to leave this room")
    ap.add_argument("--min-rise-ticks", type=float, default=1.0,
                     help="minimum absolute rise from the first swept point to the "
                          "plateau for the result to be trusted -- guards against "
                          "reporting min_stride when footprint_bytes never actually "
                          "spilled and the whole curve is already flat (default 1.0)")
    ap.add_argument("--spike-rel-threshold", type=float, default=0.3,
                     help="relative excess above BOTH neighbors for a point to be "
                          "treated as an isolated conflict-miss spike and excluded "
                          "(default 0.3, i.e. 30%%)")
    ap.add_argument("--machine-readable", action="store_true",
                     help="print only the estimated line size in bytes, nothing else "
                          "-- for scripts to consume directly")
    args = ap.parse_args()

    points, footprint_bytes = load_points(args.summary_csv)
    if len(points) < 3:
        print("Not enough swept stride points to infer a line size.", file=sys.stderr)
        sys.exit(1)

    drop_idx = find_drop(points, args.drop_rel_threshold, args.drop_min_abs_ticks,
                          args.drop_confirm)
    pre_drop = points[:drop_idx] if drop_idx is not None else points

    sat_stride = find_saturation(pre_drop, args.flat_tolerance, args.confirm,
                                  args.spike_rel_threshold)

    if sat_stride is None:
        print("No ramp-saturation plateau detected in the pre-drop segment.",
              file=sys.stderr)
        if drop_idx is None:
            print("(no capacity-driven fall-off was found either -- footprint_bytes "
                  "may never have spilled out of any cache level in this swept "
                  "range; try a larger --footprint-bytes)", file=sys.stderr)
        sys.exit(1)

    # Robust floor for the rise check: the min over the whole ramp region
    # (every point strictly before the detected plateau), not literally
    # points[0] -- the smallest swept stride is occasionally a noisy outlier
    # itself (a one-time warm-up/TLB cost not fully amortized by the warmup
    # passes), which would otherwise make a perfectly good plateau look like
    # it never rose at all. This also protects against a messy/noisy
    # mid-range region (e.g. a footprint so large it spans multiple cache
    # levels) getting mistaken for a plateau: if the ramp region still dips
    # below the candidate plateau's own value anywhere, that candidate isn't
    # a real rise-then-flatten shape.
    plateau_lat = next(lat for s, lat in pre_drop if s == sat_stride)
    ramp_region = [lat for s, lat in pre_drop if s < sat_stride]
    floor_lat = min(ramp_region) if ramp_region else plateau_lat
    if plateau_lat - floor_lat < args.min_rise_ticks:
        print(f"Rejecting saturation at stride={sat_stride}B: only "
              f"{plateau_lat - floor_lat:.2f} ticks above the lowest point in the ramp "
              f"region below it ({floor_lat:.2f}) -- below --min-rise-ticks={args.min_rise_ticks:g}. "
              "This usually means footprint_bytes fit entirely in a cache level "
              "(no spill visible anywhere in this sweep) rather than that the line "
              "size is min_stride.", file=sys.stderr)
        sys.exit(1)

    if args.machine_readable:
        print(sat_stride)
        return

    print(f"Ramp-saturation line-size estimate: {sat_stride} bytes "
          f"(plateau median {plateau_lat:.2f} ticks, "
          f"{plateau_lat - floor_lat:.2f} ticks above the ramp's floor)")
    if drop_idx is not None:
        drop_stride = points[drop_idx][0]
        print(f"(capacity-driven fall-off separately observed at stride={drop_stride}B "
              f"-- NOT the line size; that point is scaled by "
              f"footprint_bytes/cache_capacity, see module docstring)")
    else:
        print("(no capacity-driven fall-off observed within max_stride -- the "
              "plateau above is still trustworthy as the ramp-saturation point, "
              "but consider sweeping a larger max_stride to see the fall-off too "
              "as a cross-check)")

    print()
    print("Segments (stride range, median latency, #points):")
    sat_idx = next(i for i, (s, _) in enumerate(points) if s == sat_stride)
    bounds = sorted(set([0, sat_idx, drop_idx if drop_idx is not None else len(points),
                          len(points)]))
    labels = ["ramp (rising, sub-line reuse)", "plateau (flat, at/above line size)",
              "dropped (capacity spill relieved)"]
    for k, (s, e) in enumerate(zip(bounds[:-1], bounds[1:])):
        seg = points[s:e]
        if not seg:
            continue
        lat_med = statistics.median(lat for _, lat in seg)
        label = labels[min(k, len(labels) - 1)]
        print(f"  {label:<32} {seg[0][0]:>6}-{seg[-1][0]:<6} bytes  "
              f"median={lat_med:.2f} ticks  n={len(seg)}")


if __name__ == "__main__":
    main()
