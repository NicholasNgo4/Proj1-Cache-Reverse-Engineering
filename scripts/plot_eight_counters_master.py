#!/usr/bin/env python3
"""Problem 8.4, items 2-3: consolidate every machine's eight_counters/
summaries into one cross-machine table, normalize the raw counts, and plot
ranked (S-curve) summaries instead of one page of plots per machine.

Reads each machine's data_processed/<machine>/eight_counters/<benchmark>/
eight_counters_summary_*.csv (glob picks the latest timestamp if more than
one exists), takes the "median" row (median of base+2 repeats, same
convention as the rest of this project's Phase II pipeline), and writes:

  data_processed/master/eight_counters/eight_counters_master.csv
  data_processed/master/eight_counters/plots/latency_scurve.{png,pdf}
  data_processed/master/eight_counters/plots/dtlb_miss_scurve.{png,pdf}

Normalization (item 2): dtlb_load_misses is reported per 1,000 accesses
(raw count / samples_achieved * 1000); samples_achieved is fixed at
1,000,000 for every run in this pipeline (run_standardized_benchmarks.sh's
own SAMPLES constant), so dividing by 1000 is equivalent and avoids
depending on the (blank-on-median-rows) samples_achieved column. Miss
rates (cache/L1/LLC) are already self-normalized ratios (misses/references)
from summarize_eight_counters.py, so no further normalization is applied
to those.

Latency uses ns_per_access_perf (perf's own duration_time / samples_achieved,
already in real nanoseconds) rather than bench_avg_ticks_per_access_median,
because raw tick counts are NOT directly comparable across machines with
different counter frequencies (Thunderbird's 25 MHz CNTVCT_EL0 vs. every
x86 machine's multi-GHz TSC -- see CAPACITY_RESULTS.md's units caveat).
ns_per_access_perf carries its own known caveat (it is a whole-process-
lifetime number, so it is inflated by warmup/permutation-construction
overhead, most visible at the small L1_resident footprint -- see any
machine's PHASE2_VALIDATION_TABLE.md) -- used anyway here because it is
the only field in this dataset that is already unit-comparable across all
8 machines without a separate per-machine frequency calibration step.
"""
import csv
import glob
import os

MACHINES = [
    # name, vendor, microarch, year
    ("sunbird", "Intel", "Haswell", 2014),
    ("thunderbird", "Ampere/ARM", "Neoverse N1", 2020),
    ("skylark", "AMD", "Zen 2", 2019),
    ("artemisia", "Intel", "Sapphire Rapids", 2023),
    ("charnwood", "Intel", "Sky Lake", 2015),
    ("crux", "Intel", "Coffee Lake", 2019),
    ("ookay", "Intel", "Kaby Lake", 2017),
    ("upgrade", "Intel", "Coffee Lake", 2017),
]
BENCHMARKS = ["L1_resident", "LLC_random", "beyond_LLC"]
VENDOR_COLOR = {"Intel": "#4C72B0", "AMD": "#C44E52", "Ampere/ARM": "#55A868"}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "data_processed", "master", "eight_counters")
PLOT_DIR = os.path.join(OUT_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)


def latest_summary(machine, benchmark):
    pattern = os.path.join(
        REPO_ROOT, "data_processed", machine, "eight_counters", benchmark,
        "eight_counters_summary_*.csv")
    matches = sorted(glob.glob(pattern))
    if not matches:
        return None
    return matches[-1]


def read_median_row(path):
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["run_tag"] == "median":
                return row
    return None


def to_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def main():
    records = []  # one dict per (machine, benchmark)
    for machine, vendor, uarch, year in MACHINES:
        for benchmark in BENCHMARKS:
            path = latest_summary(machine, benchmark)
            if path is None:
                print(f"WARNING: no summary for {machine}/{benchmark}, skipping")
                continue
            row = read_median_row(path)
            if row is None:
                print(f"WARNING: no median row in {path}, skipping")
                continue
            ns_per_access = to_float(row["ns_per_access_perf"])
            cache_miss_rate = to_float(row["cache_miss_rate"])
            l1_miss_rate = to_float(row["l1_miss_rate"])
            llc_miss_rate = to_float(row["llc_miss_rate"])
            dtlb_misses = to_float(row["dtlb_load_misses"])
            dtlb_per_1000 = (dtlb_misses / 1000.0) if dtlb_misses is not None else None
            records.append({
                "machine": machine, "vendor": vendor, "microarch": uarch, "year": year,
                "benchmark": benchmark,
                "ns_per_access_perf": ns_per_access,
                "cache_miss_rate_pct": cache_miss_rate * 100 if cache_miss_rate is not None else None,
                "l1_miss_rate_pct": l1_miss_rate * 100 if l1_miss_rate is not None else None,
                "llc_miss_rate_pct": llc_miss_rate * 100 if llc_miss_rate is not None else None,
                "dtlb_misses_per_1000_accesses": dtlb_per_1000,
            })

    # write consolidated CSV
    master_csv = os.path.join(OUT_DIR, "eight_counters_master.csv")
    fieldnames = ["machine", "vendor", "microarch", "year", "benchmark",
                  "ns_per_access_perf", "cache_miss_rate_pct", "l1_miss_rate_pct",
                  "llc_miss_rate_pct", "dtlb_misses_per_1000_accesses"]
    with open(master_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow(r)
    print(f"Wrote {master_csv}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def scurve_panel(ax, bench, field, ylabel, log=False):
        rows = [r for r in records if r["benchmark"] == bench and r[field] is not None]
        rows.sort(key=lambda r: r[field])
        names = [r["machine"] for r in rows]
        vals = [r[field] for r in rows]
        colors = [VENDOR_COLOR[r["vendor"]] for r in rows]
        ax.bar(range(len(rows)), vals, color=colors)
        ax.set_xticks(range(len(rows)))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
        ax.set_title(bench, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=9)
        if log:
            ax.set_yscale("log")
        ax.grid(axis="y", alpha=0.3)

    # Figure 1: latency S-curve, one panel per benchmark
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, bench in zip(axes, BENCHMARKS):
        scurve_panel(ax, bench, "ns_per_access_perf", "ns / access (perf)", log=True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in VENDOR_COLOR.values()]
    fig.legend(handles, VENDOR_COLOR.keys(), loc="upper center", ncol=3,
               bbox_to_anchor=(0.5, 1.06), frameon=False)
    fig.suptitle("")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "latency_scurve.png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(PLOT_DIR, "latency_scurve.pdf"), bbox_inches="tight")
    plt.close(fig)

    # Figure 2: dTLB miss S-curve, one panel per benchmark
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, bench in zip(axes, BENCHMARKS):
        scurve_panel(ax, bench, "dtlb_misses_per_1000_accesses",
                     "dTLB misses / 1000 accesses", log=True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in VENDOR_COLOR.values()]
    fig.legend(handles, VENDOR_COLOR.keys(), loc="upper center", ncol=3,
               bbox_to_anchor=(0.5, 1.06), frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "dtlb_miss_scurve.png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(PLOT_DIR, "dtlb_miss_scurve.pdf"), bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote {PLOT_DIR}/latency_scurve.{{png,pdf}}")
    print(f"Wrote {PLOT_DIR}/dtlb_miss_scurve.{{png,pdf}}")


if __name__ == "__main__":
    main()
