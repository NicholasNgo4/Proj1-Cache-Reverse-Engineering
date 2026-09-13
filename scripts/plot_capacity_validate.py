#!/usr/bin/env python3
"""Plot the discrete-size capacity_validate data (run_capacity_validate.sh /
analyze_capacity_validate.py), reusing plot_capacity.py's box-plot code and
visual conventions.

Unlike plot_capacity.py's own curve plot (built for a continuous log-spaced
sweep, where consecutive points are always close together), this script's
four input groups (l1d/l2/l3/dram) have deliberate large gaps between them
(e.g. 512 KiB -> 16 MiB) with no data in between -- connecting those points
with a straight line would visually claim a smooth ramp across a span that
was never actually measured. So each group is plotted as its own
disconnected line segment instead of one continuous curve.

Usage:
    python3 scripts/plot_capacity_validate.py \\
        --l1d data_processed/sunbird/capacity_validate/l1d_summary.csv \\
        --l2  data_processed/sunbird/capacity_validate/l2_summary.csv \\
        --l3  data_processed/sunbird/capacity_validate/l3_summary.csv \\
        --dram data_processed/sunbird/capacity_validate/dram_summary.csv \\
        -o data_processed/sunbird/capacity_validate/plots --machine sunbird \\
        --expected-boundary 32768 --expected-boundary 262144 \\
        --expected-boundary 31457280 \\
        --flagged-boundary 26999992 --flagged-boundary 149999845
"""
import argparse
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plot_capacity import (human_bytes, style_axes, load_summaries,
                            plot_boxplots, parse_size)

GROUP_STYLE = {
    "l1d": dict(color="#1b6ca8", marker="o", label="L1D group (16-64 KiB)"),
    "l2": dict(color="#2a9d3e", marker="s", label="L2 group (128-512 KiB)"),
    "l3": dict(color="#c9622d", marker="^", label="L3 group (16-64 MiB)"),
    "dram": dict(color="#8b3a9e", marker="D", label="DRAM group (96-256 MiB)"),
}


def load_group(path):
    by_pattern = load_summaries([path])
    rows = by_pattern.get("random", {})
    pts = sorted((sz, float(r["median"]), float(r["q1"]), float(r["q3"]))
                 for sz, r in rows.items())
    return pts


def plot_curve(groups, machine, out_prefix, title_suffix,
               expected_boundaries=(), flagged_boundaries=()):
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    all_sizes = []
    for name, pts in groups.items():
        if not pts:
            continue
        style = GROUP_STYLE.get(name, dict(color="C0", marker="^", label=name))
        xs = [p[0] for p in pts]
        med = [p[1] for p in pts]
        q1 = [p[2] for p in pts]
        q3 = [p[3] for p in pts]
        all_sizes.extend(xs)
        ax.fill_between(xs, q1, q3, color=style["color"], alpha=0.15, linewidth=0)
        ax.plot(xs, med, color=style["color"], marker=style["marker"], markersize=5,
                linewidth=1.8, label=style["label"])

    for b in expected_boundaries:
        ax.axvline(b, color="#2a9d3e", linestyle="--", linewidth=1.2, alpha=0.8)
    for b in flagged_boundaries:
        ax.axvline(b, color="#c0392b", linestyle=":", linewidth=1.4, alpha=0.9)

    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: human_bytes(int(v))))
    true_min, true_max = min(all_sizes), max(all_sizes)
    lo_oct = math.floor(math.log2(true_min))
    hi_oct = math.ceil(math.log2(true_max))
    regular = [2 ** e for e in range(lo_oct, hi_oct + 1, 3)]
    tick_locs = sorted(set(regular + [true_min, true_max]))
    ax.set_xticks(tick_locs)
    ax.set_xticks([], minor=True)

    ax.set_xlabel("Working-set size (true log2 position -- gaps between groups are "
                  "untested spans, not measured plateaus)")
    ax.set_ylabel("Median latency (timer ticks / access)")
    if expected_boundaries or flagged_boundaries:
        title = f"{machine}: capacity_validate, expected (green --) vs. flagged (red :) boundaries"
    else:
        title = f"{machine}: capacity_validate discrete-size groups (random pattern)"
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=11)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--l1d")
    ap.add_argument("--l2")
    ap.add_argument("--l3")
    ap.add_argument("--dram")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("--machine", default="")
    ap.add_argument("--title-suffix", default="")
    ap.add_argument("--expected-boundary", action="append", type=parse_size, default=[],
                     help="a candidate boundary from the expected/textbook hierarchy "
                          "(shown as a green dashed line)")
    ap.add_argument("--flagged-boundary", action="append", type=parse_size, default=[],
                     help="a previously-reported detector boundary being re-tested "
                          "(shown as a red dashed line)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    paths = {"l1d": args.l1d, "l2": args.l2, "l3": args.l3, "dram": args.dram}
    groups = {name: load_group(p) for name, p in paths.items() if p}
    if not any(groups.values()):
        print("No data loaded.", file=sys.stderr)
        return 1

    plot_curve(groups, args.machine, os.path.join(args.out_dir, "capacity_validate_curve"),
               args.title_suffix)

    # Second figure, same data, with vertical markers for expected vs.
    # flagged boundaries -- kept separate so the plain curve above stays
    # uncluttered.
    plot_curve(groups, args.machine,
               os.path.join(args.out_dir, "capacity_validate_curve_annotated"),
               args.title_suffix, args.expected_boundary, args.flagged_boundary)

    # Box plots: reuse plot_capacity.py's implementation directly (it just
    # looks up the nearest sampled point per boundary, which works fine
    # even across our groups' gaps).
    all_boundaries = args.expected_boundary + args.flagged_boundary
    merged = {"random": {}}
    for pts_source in (args.l1d, args.l2, args.l3, args.dram):
        if not pts_source:
            continue
        bp = load_summaries([pts_source])
        merged["random"].update(bp.get("random", {}))
    plot_boxplots(merged, args.machine,
                  os.path.join(args.out_dir, "capacity_validate_boxplots"),
                  args.title_suffix, "random", all_boundaries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
