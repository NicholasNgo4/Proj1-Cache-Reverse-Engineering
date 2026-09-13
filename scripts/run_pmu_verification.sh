#!/bin/bash
#
# run_pmu_verification.sh -- Phase II perf-stat-based PMU verification pipeline.
# For each cache level (a hand-confirmed CAPACITY_RESULTS.md footprint), runs
# the SAME `cache_bench --experiment hit_latency` invocation Phase I already
# used, but wrapped in `perf stat` to get an independent, hardware-counter-
# based cross-check of both the miss-rate/capacity story and the latency
# number -- alongside cache_bench's own RDTSC-based ticks/access from the
# exact same run, for direct side-by-side comparison.
#
# Only runnable AFTER Phase I is frozen/tagged (see README.md's Phase
# Discipline section, tag: phase1-timing-only) -- this is the first thing in
# the repo allowed to touch `perf`.
#
# Why 4 separate perf invocations per (level, run_tag) instead of one big
# `-e a,b,c,d,e,f` command: this machine's PMU only reliably schedules 2
# hardware (generic, programmable) counters at once at 100% -- confirmed by
# hand before writing this script (NMI watchdog reserves one counter, and a
# 3-event group only scheduled 57-71%, not 100%). Software `duration_time` is
# always-on and doesn't consume a counter, so every group also carries it, as
# an independent wall-clock cross-check of cache_bench's own RDTSC-based
# timer. If a machine still reports `<not counted>` for a 2-event group (e.g.
# heavier PMU contention from other students' jobs), that is a real, honestly
# documented limitation, not a bug to silently paper over.
#
# Usage:
#   ./scripts/run_pmu_verification.sh <machine> <core> <level>:<footprint_bytes>[,<level>:<footprint_bytes>...]
#
# Example:
#   ./scripts/run_pmu_verification.sh sunbird 1 L1:32768,L2:262144,LLC:31457280
#
# Output:
#   data_raw/<machine>/pmu/<level>/<level>_perfstat_<group>_<run_tag>_<ts>.csv   raw perf stat -x, output
#   data_raw/<machine>/pmu/<level>/<level>_bench_<group>_<run_tag>_<ts>.csv      cache_bench's own CSV from the same run
#   data_processed/<machine>/pmu/<level>/pmu_summary_<ts>.csv                    parsed/combined summary (see summarize_pmu.py)
#   data_raw/<machine>/pmu/run_pmu_verification_<ts>.log                        full transcript
#
# After it finishes, add a pmu/ section to data_raw/<machine>/README.md and
# fold the summary into data_processed/<machine>/PHASE2_VALIDATION_TABLE.md.
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <level>:<footprint_bytes>[,<level>:<footprint_bytes>...]" >&2
  echo "       footprint_bytes MUST already be a hand-confirmed CAPACITY_RESULTS.md value." >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
LEVEL_SPEC_CSV="$3"

SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
REPEATS=2   # base + 2 reproducibility repeats, each its own seed (base_seed + index)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_ROOT="data_raw/${MACHINE}/pmu"
PROC_ROOT="data_processed/${MACHINE}/pmu"
mkdir -p "$RAW_ROOT" "$PROC_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_ROOT}/run_pmu_verification_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_pmu_verification: machine=${MACHINE} core=${CORE} base_seed=${SEED} =="
echo "== timestamp=${TS} =="

make -s

# group_name:events -- iterated in this fixed order (not a bash associative
# array) so output is deterministic and doesn't depend on hash order.
GROUP_NAMES=(cache l1 llc cyc)
GROUP_EVENTS=(
  "cache-references,cache-misses"
  "L1-dcache-loads,L1-dcache-load-misses"
  "LLC-loads,LLC-load-misses"
  "cycles,instructions"
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

IFS=',' read -r -a LEVEL_SPECS <<< "$LEVEL_SPEC_CSV"
for spec in "${LEVEL_SPECS[@]}"; do
  LEVEL="${spec%%:*}"
  FOOTPRINT="${spec#*:}"
  if [ "$LEVEL" = "$spec" ] || [ -z "$FOOTPRINT" ]; then
    echo "ERROR: malformed level spec '${spec}' (expected <level>:<footprint_bytes>)" >&2
    exit 1
  fi

  RAW_DIR="${RAW_ROOT}/${LEVEL}"
  PROC_DIR="${PROC_ROOT}/${LEVEL}"
  mkdir -p "$RAW_DIR" "$PROC_DIR"

  echo ""
  echo "== level ${LEVEL}: footprint_bytes=${FOOTPRINT} =="

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
      OUT_PERF="${RAW_DIR}/${LEVEL}_perfstat_${gname}_${run_tag}_${TS}.csv"
      OUT_BENCH="${RAW_DIR}/${LEVEL}_bench_${gname}_${run_tag}_${TS}.csv"
      run_group "$events" "$FOOTPRINT" "$SEED_THIS" "$OUT_PERF" "$OUT_BENCH"
      echo "  group=${gname} -> ${OUT_PERF}"
      ALL_PERF_CSVS+=("$OUT_PERF")
    done
  done

  SUM="${PROC_DIR}/pmu_summary_${TS}.csv"
  python3 scripts/summarize_pmu.py --level "$LEVEL" "${ALL_PERF_CSVS[@]}" -o "$SUM"
  echo "-- wrote ${SUM} --"
done

echo ""
echo "== done =="
echo "== record in data_raw/${MACHINE}/README.md pmu/ section: core=${CORE}, base_seed=${SEED}" \
     "(repeats use base_seed+index), samples=${SAMPLES}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
