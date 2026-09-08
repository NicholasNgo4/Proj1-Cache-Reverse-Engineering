#!/usr/bin/env python3
"""Plot the required capacity-sweep evidence from one or more processed
summary CSVs (output of summarize_raw.py on --experiment capacity raw data).

Produces, per machine:
  1. capacity_curve.{pdf,png} -- median ticks/access vs. working-set size,
     one line per access pattern (random vs. sequential), with an IQR band.
     This is the "latency vs. working-set size" plot the homework requires,
     and overlaying both patterns is the required prefetcher sanity check.
  2. capacity_boxplots.{pdf,png} -- box-and-whisker evidence at representative
     working-set sizes (immediately below/at/above each --boundary given, or
     auto-picked if none are given), drawn from the summary's own percentile
     columns (q1/median/q3/p5/p95) rather than re-reading raw per-batch data.

Multiple summary CSVs (e.g. a coarse sweep plus one or more dense zoom-window
sweeps) can be passed together; rows are merged and deduplicated by
(size_bytes, pattern) before plotting, so a dense re-sample of a region
already covered by the coarse sweep simply overrides those points.

Usage:
    python3 scripts/plot_capacity.py \\
        data_processed/sunbird/capacity/coarse_random_summary.csv \\
        data_processed/sunbird/capacity/coarse_sequential_summary.csv \\
        data_processed/sunbird/capacity/capacity_denseA_random_*_summary.csv \\
        data_processed/sunbird/capacity/capacity_denseB_random_*_summary.csv \\
        -o data_processed/sunbird/capacity/plots --machine sunbird \\
        --boundary 32768 --boundary 20971520
"""
import argparse
import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

REQUIRED_COLS = {"size_bytes", "pattern", "median", "q1", "q3", "p5", "p95", "n_outliers", "n"}


def combine_duplicate_rows(size, pattern, rows):
    """Combines multiple summary rows for the same (pattern, size) -- e.g. an
    overlapping coarse+dense sweep, or a deliberate repeat run -- instead of
    silently keeping whichever file happened to load last. A single noisy
    point from one run (transient scheduling interference, say) would
    otherwise overwrite a clean point from another run with no visible
    trace. Medians are averaged; the whisker range is the union (min of
    p5s, max of p95s) so combining runs widens the shown spread rather than
    hiding disagreement between them."""
    if len(rows) == 1:
        combined = dict(rows[0])
        combined["n_runs"] = 1
        combined["run_spread_pct"] = 0.0
        combined["n_total"] = int(float(rows[0].get("n", 0)))
        return combined
    medians = [float(r["median"]) for r in rows]
    q1s = [float(r["q1"]) for r in rows]
    q3s = [float(r["q3"]) for r in rows]
    p5s = [float(r["p5"]) for r in rows]
    p95s = [float(r["p95"]) for r in rows]
    n_outliers = [int(float(r["n_outliers"])) for r in rows]
    n_totals = [int(float(r.get("n", 0))) for r in rows]
    mean_median = sum(medians) / len(medians)
    spread = max(medians) - min(medians)
    spread_pct = (spread / mean_median * 100) if mean_median else 0.0
    if spread_pct > 20:
        print(f"  note: {human_bytes(size)} ({pattern}) has {len(rows)} overlapping "
              f"summary rows with medians {[round(m, 1) for m in medians]} "
              f"(spread {spread:.1f} ticks, {spread_pct:.1f}%) -- averaging, widening "
              f"whiskers to the union", file=sys.stderr)
    combined = dict(rows[0])
    combined["median"] = mean_median
    combined["q1"] = sum(q1s) / len(q1s)
    combined["q3"] = sum(q3s) / len(q3s)
    combined["p5"] = min(p5s)
    combined["p95"] = max(p95s)
    combined["n_outliers"] = sum(n_outliers)
    combined["n_runs"] = len(rows)
    combined["run_spread_pct"] = spread_pct
    combined["n_total"] = sum(n_totals)
    return combined


