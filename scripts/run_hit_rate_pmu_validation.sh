#!/bin/bash
#
# run_hit_rate_pmu_validation.sh -- Problem 8.5 part 4: Phase-II perf-stat
# validation of the software-only hit-rate estimator (--experiment hit_rate,
# main_code/software_hit_rate/) against a real PMU-derived hit rate.
#
# REDESIGNED 2026-09-14 after the original single-perf-wrapped-invocation
# design was found to produce invalid results on Sunbird -- see
# data_raw/sunbird/software_hit_rate/README notes / conversation history for
# the full investigation. Two separate, compounding problems were found in
# the original design and are both fixed here:
#
#   1. FOOTPRINT: the original design tested each level at its exact
#      CAPACITY_RESULTS.md boundary value (e.g. L1 at exactly 32768 B on
#      Sunbird). A capacity-sweep boundary is, by definition, the edge of a
#      level, not a safely-inside-it point -- the working (non-PMU)
#      hit_rate sweep already showed this is genuinely fragile (Hhat=0.87,
#      not ~1.0, at the exact L1 boundary; a controlled reseed showed the
#      SAME footprint swinging from 0.37 to 1.0 seed-to-seed with no perf
#      involved at all). Fix: for L1/L2/LLC, this script now tests at HALF
#      the given footprint (a "safely inside the level" point, the same
#      "boundary's midpoint" convention run_hit_latency_full.sh's own
#      docstring already uses) rather than the exact boundary. DRAM's
#      footprint is left as given -- it is not a capacity edge in the same
#      sense, just a fixed "deep in DRAM" reference.
#
#   2. PERF-STAT DISTORTION OF THE ESTIMATOR'S OWN TIMING: the original
#      design perf-wrapped a SECOND `--experiment hit_rate` invocation
#      directly, in PMU VALIDATION MODE, to get Hhat and H_pmu from the
#      IDENTICAL timed accesses. This was found to be invalid: hit_rate's
#      classifier depends on 50,000+ SINGLE-SHOT lfence+rdtsc(p) timings
#      (one pair per access, main_code/software_hit_rate/software_hit_rate.c's
#      time_single_shot_chain()) -- a controlled A/B replay (same binary,
#      same args, same seed, only difference is the perf wrapper) showed
#      `perf stat` reproducibly and severely distorts this specific timing
#      style on Sunbird: wall time for a workload that should finish in low
#      single-digit milliseconds instead took 1.7-2.9 SECONDS under perf,
#      and Hhat swung from ~1.0 (unwrapped) to as low as 0.0 (wrapped) for
#      the IDENTICAL seed/footprint. This project's own hit_latency
#      experiment, by contrast, uses BATCHED timing (one timer_start/stop
#      pair around a whole batch of accesses, main_code/common/benchmark.c)
#      and has already been perf-wrapped cleanly on every team machine via
#      scripts/run_pmu_verification.sh -- the single-shot vs. batched
#      distinction is the likely reason one survives perf-wrapping and the
#      other doesn't (leading hypothesis, not exhaustively root-caused:
#      nmi_watchdog=1 is confirmed active on Sunbird and already documented
#      elsewhere in this project as pinning a PMU counter here; this
#      machine tests out as bare metal via systemd-detect-virt, ruling out
#      a VM-trap explanation).
#
#      Fix: Hhat and H_pmu no longer come from the same invocation.
#        - Hhat now comes from an UNWRAPPED (no perf) `--experiment
#          hit_rate` run in PMU validation mode (tau/Se/Sp fixed from step
#          1's calibration, same as before) -- clean, undistorted timing.
#        - H_pmu now comes from a SEPARATE perf-wrapped `--experiment
#          hit_latency` run (BATCHED timing, load-mode dependent, pattern
#          random) at the SAME footprint/seed, using the exact
#          SAMPLES/BATCH/WARMUP already validated clean by
#          run_pmu_verification.sh on this machine. This keeps perf's
#          counters scoped to a workload of the same size/pattern without
#          ever perf-wrapping hit_rate's own fragile single-shot loop, and
#          keeps PMU-reading code out of software_hit_rate.c entirely (only
#          this harness decides which experiment/mode to invoke, same
#          discipline as the original design).
#
# Usage:
#   ./scripts/run_hit_rate_pmu_validation.sh <machine> <core> <level>:<footprint_bytes>[,...]
#
# <footprint_bytes> is still the raw CAPACITY_RESULTS.md value for that
# level (for L1/L2/LLC this script internally tests at footprint_bytes/2 --
# see fix 1 above; DRAM is tested at footprint_bytes as given).
#
# Example:
#   ./scripts/run_hit_rate_pmu_validation.sh sunbird 1 L1:32768,L2:262144,LLC:31457280,DRAM:536870912
#
# Output:
#   data_raw/<machine>/software_hit_rate/pmu/<level>/<level>_calibonly_<run_tag>_<ts>.csv  step-1 plain calibration-only run (tau/Se/Sp source)
#   data_raw/<machine>/software_hit_rate/pmu/<level>/<level>_bench_<run_tag>_<ts>.csv      step-2 UNWRAPPED hit_rate run (Hhat source)
#   data_raw/<machine>/software_hit_rate/pmu/<level>/<level>_hitlatpmu_<run_tag>_<ts>.csv  step-3 hit_latency's own CSV (supplementary, not required by compare_hit_rate_pmu.py)
#   data_raw/<machine>/software_hit_rate/pmu/<level>/<level>_perfstat_<run_tag>_<ts>.csv   step-3 raw perf stat -x, output wrapping step-3's hit_latency run (H_pmu source)
#   data_processed/<machine>/software_hit_rate/pmu_validation_<ts>.csv                     parsed comparison (see compare_hit_rate_pmu.py)
#   data_raw/<machine>/software_hit_rate/pmu/run_hit_rate_pmu_validation_<ts>.log          transcript
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <level>:<footprint_bytes>[,<level>:<footprint_bytes>...]" >&2
  echo "       footprint_bytes MUST already be a hand-confirmed CAPACITY_RESULTS.md value." >&2
  echo "       (L1/L2/LLC are automatically tested at footprint_bytes/2 -- see this" >&2
  echo "       script's header comment for why; DRAM is tested as given.)" >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
