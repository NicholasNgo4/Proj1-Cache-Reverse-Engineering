#!/bin/bash
#
# run_hit_latency_full.sh -- one-command Phase-I hit-latency pipeline for one
# machine, per cache level: base sweep (dependent + independent load modes,
# both patterns) -> reproducibility repeats -> plots. Repeated once per
# cache level, at a single fixed working-set footprint per level (see
# main_code/common/latency.h -- this experiment infers nothing about
# capacity itself, only latency at a footprint the caller already trusts).
#
# Mirrors run_associativity_full.sh's philosophy and structure: deliberately
# NOT adaptive, every level is just a fixed footprint run through the same
# base+repeats+plot sequence. No auto-detection exists here at all (unlike
# associativity's ASSOC_ALLOW_AUTO opt-in) -- footprint_bytes MUST be a
# hand-confirmed capacity boundary's midpoint from that machine's own
# data_raw/<machine>/README.md capacity section, passed explicitly.
#
# Usage:
#   ./scripts/run_hit_latency_full.sh <machine> <core> <level>:<footprint_bytes>[,<level>:<footprint_bytes>...]
#
# Example:
#   ./scripts/run_hit_latency_full.sh sunbird 2 L1:32768,LLC:27262976,DRAM:536870912
#
# Output:
#   data_raw/<machine>/latency/hit/<level>/*.csv          raw per-batch samples
#   data_processed/<machine>/latency/hit/<level>/*.csv    per-(load_mode,pattern) distribution
#                                                           summaries, timestamped per run (not
#                                                           overwritten by a later run, same
#                                                           rationale as run_associativity_full.sh)
#   data_processed/<machine>/latency/hit/<level>/plots/   hit_latency_boxplots (png+pdf)
#   data_raw/<machine>/latency/run_hit_latency_full_<ts>.log  full transcript of this run
#
# After it finishes, fill in data_raw/<machine>/README.md's latency/ section
# using the machine/core/seed/timestamp/footprint printed at the end for
# each level.
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <level>:<footprint_bytes>[,<level>:<footprint_bytes>...]" >&2
  echo "       footprint_bytes MUST already be a hand-confirmed capacity boundary's" >&2
  echo "       midpoint for that level -- see data_raw/<machine>/README.md's capacity" >&2
  echo "       section. No auto-detection exists for this experiment." >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
LEVEL_SPEC_CSV="$3"

SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
REPEATS=2   # extra repeats of the base run, each at its own seed (SEED + repeat index),
            # same rationale as run_associativity_full.sh: a fixed seed only re-checks
            # system-noise reproducibility, not sensitivity to access order.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_ROOT="data_raw/${MACHINE}/latency/hit"
PROC_ROOT="data_processed/${MACHINE}/latency/hit"
mkdir -p "$RAW_ROOT" "$PROC_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="data_raw/${MACHINE}/latency/run_hit_latency_full_${TS}.log"
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

echo "== run_hit_latency_full: machine=${MACHINE} core=${CORE} base_seed=${SEED} =="
echo "== timestamp=${TS} =="

HAZEL_MODE="${HAZEL_MODE:-0}"
if [ "$HAZEL_MODE" = "1" ]; then
  # Isolated per-job build -- avoids races when several of this project's
  # Hazel Slurm jobs land RUNNING at the same time in this one shared GPFS
  # checkout (unlike the lab machines, which each have their own separate,
  # non-shared /home -- see CLAUDE.md). Confirmed the hard way: a same-batch
  # submission of sister access-check jobs that all ran `make clean && make`
  # directly in this checkout produced a missing-.o link failure on one job.
  : "${SLURM_JOB_ID:?HAZEL_MODE=1 requires running under Slurm (SLURM_JOB_ID unset)}"
  BUILD_DIR="${REPO_ROOT}/hazel_build/${SLURM_JOB_ID}"
  rm -rf "$BUILD_DIR"
  mkdir -p "$BUILD_DIR"
  cp -r main_code Makefile "$BUILD_DIR/"
  ( cd "$BUILD_DIR" && make -s )
  BENCH="${BUILD_DIR}/cache_bench"
  PIN_CMD=(srun --cpu-bind=cores)
  cleanup_hazel_build() { rm -rf "$BUILD_DIR"; }
  trap cleanup_hazel_build EXIT
else
  make -s
  BENCH="./cache_bench"
  PIN_CMD=(taskset -c "$CORE")
fi

run_sweep() {
  # run_sweep <load_mode> <pattern> <footprint_bytes> <out_csv> [seed]
  local mode="$1" pattern="$2" footprint="$3" out="$4" seed="${5:-$SEED}"
  "${PIN_CMD[@]}" "$BENCH" --experiment hit_latency --load-mode "$mode" \
    --pattern "$pattern" --samples "$SAMPLES" --batch-size "$BATCH" \
    --footprint-bytes "$footprint" --warmup-passes "$WARMUP" --seed "$seed" > "$out"
  echo "  wrote $(wc -l < "$out") lines -> $out (mode=${mode} pattern=${pattern} seed=${seed})"
}

summarize() {
  python3 scripts/summarize_raw.py "$1" -o "$2" >/dev/null
}

RESULTS=()

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
  PLOT_DIR="${PROC_DIR}/plots"
  mkdir -p "$RAW_DIR" "$PROC_DIR" "$PLOT_DIR"

  echo ""
  echo "== level ${LEVEL}: footprint_bytes=${FOOTPRINT} =="

  ALL_SUMMARIES=()

  for run_tag in base rep1 rep2; do
    if [ "$run_tag" = "base" ]; then
      SEED_THIS="$SEED"
    else
      r="${run_tag#rep}"
      [ "$r" -gt "$REPEATS" ] && continue
      SEED_THIS=$((SEED + r))
    fi
    echo "-- ${run_tag} (seed=${SEED_THIS}) --"
    for mode in dependent independent; do
      for pattern in random sequential; do
        OUT="${RAW_DIR}/hit_latency_${run_tag}_${mode}_${pattern}_${TS}.csv"
        SUM="${PROC_DIR}/${run_tag}_${mode}_${pattern}_summary_${TS}.csv"
        run_sweep "$mode" "$pattern" "$FOOTPRINT" "$OUT" "$SEED_THIS"
        summarize "$OUT" "$SUM"
        ALL_SUMMARIES+=("$SUM")
      done
    done
  done

  echo "-- generating plots for ${LEVEL} --"
  if ! python3 scripts/plot_hit_latency.py \
    "${ALL_SUMMARIES[@]}" \
    -o "$PLOT_DIR" --machine "$MACHINE" --level "$LEVEL" \
    --title-suffix "(Phase I timing-only, auto pipeline)"; then
    echo "WARNING: plotting failed for ${LEVEL} (matplotlib missing? see CLAUDE.md's known" >&2
    echo "  matplotlib gap on Skylark/Thunderbird/Ookay) -- data above is still valid;" >&2
    echo "  continuing to the next level and re-run plot_hit_latency.py by hand once" >&2
    echo "  matplotlib is available." >&2
  fi

  echo "-- compressing raw CSVs for ${LEVEL} --"
  gzip -f "${RAW_DIR}"/hit_latency_*.csv

  RESULTS+=("${LEVEL}: footprint_bytes=${FOOTPRINT}")
done

echo ""
echo "== done =="
for r in "${RESULTS[@]}"; do
  echo "== ${r} =="
done
echo "== record in data_raw/${MACHINE}/README.md: core=${CORE}, base_seed=${SEED} (repeats use base_seed+index)," \
     "samples=${SAMPLES}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