def load_summaries(paths):
    """Returns {pattern: {size_bytes: row_dict}}, combining duplicate
    (pattern, size) rows across input files via combine_duplicate_rows()
    rather than letting the last file loaded silently win."""
    raw = {}
    for path in paths:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not REQUIRED_COLS.issubset(reader.fieldnames):
                missing = REQUIRED_COLS - set(reader.fieldnames or [])
                raise ValueError(f"{path}: missing expected column(s) {missing} -- "
                                 f"is this a capacity summary from summarize_raw.py?")
            for row in reader:
                pattern = row["pattern"]
                size = int(float(row["size_bytes"]))
                raw.setdefault(pattern, {}).setdefault(size, []).append(row)

    by_pattern = {}
    for pattern, sizes in raw.items():
        by_pattern[pattern] = {
            size: combine_duplicate_rows(size, pattern, rows)
            for size, rows in sizes.items()
        }
    return by_pattern


def human_bytes(n):
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):g} MiB"
    if n >= 1024:
        return f"{n / 1024:g} KiB"
    return f"{n} B"


def style_axes(ax):
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(1.2)
        ax.spines[side].set_color("black")
    ax.tick_params(width=1.1, labelsize=11)


PATTERN_STYLE = {
    "random": dict(color="black", marker="o", label="Randomized dependent chain"),
    "sequential": dict(color="0.55", marker="s", label="Sequential control (prefetcher check)"),
}


def plot_curve(by_pattern, machine, out_prefix, title_suffix, log_y):
    fig, ax = plt.subplots(figsize=(7.5, 5))

    all_sizes = []
    for pattern, sizes in sorted(by_pattern.items()):
        pts = sorted((sz, float(row["median"]), float(row["q1"]), float(row["q3"]))
                     for sz, row in sizes.items())
        xs = [p[0] for p in pts]
        all_sizes.extend(xs)
        med = [p[1] for p in pts]
        q1 = [p[2] for p in pts]
        q3 = [p[3] for p in pts]
        style = PATTERN_STYLE.get(pattern, dict(color="C0", marker="^", label=pattern))
        ax.fill_between(xs, q1, q3, color=style["color"], alpha=0.15, linewidth=0)
        ax.plot(xs, med, color=style["color"], marker=style["marker"], markersize=4,
                 linewidth=1.6, label=style["label"])

    ax.set_xscale("log", base=2)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: human_bytes(int(v))))
    # The default log-scale locator doesn't reliably land a tick on the
    # actual largest swept size, so the right edge of the sweep can be
    # unlabeled even though data extends to it. Force ticks at every 3rd
    # octave (8x) from the smallest to largest size actually plotted, and
    # always add the exact max/min so the swept range's edges are labeled.
    import math
    lo_oct = math.floor(math.log2(min(all_sizes)))
    hi_oct = math.ceil(math.log2(max(all_sizes)))
    tick_locs = sorted(set([2 ** e for e in range(lo_oct, hi_oct + 1, 3)] +
                            [min(all_sizes), max(all_sizes)]))
    ax.set_xticks(tick_locs)
    ax.set_xticks([], minor=True)
    if log_y:
        ax.set_yscale("log", base=2)
    ax.set_xlabel("Working-set size")
    ax.set_ylabel("Median latency (timer ticks / access)")
    title = f"{machine}: capacity sweep (dependent pointer chase)"
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=11)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    fig.tight_layout()

    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)


