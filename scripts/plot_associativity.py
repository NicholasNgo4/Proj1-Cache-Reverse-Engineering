#!/usr/bin/env python3
"""Plot the required associativity-sweep evidence from one or more processed
summary CSVs (output of summarize_raw.py on --experiment associativity raw
data for a SINGLE cache level, i.e. a single cache_bytes stride).

Produces, per machine/level:
  1. associativity_curve.{pdf,png} -- median ticks/access vs. num_ways_probed,
     one line per access pattern (random vs. sequential), with an IQR band.
     Expected shape: flat while num_ways_probed <= true associativity, then
     a sharp step up once it's exceeded (see detect_associativity.py).
  2. associativity_boxplots.{pdf,png} -- box-and-whisker evidence at
     representative num_ways values (immediately below/at/above each
     --estimate given, or auto-picked if none given), drawn from the
     summary's own percentile columns (q1/median/q3/p5/p95).

Multiple summary CSVs (e.g. a base sweep plus reproducibility repeats) can
be passed together; rows are merged and deduplicated by (num_ways_probed,
pattern) before plotting, so overlapping points are averaged rather than
letting the last file silently win.

Usage:
    python3 scripts/plot_associativity.py \\
        data_processed/sunbird/associativity/L1/base_random_summary.csv \\
        data_processed/sunbird/associativity/L1/base_sequential_summary.csv \\
        -o data_processed/sunbird/associativity/L1/plots --machine sunbird \\
        --level L1 --estimate 8
"""
import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REQUIRED_COLS = {"num_ways_probed", "pattern", "median", "q1", "q3", "p5", "p95",
                  "n_outliers", "n"}


def combine_duplicate_rows(num_ways, pattern, rows):
    """Combines multiple summary rows for the same (pattern, num_ways) --
    e.g. overlapping sweeps or a deliberate repeat run -- instead of
    silently keeping whichever file happened to load last. Medians are
    averaged; the whisker range is the union (min of p5s, max of p95s) so
    combining runs widens the shown spread rather than hiding disagreement
    between them. Mirrors plot_line_size.py's combine_duplicate_rows()."""
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
        print(f"  note: num_ways={num_ways} ({pattern}) has {len(rows)} overlapping "
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
    """Returns {pattern: {num_ways: row_dict}}, combining duplicate
    (pattern, num_ways) rows across input files, plus the cache_bytes
    stride recorded in the data (for the plot title)."""
    raw = {}
    cache_bytes = None
    for path in paths:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not REQUIRED_COLS.issubset(reader.fieldnames):
                missing = REQUIRED_COLS - set(reader.fieldnames or [])
                raise ValueError(f"{path}: missing expected column(s) {missing} -- is "
                                 f"this an associativity summary from summarize_raw.py?")
            for row in reader:
                pattern = row["pattern"]
                num_ways = int(float(row["num_ways_probed"]))
                raw.setdefault(pattern, {}).setdefault(num_ways, []).append(row)
                if cache_bytes is None and "cache_bytes" in row:
                    try:
                        cache_bytes = int(float(row["cache_bytes"]))
                    except ValueError:
                        pass

    by_pattern = {}
    for pattern, ways in raw.items():
        by_pattern[pattern] = {
            num_ways: combine_duplicate_rows(num_ways, pattern, rows)
            for num_ways, rows in ways.items()
        }
    return by_pattern, cache_bytes


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


def plot_curve(by_pattern, machine, level, cache_bytes, out_prefix, title_suffix, estimate):
    fig, ax = plt.subplots(figsize=(7.5, 5))

    for pattern, ways in sorted(by_pattern.items()):
        pts = sorted((n, float(row["median"]), float(row["q1"]), float(row["q3"]))
                     for n, row in ways.items())
        xs = [p[0] for p in pts]
        med = [p[1] for p in pts]
        q1 = [p[2] for p in pts]
        q3 = [p[3] for p in pts]
        style = PATTERN_STYLE.get(pattern, dict(color="C0", marker="^", label=pattern))
        ax.fill_between(xs, q1, q3, color=style["color"], alpha=0.15, linewidth=0)
        ax.plot(xs, med, color=style["color"], marker=style["marker"], markersize=4,
                 linewidth=1.6, label=style["label"])

    if estimate is not None:
        ax.axvline(estimate + 0.5, color="firebrick", linestyle="--", linewidth=1.2,
                   label=f"detected associativity = {estimate}-way")

    ax.set_xlabel("Same-set nodes probed (num_ways_probed)")
    ax.set_ylabel("Median latency (timer ticks / access)")
    ax.xaxis.get_major_locator().set_params(integer=True)
    title = f"{machine}: associativity sweep"
    if level:
        title += f", {level}"
    if cache_bytes:
        title += f" (stride={human_bytes(cache_bytes)})"
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=11)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=9, loc="best")
    fig.tight_layout()

    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)


