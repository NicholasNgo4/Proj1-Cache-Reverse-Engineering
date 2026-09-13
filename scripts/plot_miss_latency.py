#!/usr/bin/env python3
"""Plot the required miss/next-level-latency evidence from one or more
processed summary CSVs (output of summarize_raw.py on --experiment
miss_latency raw data for a SINGLE target/eviction-set transition).

Produces one box-plot figure, miss_latency_boxplots.{pdf,png}, with one box
per traversal pattern (random vs. sequential, the required prefetcher-
sanity control on the eviction-set walk), drawn from the summary's own
percentile columns (q1/median/q3/p5/p95).

Optionally cross-references a paired hit_latency processed summary
(--hit-latency-summary), filtered to the SOURCE level's own dependent-mode
median, to annotate the incremental miss penalty relative to the previous
level's hit latency -- the second number PROJECT 1.pdf item 6 asks for,
computed here as a simple derived quantity rather than by a separate
detection script.

Multiple summary CSVs (e.g. a base run plus reproducibility repeats) can be
passed together; rows are merged and deduplicated by pattern before
plotting, so overlapping points are averaged rather than letting the last
file silently win (mirrors plot_associativity.py's combine_duplicate_rows()).

Usage:
    python3 scripts/plot_miss_latency.py \\
        data_processed/sunbird/latency/miss/L1_to_LLC/base_*_summary_*.csv \\
        -o data_processed/sunbird/latency/miss/L1_to_LLC/plots --machine sunbird \\
        --transition L1_to_LLC \\
        --hit-latency-summary data_processed/sunbird/latency/hit/L1/base_random_summary_*.csv
"""
import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REQUIRED_COLS = {"target_bytes", "evict_bytes", "pattern", "median", "q1", "q3",
                  "p5", "p95", "n_outliers", "n"}


def combine_duplicate_rows(pattern, rows):
    """Combines multiple summary rows for the same pattern -- e.g. a base
    run plus repeats -- instead of silently keeping whichever file happened
    to load last. Medians are averaged; the whisker range is the union (min
    of p5s, max of p95s). Mirrors plot_associativity.py's function of the
    same name."""
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
        print(f"  note: pattern={pattern} has {len(rows)} overlapping summary rows "
              f"with medians {[round(m, 1) for m in medians]} (spread {spread:.1f} "
              f"ticks, {spread_pct:.1f}%) -- averaging, widening whiskers to the union",
              file=sys.stderr)
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
    """Returns {pattern: row_dict}, combining duplicate rows across input
    files, plus (target_bytes, evict_bytes) recorded in the data (for the
    plot title)."""
    raw = {}
    target_bytes = None
    evict_bytes = None
    for path in paths:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not REQUIRED_COLS.issubset(reader.fieldnames):
                missing = REQUIRED_COLS - set(reader.fieldnames or [])
                raise ValueError(f"{path}: missing expected column(s) {missing} -- is "
                                 f"this a miss_latency summary from summarize_raw.py?")
            for row in reader:
                raw.setdefault(row["pattern"], []).append(row)
                if target_bytes is None and "target_bytes" in row:
                    try:
                        target_bytes = int(float(row["target_bytes"]))
                        evict_bytes = int(float(row["evict_bytes"]))
                    except ValueError:
                        pass

    return {p: combine_duplicate_rows(p, rows) for p, rows in raw.items()}, target_bytes, evict_bytes


def load_hit_latency_median(paths, pattern="random"):
    """Reads one or more hit_latency summary CSVs and returns the dependent-
    mode median for the given pattern, or None if not found/given. Used only
    to annotate the incremental miss penalty; a missing/unparseable file is
    not fatal to the main plot."""
    if not paths:
        return None
    medians = []
    for path in paths:
        try:
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("load_mode") == "dependent" and row.get("pattern") == pattern:
                        medians.append(float(row["median"]))
        except (OSError, ValueError, KeyError):
            continue
    if not medians:
        return None
    return sum(medians) / len(medians)


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


