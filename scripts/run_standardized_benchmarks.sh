#!/bin/bash
#
# run_standardized_benchmarks.sh -- Problem 8.4 pipeline: the 3 standardized
# cross-machine microbenchmarks (L1-resident dependent accesses, LLC-sized
# randomized accesses, a working set larger than LLC), each wrapped in
# `perf stat` to collect 8 fixed performance-counter events, so every team
# machine can be ranked/compared on the SAME benchmarks and the SAME counter
# set (see CHRONOLOGICAL_MASTER_TABLE.md / CLAUDE.md's 8.4 section).
#
# This is NOT new benchmark code: all 3 "microbenchmarks" are the same
# `cache_bench --experiment hit_latency` dependent-chase, random-pattern,
# batched-timing construction already used throughout Phase I/II -- they
# differ only in --footprint-bytes. What's new here is (a) fixed,
# cross-machine-standardized benchmark NAMES instead of raw byte values, and
# (b) a different 8-event counter set than run_pmu_verification.sh's own.
#
# Why 4 separate 2-event perf groups instead of one 8-event command: this
# project's PMU-scheduling findings vary by machine (Sunbird/Thunderbird only
# reliably schedule 2 generic hardware counters at once; Crux/Artemisia/Upgrade
# can do 7-8 at once -- see CLAUDE.md's Phase II section) and no single
# assumption generalizes, so this script uses the same proven-safe 2-per-group
# split as run_pmu_verification.sh. 3 of the 4 groups below are byte-identical
# to that script's; only the 4th (store/TLB) group differs, since this
# pipeline's 8-counter set replaces run_pmu_verification.sh's cycles/
# instructions with L1-dcache-stores/dTLB-load-misses (see CLAUDE.md's 8.4
# section for why: per-access normalization doesn't need an instructions
# counter, and dTLB-load-misses gives real data toward this project's
# still-open DTLB-confound question from the associativity investigation).
# Software `duration_time` is always-on and doesn't consume a hardware
# counter, so every group also carries it, same as run_pmu_verification.sh.
#
# Only runnable AFTER Phase I is frozen/tagged (see README.md's Phase
# Discipline section, tag: phase1-timing-only) -- same discipline as
# run_pmu_verification.sh, since this also wraps cache_bench in `perf`.
#
# Usage:
#   ./scripts/run_standardized_benchmarks.sh <machine> <core> <benchmark>:<footprint_bytes>[,<benchmark>:<footprint_bytes>...]
#
# <benchmark> is a free-form label (this project's 3 standardized names are
# L1_resident, LLC_random, beyond_LLC) -- <footprint_bytes> MUST already be a
# hand-confirmed value from that machine's own FINAL_CACHE_TABLE.md /
# CAPACITY_RESULTS.md (L1_resident/LLC_random) or the project's existing
# universal DRAM-scale constant, 536870912 / 512 MiB (beyond_LLC) -- this
# script does not look values up automatically.
#
# Example (Sunbird, core 1, this machine's own confirmed L1/LLC values):
#   ./scripts/run_standardized_benchmarks.sh sunbird 1 \
#     L1_resident:32768,LLC_random:31457280,beyond_LLC:536870912
#
# Output:
#   data_raw/<machine>/eight_counters/<benchmark>/<benchmark>_perfstat_<group>_<run_tag>_<ts>.csv
#   data_raw/<machine>/eight_counters/<benchmark>/<benchmark>_bench_<group>_<run_tag>_<ts>.csv
#   data_processed/<machine>/eight_counters/<benchmark>/eight_counters_summary_<ts>.csv
#   data_raw/<machine>/eight_counters/run_standardized_benchmarks_<ts>.log
#
# After it finishes, add an eight_counters/ section to
# data_raw/<machine>/README.md and fold into CLAUDE.md's 8.4 status.
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <benchmark>:<footprint_bytes>[,<benchmark>:<footprint_bytes>...]" >&2
  echo "       footprint_bytes MUST already be a hand-confirmed FINAL_CACHE_TABLE.md/CAPACITY_RESULTS.md value" >&2
  echo "       (or the project's universal 536870912 for beyond_LLC)." >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