LEVEL_SPEC_CSV="$3"

SEED=12345
REPEATS=2   # base + 2 reproducibility repeats, each its own seed (base_seed + index)

# hit_latency parameters for the H_pmu measurement -- identical to
# run_pmu_verification.sh's own already-perf-validated-clean values on this
# machine, deliberately not re-tuned here.
HL_SAMPLES=1000000
HL_BATCH=1000
HL_WARMUP=3

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_ROOT="data_raw/${MACHINE}/software_hit_rate/pmu"
PROC_ROOT="data_processed/${MACHINE}/software_hit_rate"
mkdir -p "$RAW_ROOT" "$PROC_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_ROOT}/run_hit_rate_pmu_validation_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_hit_rate_pmu_validation: machine=${MACHINE} core=${CORE} base_seed=${SEED} =="
echo "== timestamp=${TS} =="

make -s

safe_footprint() {
  # safe_footprint <level> <raw_footprint> -- L1/L2/LLC get halved (a
  # "safely inside the level" point instead of the exact capacity edge);
  # DRAM is returned unchanged. See header comment, fix 1.
  local level="$1" raw="$2"
  if [ "$level" = "DRAM" ]; then
    echo "$raw"
  else
    echo $((raw / 2))
  fi
}

run_one() {
  # run_one <safe_footprint> <seed> <out_calibonly> <out_bench> <out_hitlatpmu> <out_perf>
  local footprint="$1" seed="$2" out_calibonly="$3" out_bench="$4" out_hitlatpmu="$5" out_perf="$6"

  # Step 1: plain, unwrapped, full self-calibrating hit_rate mode -- throwaway
  # test-phase (minimum --test-samples), only tau/Se/Sp kept.
  taskset -c "$CORE" ./cache_bench --experiment hit_rate \
    --test-bytes "$footprint" --test-samples 100 --seed "$seed" \
    > "$out_calibonly"
  local result_line
  result_line="$(grep '^# result' "$out_calibonly")"
  local tau se sp
  tau="$(grep -oP 'tau_ticks=\K[0-9.]+' <<< "$result_line")"
  se="$(grep -oP 'sensitivity=\K[0-9.]+' <<< "$result_line")"
  sp="$(grep -oP 'specificity=\K[0-9.]+' <<< "$result_line")"
  echo "  calibration: tau=${tau} sensitivity=${se} specificity=${sp} (-> ${out_calibonly})"

  # Step 2: Hhat measurement -- UNWRAPPED (no perf) hit_rate run in PMU
  # validation mode (tau/Se/Sp fixed from step 1), full test-samples. Never
  # perf-wrapped -- see header comment, fix 2.
  taskset -c "$CORE" ./cache_bench --experiment hit_rate \
    --test-bytes "$footprint" --seed "$seed" \
    --tau "$tau" --sensitivity "$se" --specificity "$sp" \
    > "$out_bench"
  local hhat
  hhat="$(grep -oP 'Hhat=\K[0-9.]+' <<< "$(grep '^# result' "$out_bench")")"
  echo "  Hhat (unwrapped): ${hhat} (-> ${out_bench})"

  # Step 3: H_pmu measurement -- perf-wrapped BATCHED hit_latency run at the
  # same footprint/pattern/seed, decoupled from hit_rate's own fragile
  # single-shot timing. See header comment, fix 2.
  perf stat -x, -e "duration_time,cache-references,cache-misses" \
    -- taskset -c "$CORE" ./cache_bench --experiment hit_latency \
       --load-mode dependent --pattern random \
       --samples "$HL_SAMPLES" --batch-size "$HL_BATCH" \
       --footprint-bytes "$footprint" --warmup-passes "$HL_WARMUP" --seed "$seed" \
       > "$out_hitlatpmu" 2> "$out_perf"
  echo "  H_pmu source (perf-wrapped hit_latency): -> ${out_perf} / ${out_hitlatpmu}"
}

