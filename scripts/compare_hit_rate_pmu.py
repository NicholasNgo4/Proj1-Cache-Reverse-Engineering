#!/usr/bin/env python3
"""Problem 8.5 part 4: compares the software-only Hhat (main_code/
software_hit_rate/, no PMU access) against a PMU-derived ground-truth hit
rate H_pmu = 1 - cache-misses/cache-references.

REDESIGNED 2026-09-14: Hhat and H_pmu no longer come from the same
invocation. An earlier design perf-wrapped `cache_bench --experiment
hit_rate` directly to get both numbers from identical timed accesses, but
that was found to be invalid on Sunbird -- `perf stat` reproducibly and
severely distorts hit_rate's own single-shot per-access timing (wall time
for a sub-millisecond workload inflated to 1.7-2.9s under perf, flipping
Hhat from ~1.0 to as low as 0.0 for the identical seed/footprint; see
run_hit_rate_pmu_validation.sh's header comment for the full writeup).
Hhat's bench_csv now comes from an UNWRAPPED hit_rate run; H_pmu's perf_csv
now comes from a SEPARATE perf-wrapped `--experiment hit_latency` run
(batched timing, already validated clean by run_pmu_verification.sh) at the
same footprint/seed -- decoupled sources, not identical timed accesses, but
each individually trustworthy where the original combined approach was not.

cache-references/cache-misses is an LLC-scope event pair on this project's
machines (confirmed in scripts/run_pmu_verification.sh's own usage) -- this
is exactly the "served by any cache level vs. served by DRAM" boundary
software_hit_rate.h's "hit" definition is designed to match, so H_pmu is a
direct, no-guesswork comparison target, not an approximation.

Reads run_hit_rate_pmu_validation.sh's own positional arguments
(<level>:<footprint>:<perf_csv>:<bench_csv>, one per run_tag) rather than
re-discovering files by globbing, so it works from a single invocation of
that script without needing a separate file-naming convention. Note
<footprint> here is the ACTUAL tested footprint (already halved for
L1/L2/LLC by run_hit_rate_pmu_validation.sh), not the raw CAPACITY_RESULTS.md
value passed on its command line.

Usage:
    python3 scripts/compare_hit_rate_pmu.py \\
        L1:32768:data_raw/sunbird/.../L1_perfstat_base_<ts>.csv:data_raw/sunbird/.../L1_bench_base_<ts>.csv \\
        L1:32768:...rep1... L1:32768:...rep2... L2:262144:... \\
        -o data_processed/sunbird/software_hit_rate/pmu_validation_<ts>.csv
"""
import argparse
import csv
import re
import statistics
import sys


def parse_perf_csv(path):
    """Returns {event_name: (value_or_None, not_counted_bool)}, same format
    as summarize_pmu.py's parser (kept independent/duplicated deliberately --
    this script has no other dependency on that module)."""
    events = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or len(row) < 3:
                continue
            value_str, _unit, event_name = row[0], row[1], row[2]
            event_name = event_name.split(":")[0]
            if value_str == "<not counted>":
                events[event_name] = (None, True)
            else:
                try:
                    events[event_name] = (float(value_str), False)
                except ValueError:
                    events[event_name] = (None, True)
    return events


def parse_bench_result(path):
    """Pulls the '# result ...' line's key=value fields out of a hit_rate
    bench CSV."""
    with open(path) as f:
        for line in f:
            if line.startswith("# result"):
                tokens = line.strip().split()[2:]  # drop "#" "result"
                return dict(t.split("=", 1) for t in tokens if "=" in t)
    raise ValueError(f"{path}: no '# result' line found")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", nargs="+",
                     help="<level>:<footprint_bytes>:<perf_csv>:<bench_csv> entries")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    per_run = []
    for spec in args.pairs:
        level, footprint, perf_path, bench_path = spec.split(":", 3)
        events = parse_perf_csv(perf_path)
        result = parse_bench_result(bench_path)

        refs, refs_nc = events.get("cache-references", (None, True))
        misses, misses_nc = events.get("cache-misses", (None, True))

        row = {
            "level": level,
            "footprint_bytes": footprint,
            "perf_csv": perf_path,
            "bench_csv": bench_path,
            "Hhat": result.get("Hhat"),
            "ci_lower": result.get("ci_lower"),
            "ci_upper": result.get("ci_upper"),
            "tau_ticks": result.get("tau_ticks"),
            "sensitivity": result.get("sensitivity"),
            "specificity": result.get("specificity"),
            "cache_references": refs,
            "cache_misses": misses,
            "not_counted": refs_nc or misses_nc,
            "H_pmu": None,
            "abs_error": None,
            "rel_error_pct": None,
        }
        if not row["not_counted"] and refs and refs > 0:
            h_pmu = 1.0 - (misses / refs)
            hhat = float(result["Hhat"])
            row["H_pmu"] = h_pmu
            row["abs_error"] = abs(hhat - h_pmu)
            row["rel_error_pct"] = (row["abs_error"] / h_pmu * 100.0) if h_pmu > 0 else None
        per_run.append(row)

    # Per-level summary: median H_pmu/Hhat/abs_error across base+repeats at
    # that level, same "median of reproducibility repeats" convention as
    # summarize_pmu.py.
    by_level = {}
    for r in per_run:
        by_level.setdefault(r["level"], []).append(r)

    summary_rows = []
    for level, rows in by_level.items():
        footprint = rows[0]["footprint_bytes"]
        valid = [r for r in rows if r["H_pmu"] is not None]
        if valid:
            med_hhat = statistics.median(float(r["Hhat"]) for r in valid)
            med_hpmu = statistics.median(r["H_pmu"] for r in valid)
            med_abs = statistics.median(r["abs_error"] for r in valid)
            rel_vals = [r["rel_error_pct"] for r in valid if r["rel_error_pct"] is not None]
            med_rel = statistics.median(rel_vals) if rel_vals else None
        else:
            med_hhat = med_hpmu = med_abs = med_rel = None
        summary_rows.append({
            "level": level,
            "footprint_bytes": footprint,
            "n_runs": len(rows),
            "n_valid": len(valid),
            "median_Hhat": med_hhat,
            "median_H_pmu": med_hpmu,
            "median_abs_error": med_abs,
            "median_rel_error_pct": med_rel,
        })

    run_fieldnames = list(per_run[0].keys())
    summary_only = ["n_runs", "n_valid", "median_Hhat", "median_H_pmu",
                     "median_abs_error", "median_rel_error_pct"]
    all_fieldnames = ["kind"] + run_fieldnames + [f for f in summary_only if f not in run_fieldnames]

    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_fieldnames, restval="")
        w.writeheader()
        for r in per_run:
            w.writerow({"kind": "run", **r})
        for r in summary_rows:
            w.writerow({"kind": "level_summary", **r})

    print(f"wrote {len(per_run)} run rows + {len(summary_rows)} level summaries -> {args.output}",
          file=sys.stderr)
    for r in summary_rows:
        print(f"  {r['level']} (footprint={r['footprint_bytes']}): "
              f"Hhat={r['median_Hhat']} H_pmu={r['median_H_pmu']} "
              f"abs_error={r['median_abs_error']} rel_error_pct={r['median_rel_error_pct']} "
              f"(n_valid={r['n_valid']}/{r['n_runs']})",
              file=sys.stderr)


if __name__ == "__main__":
    main()
