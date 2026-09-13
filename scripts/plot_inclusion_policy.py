#!/usr/bin/env python3
"""Plot the required cross-level eviction/reload evidence for
inclusion/exclusion behavior (PROJECT 1.pdf item 7) from one or more
processed summary CSVs (output of summarize_raw.py on --experiment
inclusion_policy raw data for a SINGLE target/eviction pairing).

Produces inclusion_policy_boxplots.{pdf,png}: one box per (channel,
pattern) -- target x {random,sequential} and control x {random,sequential}
-- drawn from the summary's own percentile columns, with two horizontal
reference lines showing this machine's calibrated "survived" (upper-level
hit) and "invalidated" (beyond-lower-level) hit_latency classes. Where the
boxes land relative to those two lines IS the required evidence: target
near the survived line = evidence of exclusive/non-inclusive behavior;
target near the invalidated line = evidence of inclusive behavior; control
should sit near the survived line regardless (it is never touched by the
eviction walk by construction -- see inclusion_policy.h) -- if it doesn't,
that is evidence the result is confounded, not evidence about policy (see
scripts/classify_inclusion_policy.py, which makes this call quantitatively
from the raw per-trial data; this plot is the visual companion).

Multiple summary CSVs (e.g. a base run plus reproducibility repeats) can be
passed together; rows are merged and deduplicated by (channel, pattern)
before plotting, so overlapping points are averaged rather than letting the
last file silently win (mirrors plot_associativity.py's
combine_duplicate_rows()).

Usage:
    python3 scripts/plot_inclusion_policy.py \\
        data_processed/sunbird/inclusion_policy/L1_vs_LLC/*_target_summary_*.csv \\
        data_processed/sunbird/inclusion_policy/L1_vs_LLC/*_control_summary_*.csv \\
        -o data_processed/sunbird/inclusion_policy/L1_vs_LLC/plots --machine sunbird \\
        --label L1_vs_LLC --survived-ticks 10.35 --invalidated-ticks 207.10
"""
import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REQUIRED_COLS = {"channel", "pattern", "median", "q1", "q3", "p5", "p95", "n_outliers", "n"}


def combine_duplicate_rows(key, rows):
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
    raw = {}
    for path in paths:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not REQUIRED_COLS.issubset(reader.fieldnames):
                missing = REQUIRED_COLS - set(reader.fieldnames or [])
                raise ValueError(f"{path}: missing expected column(s) {missing} -- is this an "
                                 f"inclusion_policy summary from summarize_raw.py (run with "
                                 f"--value-column ticks --trial-column trial_index)?")
            for row in reader:
                key = (row["channel"], row["pattern"])
                raw.setdefault(key, []).append(row)
    return {key: combine_duplicate_rows(key, rows) for key, rows in raw.items()}


def style_axes(ax):
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(1.2)
        ax.spines[side].set_color("black")
    ax.tick_params(width=1.1, labelsize=11)


def plot_boxplots(by_key, machine, label, out_prefix, title_suffix, survived_ticks, invalidated_ticks):
    order = [("target", "random"), ("target", "sequential"),
             ("control", "random"), ("control", "sequential")]
    picks = [k for k in order if k in by_key]
    if not picks:
        print("No data loaded; skipping box plots.", file=sys.stderr)
        return

    stats, labels, annotations = [], [], []
    for key in picks:
        row = by_key[key]
        stats.append({
            "med": float(row["median"]), "q1": float(row["q1"]), "q3": float(row["q3"]),
            "whislo": float(row["p5"]), "whishi": float(row["p95"]), "fliers": [],
        })
        labels.append(f"{key[0]}\n({key[1]})")
        n_outliers = int(float(row["n_outliers"]))
        n_runs = int(row.get("n_runs", 1))
        n_total = int(row.get("n_total", int(float(row.get("n", 0)))))
        lines = [f"n_outliers={n_outliers}"]
        if n_runs > 1:
            lines.append(f"{n_runs} runs, {int(row['run_spread_pct'])}% spread")
        else:
            lines.append(f"{n_total:,} trials")
        annotations.append(lines)

    fig, ax = plt.subplots(figsize=(max(7.5, 1.6 * len(stats)), 6.2))
    bp = ax.bxp(stats, showfliers=False, patch_artist=True)
    for i, box in enumerate(bp["boxes"]):
        color = "0.85" if picks[i][0] == "target" else "0.65"
        box.set(facecolor=color, edgecolor="black", linewidth=1.2)
    for element in ("whiskers", "caps", "medians"):
        for line in bp[element]:
            line.set(color="black", linewidth=1.2)

    if survived_ticks is not None:
        ax.axhline(survived_ticks, color="steelblue", linestyle="--", linewidth=1.4,
                   label=f"survived class (upper-level hit) = {survived_ticks:.1f} ticks")
    if invalidated_ticks is not None:
        ax.axhline(invalidated_ticks, color="firebrick", linestyle="--", linewidth=1.4,
                   label=f"invalidated class (beyond lower level) = {invalidated_ticks:.1f} ticks")
    if survived_ticks is not None or invalidated_ticks is not None:
        ax.legend(frameon=False, fontsize=9, loc="upper left")

    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Reload latency (timer ticks, single dependent access)")
    title = f"{machine}: inclusion/exclusion evidence"
    if label:
        title += f", {label}"
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=11)
    style_axes(ax)

    ymax_candidates = [s["whishi"] for s in stats]
    if invalidated_ticks is not None:
        ymax_candidates.append(invalidated_ticks)
    ymax = max(ymax_candidates)
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
    ap.add_argument("summary_csvs", nargs="+",
                     help="inclusion_policy summary CSVs (both target and control channel "
                          "summaries together -- single target/eviction pairing)")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("--machine", default="")
    ap.add_argument("--label", default="", help="e.g. L1_vs_LLC")
    ap.add_argument("--title-suffix", default="")
    ap.add_argument("--survived-ticks", type=float, default=None,
                     help="this machine's calibrated upper-level hit_latency median")
    ap.add_argument("--invalidated-ticks", type=float, default=None,
                     help="this machine's calibrated beyond-lower-level hit_latency median")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    by_key = load_summaries(args.summary_csvs)
    if not by_key:
        print("No data loaded.", file=sys.stderr)
        return 1

    plot_boxplots(by_key, args.machine, args.label,
                  os.path.join(args.out_dir, "inclusion_policy_boxplots"), args.title_suffix,
                  args.survived_ticks, args.invalidated_ticks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