ALL_PAIRS=()
IFS=',' read -r -a LEVEL_SPECS <<< "$LEVEL_SPEC_CSV"
for spec in "${LEVEL_SPECS[@]}"; do
  LEVEL="${spec%%:*}"
  RAW_FOOTPRINT="${spec#*:}"
  if [ "$LEVEL" = "$spec" ] || [ -z "$RAW_FOOTPRINT" ]; then
    echo "ERROR: malformed level spec '${spec}' (expected <level>:<footprint_bytes>)" >&2
    exit 1
  fi
  FOOTPRINT="$(safe_footprint "$LEVEL" "$RAW_FOOTPRINT")"

  RAW_DIR="${RAW_ROOT}/${LEVEL}"
  mkdir -p "$RAW_DIR"

  echo ""
  echo "== level ${LEVEL}: capacity_results_bytes=${RAW_FOOTPRINT} tested_footprint_bytes=${FOOTPRINT} =="

  for run_tag in base rep1 rep2; do
    if [ "$run_tag" = "base" ]; then
      SEED_THIS="$SEED"
    else
      r="${run_tag#rep}"
      [ "$r" -gt "$REPEATS" ] && continue
      SEED_THIS=$((SEED + r))
    fi
    OUT_CALIBONLY="${RAW_DIR}/${LEVEL}_calibonly_${run_tag}_${TS}.csv"
    OUT_BENCH="${RAW_DIR}/${LEVEL}_bench_${run_tag}_${TS}.csv"
    OUT_HITLATPMU="${RAW_DIR}/${LEVEL}_hitlatpmu_${run_tag}_${TS}.csv"
    OUT_PERF="${RAW_DIR}/${LEVEL}_perfstat_${run_tag}_${TS}.csv"
    echo "-- ${run_tag} (seed=${SEED_THIS}) --"
    run_one "$FOOTPRINT" "$SEED_THIS" "$OUT_CALIBONLY" "$OUT_BENCH" "$OUT_HITLATPMU" "$OUT_PERF"
    ALL_PAIRS+=("${LEVEL}:${FOOTPRINT}:${OUT_PERF}:${OUT_BENCH}")
  done
done

SUM="${PROC_ROOT}/pmu_validation_${TS}.csv"
python3 scripts/compare_hit_rate_pmu.py "${ALL_PAIRS[@]}" -o "$SUM"
echo "-- wrote ${SUM} --"

echo ""
echo "== done =="
echo "== record in data_raw/${MACHINE}/README.md software_hit_rate/ section: core=${CORE}," \
     "base_seed=${SEED} (repeats use base_seed+index), timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