BENCH_SPEC_CSV="$3"

SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
REPEATS=2   # base + 2 reproducibility repeats, each its own seed (base_seed + index)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_ROOT="data_raw/${MACHINE}/eight_counters"
PROC_ROOT="data_processed/${MACHINE}/eight_counters"
mkdir -p "$RAW_ROOT" "$PROC_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_ROOT}/run_standardized_benchmarks_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_standardized_benchmarks: machine=${MACHINE} core=${CORE} base_seed=${SEED} =="
echo "== timestamp=${TS} =="

make -s

# group_name:events -- iterated in this fixed order (not a bash associative
# array) so output is deterministic and doesn't depend on hash order.
GROUP_NAMES=(cache l1 llc tlb)
GROUP_EVENTS=(
  "cache-references,cache-misses"
  "L1-dcache-loads,L1-dcache-load-misses"
  "LLC-loads,LLC-load-misses"
  "L1-dcache-stores,dTLB-load-misses"
)

run_group() {
  # run_group <events> <footprint> <seed> <out_perf_csv> <out_bench_csv>
  local events="$1" footprint="$2" seed="$3" out_perf="$4" out_bench="$5"
  perf stat -x, -e "duration_time,${events}" \
    -- taskset -c "$CORE" ./cache_bench --experiment hit_latency --load-mode dependent \
       --pattern random --samples "$SAMPLES" --batch-size "$BATCH" \
       --footprint-bytes "$footprint" --warmup-passes "$WARMUP" --seed "$seed" \
       > "$out_bench" 2> "$out_perf"
}

IFS=',' read -r -a BENCH_SPECS <<< "$BENCH_SPEC_CSV"
for spec in "${BENCH_SPECS[@]}"; do
  BENCHMARK="${spec%%:*}"
  FOOTPRINT="${spec#*:}"
  if [ "$BENCHMARK" = "$spec" ] || [ -z "$FOOTPRINT" ]; then
    echo "ERROR: malformed benchmark spec '${spec}' (expected <benchmark>:<footprint_bytes>)" >&2
    exit 1
  fi

  RAW_DIR="${RAW_ROOT}/${BENCHMARK}"
  PROC_DIR="${PROC_ROOT}/${BENCHMARK}"
  mkdir -p "$RAW_DIR" "$PROC_DIR"

  echo ""
  echo "== benchmark ${BENCHMARK}: footprint_bytes=${FOOTPRINT} =="

  ALL_PERF_CSVS=()
  for run_tag in base rep1 rep2; do
    if [ "$run_tag" = "base" ]; then
      SEED_THIS="$SEED"
    else
      r="${run_tag#rep}"
      [ "$r" -gt "$REPEATS" ] && continue
      SEED_THIS=$((SEED + r))
    fi
    echo "-- ${run_tag} (seed=${SEED_THIS}) --"
    for i in "${!GROUP_NAMES[@]}"; do
      gname="${GROUP_NAMES[$i]}"
      events="${GROUP_EVENTS[$i]}"
      OUT_PERF="${RAW_DIR}/${BENCHMARK}_perfstat_${gname}_${run_tag}_${TS}.csv"
      OUT_BENCH="${RAW_DIR}/${BENCHMARK}_bench_${gname}_${run_tag}_${TS}.csv"
      run_group "$events" "$FOOTPRINT" "$SEED_THIS" "$OUT_PERF" "$OUT_BENCH"
      echo "  group=${gname} -> ${OUT_PERF}"
      ALL_PERF_CSVS+=("$OUT_PERF")
    done
  done

  SUM="${PROC_DIR}/eight_counters_summary_${TS}.csv"
  python3 scripts/summarize_eight_counters.py --benchmark "$BENCHMARK" "${ALL_PERF_CSVS[@]}" -o "$SUM"
  echo "-- wrote ${SUM} --"
done

echo ""
echo "== done =="
echo "== record in data_raw/${MACHINE}/README.md eight_counters/ section: core=${CORE}, base_seed=${SEED}" \
     "(repeats use base_seed+index), samples=${SAMPLES}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