def pick_box_sizes(sorted_sizes, boundaries):
    """Returns an ordered list of (size, boundary_label, position_tag) picks:
    for each boundary, the sampled point immediately below it, the closest
    one to it, and the one immediately above it (deduplicated). If no
    boundaries are given, auto-pick 6 log-evenly-spaced points instead."""
    picks = []
    if boundaries:
        for b in boundaries:
            idx = min(range(len(sorted_sizes)), key=lambda i: abs(sorted_sizes[i] - b))
            for j, tag in ((idx - 1, "below"), (idx, "near"), (idx + 1, "above")):
                if 0 <= j < len(sorted_sizes):
                    picks.append((sorted_sizes[j], human_bytes(b), tag))
    else:
        n = len(sorted_sizes)
        step = max(1, n // 6)
        for i in range(0, n, step):
            picks.append((sorted_sizes[i], None, None))

    seen = set()
    deduped = []
    for size, boundary_label, tag in picks:
        if size not in seen:
            seen.add(size)
            deduped.append((size, boundary_label, tag))
    return deduped


def plot_boxplots(by_pattern, machine, out_prefix, title_suffix, pattern, boundaries):
    if pattern not in by_pattern:
        print(f"No '{pattern}' pattern rows found; skipping box plots.", file=sys.stderr)
        return

    sizes = by_pattern[pattern]
    sorted_sizes = sorted(sizes)
    picks = pick_box_sizes(sorted_sizes, boundaries)
    if not picks:
        print("No box-plot points selected; skipping.", file=sys.stderr)
        return

    stats = []
    labels = []
    annotations = []
    boundary_labels_seen = []
    for size, boundary_label, tag in picks:
        row = sizes[size]
        stats.append({
            "med": float(row["median"]),
            "q1": float(row["q1"]),
            "q3": float(row["q3"]),
            "whislo": float(row["p5"]),
            "whishi": float(row["p95"]),
            "fliers": [],
        })
        if boundary_label:
            labels.append(f"{human_bytes(size)}\n({tag})")
            if boundary_label not in boundary_labels_seen:
                boundary_labels_seen.append(boundary_label)
        else:
            labels.append(human_bytes(size))

        n_outliers = int(float(row["n_outliers"]))
        n_runs = int(row.get("n_runs", 1))
        n_total = int(row.get("n_total", int(float(row.get("n", 0))) * 1000))
        lines = [f"n_outliers={n_outliers}"]
        if n_runs > 1:
            lines.append(f"{n_runs} runs, {int(row['run_spread_pct'])}% spread")
        else:
            lines.append(f"{n_total:,} samples")
        annotations.append(lines)

    fig, ax = plt.subplots(figsize=(max(7.5, 1.6 * len(stats)), 5.8))
    bp = ax.bxp(stats, showfliers=False, patch_artist=True)
    for box in bp["boxes"]:
        box.set(facecolor="0.85", edgecolor="black", linewidth=1.2)
    for element in ("whiskers", "caps", "medians"):
        for line in bp[element]:
            line.set(color="black", linewidth=1.2)

    ax.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("Latency (timer ticks / access)")
    title = f"{machine}: capacity box plots, {pattern} pattern (whiskers = p5/p95)"
    if title_suffix:
        title += f"\n{title_suffix}"
    if boundary_labels_seen:
        title += f"\ntested boundaries: {', '.join(boundary_labels_seen)}"
    ax.set_title(title, fontsize=11)
    style_axes(ax)

    ymax = max(s["whishi"] for s in stats)
    for i, lines in enumerate(annotations, start=1):
        for j, line in enumerate(lines):
            ax.text(i, ymax * (1.03 + 0.06 * j), line, ha="center", va="bottom", fontsize=8)
    ax.set_ylim(top=ymax * (1.10 + 0.06 * max(len(a) for a in annotations)))

    fig.tight_layout()
    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)


def parse_size(s):
    s = s.strip().upper()
    mult = 1
    for suffix, m in (("KIB", 1024), ("MIB", 1024 * 1024), ("GIB", 1024 ** 3),
                      ("K", 1000), ("M", 1_000_000)):
        if s.endswith(suffix):
            return int(float(s[:-len(suffix)]) * m)
    return int(float(s))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary_csvs", nargs="+", help="one or more capacity summary CSVs")
    ap.add_argument("-o", "--out-dir", required=True, help="output directory for plots")
    ap.add_argument("--machine", default="", help="machine name for plot titles")
    ap.add_argument("--title-suffix", default="", help="extra text appended to plot titles")
    ap.add_argument("--boundary", action="append", type=parse_size, default=[],
                     help="candidate cache-boundary size (bytes, or e.g. 256KiB/8MiB); "
                          "repeatable. Box plots show the sampled point immediately "
                          "below/at/above each one.")
    ap.add_argument("--box-pattern", default="random",
                     help="which pattern's box plots to draw (default: random)")
    ap.add_argument("--log-y", action="store_true",
                     help="use a log y-axis on the capacity curve")
    args = ap.parse_args()

    import os
    os.makedirs(args.out_dir, exist_ok=True)

    by_pattern = load_summaries(args.summary_csvs)
    if not by_pattern:
        print("No data loaded.", file=sys.stderr)
        return 1

    plot_curve(by_pattern, args.machine, os.path.join(args.out_dir, "capacity_curve"),
               args.title_suffix, args.log_y)
    plot_boxplots(by_pattern, args.machine, os.path.join(args.out_dir, "capacity_boxplots"),
                  args.title_suffix, args.box_pattern, args.boundary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
