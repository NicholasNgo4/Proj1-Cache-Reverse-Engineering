#!/usr/bin/env python3
"""Plots for Problem 8.5's software-only cache hit-rate estimator
(main_code/software_hit_rate/, --experiment hit_rate).

Two figures:

  1. calibration_distributions.{png,pdf} -- overlaid histograms of the
     "resident" (known-hit) and "nonresident" (known-miss) single-shot
     calibration tick distributions from ONE raw hit_rate output file, with
     the classification threshold tau marked -- the direct visual evidence
     for whether a fixed threshold is justified by the data (assignment
     parts 1-2).

  2. hit_rate_sweep.{png,pdf} -- Hhat (with its bootstrap [ci_lower,
     ci_upper] band) vs. test_bytes from a summarize_software_hit_rate.py
     summary CSV, log-x, with cache-level boundaries (passed explicitly, not
     read from FINAL_CACHE_TABLE.md automatically -- same explicit-only
     discipline as every other plot script here) drawn as vertical
     reference lines -- the hit-rate-vs-working-set-size sanity check.

Usage:
    python3 scripts/plot_software_hit_rate.py \\
        --summary data_raw/sunbird/software_hit_rate/hit_rate_sweep_<ts>.csv \\
        --calib-raw data_raw/sunbird/software_hit_rate/raw/hit_rate_536870912_<ts>.csv.gz \\
        --boundary L1:32768 --boundary L2:262144 --boundary LLC:31457280 --boundary DRAM:536870912 \\
        -o data_processed/sunbird/software_hit_rate/plots --machine sunbird
"""
import argparse
import csv
import gzip
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def open_maybe_gzip(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt")
    return open(path, "r")


def load_calib_ticks(raw_path):
    resident, nonresident = [], []
    tau = None
    with open_maybe_gzip(raw_path) as f:
        header_seen = False
        for line in f:
            if line.startswith("# result"):
                for tok in line.strip().split():
                    if tok.startswith("tau_ticks="):
                        tau = float(tok.split("=", 1)[1])
                continue
            if line.startswith("#"):
                continue
            if not header_seen:
                header_seen = True  # the "phase,index,ticks,classified_hit" header row
                continue
            phase, _idx, ticks, _hit = line.strip().split(",")
            if phase == "calib_resident":
                resident.append(float(ticks))
            elif phase == "calib_nonresident":
                nonresident.append(float(ticks))
    if tau is None:
        raise ValueError(f"{raw_path}: no '# result' line with tau_ticks found")
    return resident, nonresident, tau


def load_summary(summary_path):
    with open(summary_path, newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: int(r["test_bytes"]))
    return rows


def plot_calibration(resident, nonresident, tau, out_prefix, machine):
    fig, ax = plt.subplots(figsize=(8, 5))
    # Single-shot timing has a heavy right tail (rare interrupts/context
    # switches/page faults mid-measurement -- the same fixed-overhead-plus-
    # occasional-outlier behavior latency.h's run_miss_latency_experiment()
    # docstring already documents for this codebase). A handful of such
    # outliers can be 10-100x the bulk of either distribution, which would
    # otherwise compress the whole resident-vs-nonresident separation into a
    # few pixels at the left edge -- clip the DISPLAY range to just past the
    # 99.5th percentile of the combined data (never drops points from the
    # classifier/estimator itself, only from what's plotted) and annotate
    # how many points that excludes from view.
    combined = np.array(resident + nonresident)
    display_max = max(np.percentile(combined, 99.5), tau) * 1.15
    n_clipped = int(np.sum(combined > display_max))
    bins = 60
    ax.hist(resident, bins=bins, range=(0, display_max), alpha=0.6,
            label=f"resident (n={len(resident)})", color="#2a9d8f")
    ax.hist(nonresident, bins=bins, range=(0, display_max), alpha=0.6,
            label=f"nonresident (n={len(nonresident)})", color="#e76f51")
    ax.axvline(tau, color="black", linestyle="--", linewidth=1.5,
                label=f"tau = {tau:.1f} ticks")
    ax.set_xlabel("single-shot access latency (ticks)")
    ax.set_ylabel("count")
    title = "Calibration distributions: resident vs. nonresident"
    if machine:
        title += f" ({machine})"
    ax.set_title(title)
    if n_clipped:
        ax.text(0.98, 0.5, f"{n_clipped} outlier point(s) beyond\nx-axis range not shown\n"
                            f"(included in tau/Se/Sp computation)",
                transform=ax.transAxes, ha="right", va="center", fontsize=8, color="dimgray")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{out_prefix}.png", dpi=150)
    fig.savefig(f"{out_prefix}.pdf")
    plt.close(fig)
    print(f"wrote {out_prefix}.{{png,pdf}}", file=sys.stderr)


def plot_sweep(rows, boundaries, out_prefix, machine):
    xs = [int(r["test_bytes"]) for r in rows]
    hhat = [float(r["Hhat"]) for r in rows]
    lo = [float(r["ci_lower"]) for r in rows]
    hi = [float(r["ci_upper"]) for r in rows]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(xs, hhat, marker="o", color="#264653", label="Hhat (point estimate)")
    ax.fill_between(xs, lo, hi, color="#264653", alpha=0.2, label="bootstrap 95% CI")
    ax.set_xscale("log")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("test_bytes (working-set size, log scale)")
    ax.set_ylabel("Hhat (estimated hit rate)")
    title = "Software-only Hhat vs. working-set size"
    if machine:
        title += f" ({machine})"
    ax.set_title(title)

    for name, byte_val in boundaries:
        ax.axvline(byte_val, color="gray", linestyle=":", linewidth=1)
        ax.text(byte_val, 1.02, name, rotation=90, va="bottom", ha="right",
                fontsize=8, color="gray")

    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(f"{out_prefix}.png", dpi=150)
    fig.savefig(f"{out_prefix}.pdf")
    plt.close(fig)
    print(f"wrote {out_prefix}.{{png,pdf}}", file=sys.stderr)


def parse_boundary(spec):
    name, val = spec.split(":")
    return name, int(val)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", required=True, help="summarize_software_hit_rate.py output CSV")
    ap.add_argument("--calib-raw", required=True,
                     help="one raw hit_rate output file (.csv or .csv.gz) to source the "
                          "calibration histogram from")
    ap.add_argument("--boundary", action="append", default=[],
                     metavar="NAME:BYTES", help="cache-level boundary to annotate on the "
                     "sweep plot, e.g. --boundary L1:32768 (repeatable)")
    ap.add_argument("-o", "--output-dir", required=True)
    ap.add_argument("--machine", default="")
    args = ap.parse_args()

    import os
    os.makedirs(args.output_dir, exist_ok=True)

    resident, nonresident, tau = load_calib_ticks(args.calib_raw)
    plot_calibration(resident, nonresident, tau,
                      os.path.join(args.output_dir, "calibration_distributions"), args.machine)

    rows = load_summary(args.summary)
    boundaries = [parse_boundary(b) for b in args.boundary]
    plot_sweep(rows, boundaries, os.path.join(args.output_dir, "hit_rate_sweep"), args.machine)


if __name__ == "__main__":
    main()
