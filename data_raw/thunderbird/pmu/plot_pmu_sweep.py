#!/usr/bin/env python3
"""Plot Thunderbird's Phase-II PMU miss-rate sweep against the Phase-I timing
boundaries, for the pmu/ section of data_raw/thunderbird/README.md.

Usage: python3 plot_pmu_sweep.py <pmu_summary.csv> -o <out_dir>
"""
import csv
import sys
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument("summary_csv")
p.add_argument("-o", "--out-dir", required=True)
args = p.parse_args()

rows = list(csv.DictReader(open(args.summary_csv)))
sizes = [int(r["size_bytes"]) for r in rows]
l1 = [float(r["l1d_miss_pct"]) for r in rows]
l2 = [float(r["l2d_miss_pct"]) for r in rows]
l3 = [float(r["l3d_miss_pct"]) for r in rows]

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(sizes, l1, "o-", label="L1D miss % (armv8_pmuv3 l1d_cache_refill/l1d_cache)")
ax.plot(sizes, l2, "s-", label="L2D miss % (l2d_cache_refill/l2d_cache)")
ax.plot(sizes, l3, "^-", label="L3D miss % (l3d_cache_refill/l3d_cache)")
ax.set_xscale("log", base=2)
ax.set_xlabel("Working-set size (bytes)")
ax.set_ylabel("Miss rate (%)")
ax.set_title("Thunderbird — PMU miss-rate sweep vs. working-set size (Phase II)")
ax.axvline(65536, color="gray", linestyle=":", linewidth=1)
ax.text(65536, ax.get_ylim()[1]*0.9, " 64 KiB (Phase I L1 edge)", fontsize=8, rotation=90, va="top")
ax.axvline(1048576, color="gray", linestyle=":", linewidth=1)
ax.text(1048576, ax.get_ylim()[1]*0.9, " 1 MiB (L2 ref. capacity)", fontsize=8, rotation=90, va="top")
ax.axvline(31457280, color="gray", linestyle=":", linewidth=1)
ax.text(31457280, ax.get_ylim()[1]*0.9, " ~30 MiB (Phase I LLC candidate)", fontsize=8, rotation=90, va="top")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(f"{args.out_dir}/pmu_miss_rate_sweep.png", dpi=150)
fig.savefig(f"{args.out_dir}/pmu_miss_rate_sweep.pdf")
print(f"Wrote {args.out_dir}/pmu_miss_rate_sweep.{{png,pdf}}")
