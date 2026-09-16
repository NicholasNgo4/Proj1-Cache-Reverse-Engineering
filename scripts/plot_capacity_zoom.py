#!/usr/bin/env python3
"""Plot zoomed-in L1/L2/LLC capacity curves for Section 5 of the report.

Section 5's per-machine "Cache Hierarchy and Capacity" subsubsection already
cites one full-range (1 KiB-1 GiB+) capacity_curve.png per machine
(scripts/plot_capacity.py); that plot's log-x axis compresses each
individual level's own knee/plateau into a few pixels. This script re-plots
the SAME underlying summary data (no new sweeps, no new C code) three times
per machine, each time zoomed to an octave window centered on one level's
own boundary, so each transition is actually readable.

Reuses plot_capacity.load_summaries()/style_axes()/human_bytes() unchanged
-- only the x-axis window and per-panel title differ from plot_capacity.py's
own plot_curve().

Usage:
    python3 scripts/plot_capacity_zoom.py \\
        --machine sunbird --level L1 --boundary 32768 \\
        --out data_processed/sunbird/capacity/plots/capacity_zoom_L1 \\
        data_processed/sunbird/capacity/*_summary.csv
"""
import argparse
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from plot_capacity import load_summaries, human_bytes, style_axes, PATTERN_STYLE

# How many octaves (powers of two) to show on either side of the boundary.
# +-4 octaves = a 256x window (e.g. 32,768 B -> 2,048 B..524,288 B), wide
# enough to show the flat shelf below AND the climb into the next level
# above for every machine in this project (checked against the narrowest
# gap on the team, Skylark's L1=32,768 B / L2=524,288 B, a 16x/4-octave
# gap) without the window being so wide it re-compresses the knee the same
# way the full-range plot does.
WINDOW_OCTAVES = 4.0


def plot_zoom(by_pattern, machine, level, boundary, out_prefix, title_suffix):
    lo = boundary / (2 ** WINDOW_OCTAVES)
    hi = boundary * (2 ** WINDOW_OCTAVES)

    fig, ax = plt.subplots(figsize=(7, 4.6))
    any_plotted = False
    for pattern, sizes in sorted(by_pattern.items()):
        pts = sorted((sz, float(row["median"]), float(row["q1"]), float(row["q3"]))
                     for sz, row in sizes.items() if lo <= sz <= hi)
        if not pts:
            continue
        any_plotted = True
        xs = [p[0] for p in pts]
        med = [p[1] for p in pts]
        q1 = [p[2] for p in pts]
        q3 = [p[3] for p in pts]
        style = PATTERN_STYLE.get(pattern, dict(color="C0", marker="^", label=pattern))
        ax.fill_between(xs, q1, q3, color=style["color"], alpha=0.15, linewidth=0)
        ax.plot(xs, med, color=style["color"], marker=style["marker"], markersize=4,
                 linewidth=1.6, label=style["label"])

    if not any_plotted:
        print(f"  WARNING: no points in [{human_bytes(int(lo))}, {human_bytes(int(hi))}] "
              f"for {machine}/{level} -- skipping", file=sys.stderr)
        plt.close(fig)
        return False

    ax.axvline(boundary, color="firebrick", linestyle="--", linewidth=1.1, alpha=0.8,
               label=f"candidate {human_bytes(boundary)}")

    ax.set_xscale("log", base=2)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: human_bytes(int(v))))
    lo_oct = math.floor(math.log2(lo))
    hi_oct = math.ceil(math.log2(hi))
    ax.set_xticks([2 ** e for e in range(lo_oct, hi_oct + 1)])
    ax.set_xticks([], minor=True)
    ax.tick_params(axis="x", labelrotation=40, labelsize=8)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Working-set size")
    ax.set_ylabel("Median latency (ticks/access)")
    title = f"{machine}: {level} zoom"
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=10)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()

    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary_csvs", nargs="+")
    ap.add_argument("--machine", required=True)
    ap.add_argument("--level", required=True, help="label for the plot title, e.g. L1/L2/LLC")
    ap.add_argument("--boundary", required=True, type=float, help="candidate boundary, bytes")
    ap.add_argument("--out", required=True, help="output path prefix (no extension)")
    ap.add_argument("--title-suffix", default="")
    args = ap.parse_args()

    by_pattern = load_summaries(args.summary_csvs)
    if not by_pattern:
        print("No data loaded.", file=sys.stderr)
        return 1
    ok = plot_zoom(by_pattern, args.machine, args.level, args.boundary, args.out,
                    args.title_suffix)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
