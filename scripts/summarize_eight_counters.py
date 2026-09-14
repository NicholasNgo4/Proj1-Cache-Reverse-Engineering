#!/usr/bin/env python3
"""Parse run_standardized_benchmarks.sh's raw `perf stat -x,` CSV output (one
file per (group, run_tag) at a fixed standardized benchmark) into one
combined summary row per run_tag, plus a median-of-repeats row.

Sibling of scripts/summarize_pmu.py -- reuses its perf-CSV and bench-CSV
parsing helpers directly (same file formats, same cache_bench CSV shape),
differing only in the group/event set: this pipeline's 4th perf group is
`tlb` (L1-dcache-stores, dTLB-load-misses) instead of summarize_pmu.py's
`cyc` (cycles, instructions) -- see run_standardized_benchmarks.sh's header
for why (problem 8.4's fixed 8-counter set, not Phase II's).

Each input file is named `<BENCHMARK>_perfstat_<group>_<run_tag>_<ts>.csv`
where group is one of cache/l1/llc/tlb (see run_standardized_benchmarks.sh's
GROUP_NAMES).

Usage:
    python3 scripts/summarize_eight_counters.py --benchmark L1_resident \\
        data_raw/<machine>/eight_counters/L1_resident/L1_resident_perfstat_*_base_<ts>.csv ... \\
        -o data_processed/<machine>/eight_counters/L1_resident/eight_counters_summary_<ts>.csv
"""
import argparse
import csv
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summarize_pmu import parse_perf_csv, parse_bench_header  # noqa: E402

FILENAME_RE = re.compile(r"^(?P<benchmark>.+)_perfstat_(?P<group>cache|l1|llc|tlb)_(?P<run_tag>base|rep\d+)_(?P<ts>[^_]+)\.csv$")


def bench_path_for(perf_path):
    return perf_path.replace("_perfstat_", "_bench_")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("perf_csvs", nargs="+")
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    # run_tag -> group -> {event: (value, not_counted)}
    by_run = {}
    # run_tag -> samples_achieved, list of bench ticks (concatenated across groups; all should agree since same config)
    bench_by_run = {}

    for path in args.perf_csvs:
        base = os.path.basename(path)
        m = FILENAME_RE.match(base)
        if not m or m.group("benchmark") != args.benchmark:
            print(f"WARNING: skipping unrecognized filename {base}", file=sys.stderr)
            continue
        run_tag = m.group("run_tag")
        group = m.group("group")
        events = parse_perf_csv(path)
        by_run.setdefault(run_tag, {})[group] = events

        bpath = bench_path_for(path)
        if os.path.exists(bpath):
            samples_achieved, ticks = parse_bench_header(bpath)
            entry = bench_by_run.setdefault(run_tag, {"samples_achieved": None, "ticks": []})
            if samples_achieved is not None:
                entry["samples_achieved"] = samples_achieved
            entry["ticks"].extend(ticks)

    def get(events_by_group, group, event_name):
        val, not_counted = events_by_group.get(group, {}).get(event_name, (None, True))
        return val, not_counted

    fieldnames = [
        "benchmark", "run_tag", "samples_achieved",
        "duration_time_ns", "ns_per_access_perf",
        "bench_avg_ticks_per_access_median",
        "cache_references", "cache_misses", "cache_miss_rate",
        "l1_dcache_loads", "l1_dcache_load_misses", "l1_miss_rate",
        "l1_dcache_stores",
        "llc_loads", "llc_load_misses", "llc_miss_rate",
        "dtlb_load_misses",
        "notes",
    ]

    rows = []
    for run_tag in ("base", "rep1", "rep2"):
        if run_tag not in by_run:
            continue
        groups = by_run[run_tag]
        notes = []

        # duration_time is recorded in every group's file; take the cache
        # group's copy (all four should closely agree -- same command/seed).
        duration_ns = None
        for g in ("cache", "l1", "llc", "tlb"):
            val, not_counted = get(groups, g, "duration_time")
            if val is not None:
                duration_ns = val
                break
        samples_achieved = bench_by_run.get(run_tag, {}).get("samples_achieved")
        ticks_list = bench_by_run.get(run_tag, {}).get("ticks", [])
        bench_median = statistics.median(ticks_list) if ticks_list else None

        ns_per_access = (duration_ns / samples_achieved) if (duration_ns and samples_achieved) else None

        cache_refs, cr_nc = get(groups, "cache", "cache-references")
        cache_miss, cm_nc = get(groups, "cache", "cache-misses")
        cache_miss_rate = (cache_miss / cache_refs) if (cache_refs and not cr_nc and not cm_nc) else None
        if cr_nc or cm_nc:
            notes.append("cache-references/misses <not counted>")

        l1_loads, l1l_nc = get(groups, "l1", "L1-dcache-loads")
        l1_misses, l1m_nc = get(groups, "l1", "L1-dcache-load-misses")
        l1_miss_rate = (l1_misses / l1_loads) if (l1_loads and not l1l_nc and not l1m_nc) else None
        if l1l_nc or l1m_nc:
            notes.append("L1-dcache-loads/misses <not counted>")

        llc_loads, llcl_nc = get(groups, "llc", "LLC-loads")
        llc_misses, llcm_nc = get(groups, "llc", "LLC-load-misses")
        llc_miss_rate = (llc_misses / llc_loads) if (llc_loads and not llcl_nc and not llcm_nc) else None
        if llcl_nc or llcm_nc:
            notes.append("LLC-loads/misses <not counted> (real PMU limitation -- see script docstring)")

        l1_stores, l1s_nc = get(groups, "tlb", "L1-dcache-stores")
        dtlb_misses, dtlb_nc = get(groups, "tlb", "dTLB-load-misses")
        if l1s_nc or dtlb_nc:
            notes.append("L1-dcache-stores/dTLB-load-misses <not counted>")

        rows.append({
            "benchmark": args.benchmark,
            "run_tag": run_tag,
            "samples_achieved": samples_achieved,
            "duration_time_ns": duration_ns,
            "ns_per_access_perf": ns_per_access,
            "bench_avg_ticks_per_access_median": bench_median,
            "cache_references": cache_refs,
            "cache_misses": cache_miss,
            "cache_miss_rate": cache_miss_rate,
            "l1_dcache_loads": l1_loads,
            "l1_dcache_load_misses": l1_misses,
            "l1_miss_rate": l1_miss_rate,
            "l1_dcache_stores": l1_stores,
            "llc_loads": llc_loads,
            "llc_load_misses": llc_misses,
            "llc_miss_rate": llc_miss_rate,
            "dtlb_load_misses": dtlb_misses,
            "notes": "; ".join(notes),
        })

    # median-across-run_tags row, for the numeric columns only
    numeric_cols = [c for c in fieldnames if c not in ("benchmark", "run_tag", "samples_achieved", "notes")]
    median_row = {"benchmark": args.benchmark, "run_tag": "median", "samples_achieved": "", "notes": ""}
    for c in numeric_cols:
        vals = [r[c] for r in rows if r[c] is not None]
        median_row[c] = statistics.median(vals) if vals else None
    rows.append(median_row)

    with open(args.output, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} rows (incl. median) to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
