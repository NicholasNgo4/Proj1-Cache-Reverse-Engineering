#!/usr/bin/env python3
"""Plot the required hit-latency evidence from one or more processed summary
CSVs (output of summarize_raw.py on --experiment hit_latency raw data for a
SINGLE working-set footprint / cache level).

Produces one box-plot figure, hit_latency_boxplots.{pdf,png}, with one box
per (load_mode, pattern) combination -- dependent x {random, sequential} and
independent x {random, sequential} -- drawn from the summary's own
percentile columns (q1/median/q3/p5/p95). There is no swept x-axis here
(capacity/associativity's "curve" plot has no equivalent for a single fixed
footprint), so a box-plot comparison is the whole picture.

The dependent-mode box is the reported hit latency; the independent-mode box
is the REQUIRED diagnostic control and is annotated with whether it reads
faster than dependent, as it must (PROJECT 1.pdf item 5) -- if it doesn't,
that's flagged loudly rather than silently plotted.

Multiple summary CSVs (e.g. a base run plus reproducibility repeats) can be
passed together; rows are merged and deduplicated by (load_mode, pattern)
before plotting, so overlapping points are averaged rather than letting the
last file silently win (mirrors plot_associativity.py's
combine_duplicate_rows()).

Usage:
    python3 scripts/plot_hit_latency.py \\
        data_processed/sunbird/latency/hit/L1/base_*_summary_*.csv \\
        -o data_processed/sunbird/latency/hit/L1/plots --machine sunbird --level L1
"""
import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REQUIRED_COLS = {"footprint_bytes", "load_mode", "pattern", "median", "q1", "q3",
                  "p5", "p95", "n_outliers", "n"}


def combine_duplicate_rows(key, rows):
    """Combines multiple summary rows for the same (load_mode, pattern) key
    -- e.g. a base run plus repeats -- instead of silently keeping whichever
    file happened to load last. Medians are averaged; the whisker range is
    the union (min of p5s, max of p95s). Mirrors plot_associativity.py's
    function of the same name."""
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
        print(f"  note: {key} has {len(rows)} overlapping summary rows with medians "
              f"{[round(m, 1) for m in medians]} (spread {spread:.1f} ticks, "
              f"{spread_pct:.1f}%) -- averaging, widening whiskers to the union",
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
    """Returns {(load_mode, pattern): row_dict}, combining duplicate rows
    across input files, plus the footprint_bytes recorded in the data (for
    the plot title)."""
    raw = {}
    footprint_bytes = None
    for path in paths:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not REQUIRED_COLS.issubset(reader.fieldnames):
                missing = REQUIRED_COLS - set(reader.fieldnames or [])
                raise ValueError(f"{path}: missing expected column(s) {missing} -- is "
                                 f"this a hit_latency summary from summarize_raw.py?")
            for row in reader:
                key = (row["load_mode"], row["pattern"])
                raw.setdefault(key, []).append(row)
                if footprint_bytes is None and "footprint_bytes" in row:
                    try:
                        footprint_bytes = int(float(row["footprint_bytes"]))
                    except ValueError:
                        pass

    return {key: combine_duplicate_rows(key, rows) for key, rows in raw.items()}, footprint_bytes


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


def plot_boxplots(by_key, machine, level, footprint_bytes, out_prefix, title_suffix):
    order = [("dependent", "random"), ("dependent", "sequential"),
             ("independent", "random"), ("independent", "sequential")]
    picks = [k for k in order if k in by_key]
    if not picks:
        print("No data loaded; skipping box plots.", file=sys.stderr)
        return

    stats = []
    labels = []
    annotations = []
    for key in picks:
        row = by_key[key]
        stats.append({
            "med": float(row["median"]),
            "q1": float(row["q1"]),
            "q3": float(row["q3"]),
            "whislo": float(row["p5"]),
            "whishi": float(row["p95"]),
            "fliers": [],
        })
        labels.append(f"{key[0]}\n({key[1]})")

        n_outliers = int(float(row["n_outliers"]))
        n_runs = int(row.get("n_runs", 1))
        n_total = int(row.get("n_total", int(float(row.get("n", 0)))))
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

    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Latency (timer ticks / access)")
    title = f"{machine}: hit-latency box plots"
    if level:
        title += f", {level}"
    if footprint_bytes:
        title += f" (footprint={human_bytes(footprint_bytes)})"
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=11)
    style_axes(ax)

    # The required MLP-exposing check: independent must read faster than
    # dependent at the same pattern, or the independent-load construction
    # (or the dependent number) is suspect.
    for pattern in ("random", "sequential"):
        dep = by_key.get(("dependent", pattern))
        ind = by_key.get(("independent", pattern))
        if dep and ind:
            dep_med, ind_med = float(dep["median"]), float(ind["median"])
            ok = ind_med < dep_med
            msg = (f"{pattern}: independent {'<' if ok else '>='} dependent "
                   f"({ind_med:.2f} vs {dep_med:.2f} ticks) "
                   f"{'[expected]' if ok else '[UNEXPECTED -- investigate]'}")
            print(msg, file=sys.stderr)

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
    ap.add_argument("summary_csvs", nargs="+", help="one or more hit_latency summary CSVs "
                     "(single working-set footprint / cache level)")
    ap.add_argument("-o", "--out-dir", required=True, help="output directory for plots")
    ap.add_argument("--machine", default="", help="machine name for plot titles")
    ap.add_argument("--level", default="", help="cache level label for plot titles (e.g. L1)")
    ap.add_argument("--title-suffix", default="", help="extra text appended to plot titles")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    by_key, footprint_bytes = load_summaries(args.summary_csvs)
    if not by_key:
        print("No data loaded.", file=sys.stderr)
        return 1

    plot_boxplots(by_key, args.machine, args.level, footprint_bytes,
                  os.path.join(args.out_dir, "hit_latency_boxplots"), args.title_suffix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
