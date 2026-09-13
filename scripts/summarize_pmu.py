#!/usr/bin/env python3
"""Parse run_pmu_verification.sh's raw `perf stat -x,` CSV output (one file per
(group, run_tag) at a fixed cache level/footprint) into one combined summary
row per run_tag, plus a median-of-repeats row.

Each input file is named `<LEVEL>_perfstat_<group>_<run_tag>_<ts>.csv` where
group is one of cache/l1/llc/cyc (see run_pmu_verification.sh's GROUP_NAMES).
`perf stat -x,` rows look like:

    <value>,<unit>,<event_name>,<time_running_ns>,<pct_running>[,<ratio>,<ratio_desc>]

`<not counted>` in the value column means the event never got scheduled on a
hardware counter during the run (real PMU contention, not a parsing bug) --
recorded as an explicit "not_counted" flag per metric rather than silently
dropped or treated as zero.

Also reads the matching `<LEVEL>_bench_<group>_<run_tag>_<ts>.csv` (same run,
cache_bench's own RDTSC-based output) for samples_achieved (from its `#
...samples_achieved=N...` header comment) and its own avg_ticks_per_access,
so the summary carries both the independent perf-stat-derived latency AND the
Phase-I-style timer's own number from the exact same invocation, side by side.

Usage:
    python3 scripts/summarize_pmu.py --level L1 \\
        data_raw/<machine>/pmu/L1/L1_perfstat_*_base_<ts>.csv ... \\
        -o data_processed/<machine>/pmu/L1/pmu_summary_<ts>.csv
"""
import argparse
import csv
import os
import re
import statistics
import sys

FILENAME_RE = re.compile(r"^(?P<level>.+)_perfstat_(?P<group>cache|l1|llc|cyc)_(?P<run_tag>base|rep\d+)_(?P<ts>[^_]+)\.csv$")


def parse_perf_csv(path):
    """Return {event_name: (value_or_None, not_counted_bool)}."""
    events = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or len(row) < 3:
                continue
            value_str, _unit, event_name = row[0], row[1], row[2]
            event_name = event_name.split(":")[0]  # strip perf's ":u" user-space suffix
            if value_str == "<not counted>":
                events[event_name] = (None, True)
            else:
                try:
                    events[event_name] = (float(value_str), False)
                except ValueError:
                    events[event_name] = (None, True)
    return events


def parse_bench_header(path):
    """Pull samples_achieved and the (only) avg_ticks_per_access data row's
    values out of a cache_bench hit_latency CSV. Returns
    (samples_achieved, [avg_ticks_per_access, ...]) -- a list since the CSV
    has one row per batch."""
    samples_achieved = None
    ticks = []
    with open(path, newline="") as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("#"):
            m = re.search(r"samples_achieved=(\d+)", line)
            if m:
                samples_achieved = int(m.group(1))
    data_lines = [l for l in lines if not l.startswith("#") and l.strip()]
    if data_lines:
        reader = csv.DictReader(data_lines)
        for row in reader:
            try:
                ticks.append(float(row["avg_ticks_per_access"]))
            except (KeyError, ValueError):
                pass
    return samples_achieved, ticks


def bench_path_for(perf_path):
    return perf_path.replace("_perfstat_", "_bench_")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("perf_csvs", nargs="+")
    ap.add_argument("--level", required=True)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    # run_tag -> group -> {event: (value, not_counted)}
    by_run = {}
    # run_tag -> samples_achieved, list of bench ticks (concatenated across groups; all should agree since same config)
    bench_by_run = {}

    for path in args.perf_csvs:
        base = os.path.basename(path)
        m = FILENAME_RE.match(base)
        if not m or m.group("level") != args.level:
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
        "level", "run_tag", "samples_achieved",
        "duration_time_ns", "ns_per_access_perf",
        "bench_avg_ticks_per_access_median",
        "cache_references", "cache_misses", "cache_miss_rate",
        "l1_dcache_loads", "l1_dcache_load_misses", "l1_miss_rate",
        "llc_loads", "llc_load_misses", "llc_miss_rate",
        "cycles", "instructions", "cycles_per_access", "ipc",
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
        for g in ("cache", "l1", "llc", "cyc"):
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

        cycles, cyc_nc = get(groups, "cyc", "cycles")
        instructions, ins_nc = get(groups, "cyc", "instructions")
        cycles_per_access = (cycles / samples_achieved) if (cycles and samples_achieved and not cyc_nc) else None
        ipc = (instructions / cycles) if (instructions and cycles and not cyc_nc and not ins_nc) else None
        if cyc_nc or ins_nc:
            notes.append("cycles/instructions <not counted>")

        rows.append({
            "level": args.level,
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
            "llc_loads": llc_loads,
            "llc_load_misses": llc_misses,
            "llc_miss_rate": llc_miss_rate,
            "cycles": cycles,
            "instructions": instructions,
            "cycles_per_access": cycles_per_access,
            "ipc": ipc,
            "notes": "; ".join(notes),
        })

    # median-across-run_tags row, for the numeric columns only
    numeric_cols = [c for c in fieldnames if c not in ("level", "run_tag", "samples_achieved", "notes")]
    median_row = {"level": args.level, "run_tag": "median", "samples_achieved": "", "notes": ""}
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
