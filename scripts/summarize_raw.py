#!/usr/bin/env python3
"""Reduce a raw cache_bench CSV (one row per timed batch) to one summary row
per swept point, with the full distribution stats the homework requires:
n, mean, median, stddev, min, q1, q3, p5, p95, max, n_outliers.

cache_bench prints RAW data: every batch's average ticks/access, tagged by
the swept configuration (e.g. size_bytes,num_nodes for --experiment
capacity). This script groups rows by every column except the last two
(assumed to be <trial-index>,<measured-value>) and computes distribution
statistics over the measured-value column within each group. Output feeds
data_processed/<machine>/<experiment>/ and the box-plot / boundary-detection
scripts.

Usage:
    python3 scripts/summarize_raw.py data_raw/<machine>/capacity/capacity_*.csv \
        -o data_processed/<machine>/capacity/summary.csv
"""
import argparse
import csv
import statistics
import sys
from collections import defaultdict


def load_rows(path):
    with open(path, newline="") as f:
        lines = [line for line in f if not line.lstrip().startswith("#") and line.strip()]
    reader = csv.DictReader(lines)
    if reader.fieldnames is None or len(reader.fieldnames) < 2:
        raise ValueError(f"{path}: expected at least a trial-index and a value column")
    return list(reader), reader.fieldnames


def summarize_group(values):
    n = len(values)
    sorted_vals = sorted(values)
    mean = statistics.mean(values)
    median = statistics.median(sorted_vals)
    stddev = statistics.stdev(values) if n > 1 else 0.0
    q1 = _percentile(sorted_vals, 0.25)
    q3 = _percentile(sorted_vals, 0.75)
    p5 = _percentile(sorted_vals, 0.05)
    p95 = _percentile(sorted_vals, 0.95)
    iqr = q3 - q1
    lo_fence = q1 - 1.5 * iqr
    hi_fence = q3 + 1.5 * iqr
    n_outliers = sum(1 for v in values if v < lo_fence or v > hi_fence)
    return {
        "n": n,
        "mean": mean,
        "median": median,
        "stddev": stddev,
        "min": sorted_vals[0],
        "q1": q1,
        "q3": q3,
        "p5": p5,
        "p95": p95,
        "max": sorted_vals[-1],
        "n_outliers": n_outliers,
    }


def _percentile(sorted_vals, p):
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    idx = p * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw_csv")
    ap.add_argument("-o", "--output", required=True, help="processed summary CSV path")
    ap.add_argument("--value-column", default=None,
                     help="name of the measured-value column (default: last column)")
    ap.add_argument("--trial-column", default=None,
                     help="name of the trial/batch-index column to drop from the "
                          "group key (default: second-to-last column)")
    args = ap.parse_args()

    rows, fieldnames = load_rows(args.raw_csv)
    value_col = args.value_column or fieldnames[-1]
    trial_col = args.trial_column or fieldnames[-2]
    key_cols = [c for c in fieldnames if c not in (value_col, trial_col)]

    groups = defaultdict(list)
    for row in rows:
        key = tuple(row[c] for c in key_cols)
        groups[key].append(float(row[value_col]))

    stat_cols = ["n", "mean", "median", "stddev", "min", "q1", "q3", "p5", "p95",
                 "max", "n_outliers"]

    with open(args.output, "w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(key_cols + stat_cols)
        # Sort numerically on the first key column when possible (typically
        # size_bytes or stride_bytes) so downstream boundary detection sees
        # points in sweep order.
        def sort_key(k):
            try:
                return (0, float(k[0]))
            except (ValueError, IndexError):
                return (1, k)

        for key in sorted(groups.keys(), key=sort_key):
            s = summarize_group(groups[key])
            writer.writerow(list(key) + [s[c] for c in stat_cols])

    print(f"Wrote {len(groups)} summary rows to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