def plot_boxplots(by_pattern, machine, transition, target_bytes, evict_bytes,
                   out_prefix, title_suffix, hit_latency_median):
    order = ["random", "sequential"]
    picks = [p for p in order if p in by_pattern]
    if not picks:
        print("No data loaded; skipping box plots.", file=sys.stderr)
        return

    stats = []
    labels = []
    annotations = []
    for pattern in picks:
        row = by_pattern[pattern]
        stats.append({
            "med": float(row["median"]),
            "q1": float(row["q1"]),
            "q3": float(row["q3"]),
            "whislo": float(row["p5"]),
            "whishi": float(row["p95"]),
            "fliers": [],
        })
        labels.append(pattern)

        n_outliers = int(float(row["n_outliers"]))
        n_runs = int(row.get("n_runs", 1))
        n_total = int(row.get("n_total", int(float(row.get("n", 0)))))
        lines = [f"n_outliers={n_outliers}"]
        if n_runs > 1:
            lines.append(f"{n_runs} runs, {int(row['run_spread_pct'])}% spread")
        else:
            lines.append(f"{n_total:,} trials")
        if hit_latency_median is not None:
            penalty = float(row["median"]) - hit_latency_median
            lines.append(f"penalty vs. source hit: +{penalty:.1f} ticks")
        annotations.append(lines)

    fig, ax = plt.subplots(figsize=(max(6.5, 1.8 * len(stats)), 5.8))
    bp = ax.bxp(stats, showfliers=False, patch_artist=True)
    for box in bp["boxes"]:
        box.set(facecolor="0.85", edgecolor="black", linewidth=1.2)
    for element in ("whiskers", "caps", "medians"):
        for line in bp[element]:
            line.set(color="black", linewidth=1.2)

    if hit_latency_median is not None:
        ax.axhline(hit_latency_median, color="firebrick", linestyle="--", linewidth=1.2,
                   label=f"source-level hit latency ({hit_latency_median:.1f} ticks)")
        ax.legend(frameon=False, fontsize=9, loc="best")

    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Reload latency (timer ticks, single dependent access)")
    title = f"{machine}: miss/next-level latency"
    if transition:
        title += f", {transition}"
    if target_bytes and evict_bytes:
        title += f"\ntarget={human_bytes(target_bytes)}, evict-set={human_bytes(evict_bytes)}"
    if title_suffix:
        title += f"\n{title_suffix}"
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
    ap.add_argument("summary_csvs", nargs="+", help="one or more miss_latency summary CSVs "
                     "(single target/eviction-set transition)")
    ap.add_argument("-o", "--out-dir", required=True, help="output directory for plots")
    ap.add_argument("--machine", default="", help="machine name for plot titles")
    ap.add_argument("--transition", default="", help="transition label for plot titles "
                     "(e.g. L1_to_LLC)")
    ap.add_argument("--title-suffix", default="", help="extra text appended to plot titles")
    ap.add_argument("--hit-latency-summary", nargs="*", default=None,
                     help="optional hit_latency summary CSV(s) for the SOURCE level, used "
                          "to annotate the incremental miss penalty (dependent-mode median "
                          "at --hit-latency-pattern is subtracted from this transition's "
                          "median)")
    ap.add_argument("--hit-latency-pattern", default="random",
                     help="which pattern's dependent-mode median to read from "
                          "--hit-latency-summary (default: random)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    by_pattern, target_bytes, evict_bytes = load_summaries(args.summary_csvs)
    if not by_pattern:
        print("No data loaded.", file=sys.stderr)
        return 1

    hit_latency_median = load_hit_latency_median(args.hit_latency_summary,
                                                  args.hit_latency_pattern)
    if args.hit_latency_summary and hit_latency_median is None:
        print("WARNING: --hit-latency-summary given but no matching dependent-mode row "
              "found; plotting without the incremental-penalty annotation.", file=sys.stderr)

    plot_boxplots(by_pattern, args.machine, args.transition, target_bytes, evict_bytes,
                  os.path.join(args.out_dir, "miss_latency_boxplots"), args.title_suffix,
                  hit_latency_median)
    return 0


if __name__ == "__main__":
    sys.exit(main())