def pick_box_ways(sorted_ways, estimate):
    """Returns an ordered list of (num_ways, tag) picks: the estimate itself
    plus a couple of points on either side, so the box plots show the
    flat-vs-thrashing transition directly. Falls back to 6 evenly-spaced
    points if no estimate is given."""
    picks = []
    if estimate is not None:
        idx = min(range(len(sorted_ways)), key=lambda i: abs(sorted_ways[i] - estimate))
        for j, tag in ((idx - 2, "below"), (idx - 1, "below"), (idx, "estimate"),
                       (idx + 1, "above"), (idx + 2, "above")):
            if 0 <= j < len(sorted_ways):
                picks.append((sorted_ways[j], tag))
    else:
        n = len(sorted_ways)
        step = max(1, n // 6)
        for i in range(0, n, step):
            picks.append((sorted_ways[i], None))

    seen = set()
    deduped = []
    for num_ways, tag in picks:
        if num_ways not in seen:
            seen.add(num_ways)
            deduped.append((num_ways, tag))
    return deduped


def plot_boxplots(by_pattern, machine, level, out_prefix, title_suffix, pattern, estimate):
    if pattern not in by_pattern:
        print(f"No '{pattern}' pattern rows found; skipping box plots.", file=sys.stderr)
        return

    ways = by_pattern[pattern]
    sorted_ways = sorted(ways)
    picks = pick_box_ways(sorted_ways, estimate)
    if not picks:
        print("No box-plot points selected; skipping.", file=sys.stderr)
        return

    stats = []
    labels = []
    annotations = []
    for num_ways, tag in picks:
        row = ways[num_ways]
        stats.append({
            "med": float(row["median"]),
            "q1": float(row["q1"]),
            "q3": float(row["q3"]),
            "whislo": float(row["p5"]),
            "whishi": float(row["p95"]),
            "fliers": [],
        })
        labels.append(f"{num_ways}\n({tag})" if tag else str(num_ways))

        n_outliers = int(float(row["n_outliers"]))
        n_runs = int(row.get("n_runs", 1))
        n_total = int(row.get("n_total", int(float(row.get("n", 0))) * 1000))
        lines = [f"n_outliers={n_outliers}"]
        if n_runs > 1:
            lines.append(f"{n_runs} runs, {int(row['run_spread_pct'])}% spread")
        else:
            lines.append(f"{n_total:,} samples")
        annotations.append(lines)

    fig, ax = plt.subplots(figsize=(max(7.5, 1.3 * len(stats)), 5.8))
    bp = ax.bxp(stats, showfliers=False, patch_artist=True)
    for box in bp["boxes"]:
        box.set(facecolor="0.85", edgecolor="black", linewidth=1.2)
    for element in ("whiskers", "caps", "medians"):
        for line in bp[element]:
            line.set(color="black", linewidth=1.2)

    ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("Same-set nodes probed (num_ways_probed)")
    ax.set_ylabel("Latency (timer ticks / access)")
    title = f"{machine}: associativity box plots"
    if level:
        title += f", {level}"
    title += f", {pattern} pattern (whiskers = p5/p95)"
    if title_suffix:
        title += f"\n{title_suffix}"
    if estimate is not None:
        title += f"\ndetected associativity estimate: {estimate}-way"
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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary_csvs", nargs="+", help="one or more associativity summary CSVs "
                     "(single cache level / cache_bytes stride)")
    ap.add_argument("-o", "--out-dir", required=True, help="output directory for plots")
    ap.add_argument("--machine", default="", help="machine name for plot titles")
    ap.add_argument("--level", default="", help="cache level label for plot titles (e.g. L1)")
    ap.add_argument("--title-suffix", default="", help="extra text appended to plot titles")
    ap.add_argument("--estimate", type=int, default=None,
                     help="detected associativity (ways); box plots bracket this value")
    ap.add_argument("--box-pattern", default="random",
                     help="which pattern's box plots to draw (default: random)")
    ap.add_argument("--curve-basename", default="associativity_curve",
                     help="output filename (no extension) for the curve plot -- override to "
                          "avoid overwriting an existing associativity_curve.{png,pdf} when "
                          "generating an alternate version (e.g. one with no detected-"
                          "associativity marker) from the same input data")
    ap.add_argument("--curve-only", action="store_true",
                     help="skip the box-plot figure entirely (it has no equivalent "
                          "'no estimate' variant, since box placement itself depends on "
                          "--estimate)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    by_pattern, cache_bytes = load_summaries(args.summary_csvs)
    if not by_pattern:
        print("No data loaded.", file=sys.stderr)
        return 1

    plot_curve(by_pattern, args.machine, args.level, cache_bytes,
               os.path.join(args.out_dir, args.curve_basename), args.title_suffix,
               args.estimate)
    if not args.curve_only:
        plot_boxplots(by_pattern, args.machine, args.level,
                      os.path.join(args.out_dir, "associativity_boxplots"), args.title_suffix,
                      args.box_pattern, args.estimate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
