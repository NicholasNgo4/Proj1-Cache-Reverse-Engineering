#!/bin/bash
#
# run_software_hit_rate_sweep.sh -- Problem 8.5 demonstration pipeline: runs
# `cache_bench --experiment hit_rate` once per working-set footprint across a
# log-spaced, cache-boundary-anchored sweep, producing the
# Hhat-vs-working-set-size curve (the standalone sanity check for parts 1-3,
# independent of any PMU comparison). Calibration (resident/nonresident)
# re-runs FRESH inside every single invocation -- see
# main_code/software_hit_rate/software_hit_rate.h's module doc comment for
# why that's deliberate, not wasteful: the estimator must self-calibrate
# without depending on a prior run or a stored constant, per the
# Competition's generalization requirement (competition/HIT_RATE_VALIDATION.md).
#
# Usage:
#   ./scripts/run_software_hit_rate_sweep.sh <machine> <core> [footprint_bytes_csv]
#
# If footprint_bytes_csv is omitted, sweeps a default list anchored to
# Sunbird's own confirmed L1/L2/LLC/DRAM boundaries
# (data_processed/sunbird/FINAL_CACHE_TABLE.md) -- override explicitly for
# another machine, same explicit-only discipline as every other experiment's
# footprint arguments in this repo.
#
# Output:
#   data_raw/<machine>/software_hit_rate/raw/hit_rate_<bytes>_<ts>.csv.gz   full per-access raw CSV per point
#   data_raw/<machine>/software_hit_rate/hit_rate_sweep_<ts>.csv            one row per footprint point (see summarize_software_hit_rate.py)
#   data_processed/<machine>/software_hit_rate/plots/                      plots (see plot_software_hit_rate.py)
#   data_raw/<machine>/software_hit_rate/run_software_hit_rate_sweep_<ts>.log  transcript
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <machine> <core> [footprint_bytes_csv]" >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
DEFAULT_SWEEP="4096,16384,32768,65536,131072,262144,1048576,4194304,8388608,16777216,31457280,67108864,134217728,268435456,536870912"
SWEEP_CSV="${3:-$DEFAULT_SWEEP}"

SEED=12345

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_ROOT="data_raw/${MACHINE}/software_hit_rate"
RAW_DETAIL="${RAW_ROOT}/raw"
PROC_ROOT="data_processed/${MACHINE}/software_hit_rate"
mkdir -p "$RAW_ROOT" "$RAW_DETAIL" "$PROC_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_ROOT}/run_software_hit_rate_sweep_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_software_hit_rate_sweep: machine=${MACHINE} core=${CORE} seed=${SEED} =="
echo "== timestamp=${TS} =="

make -s

RAW_FILES=()
IFS=',' read -r -a FOOTPRINTS <<< "$SWEEP_CSV"
for fp in "${FOOTPRINTS[@]}"; do
  OUT="${RAW_DETAIL}/hit_rate_${fp}_${TS}.csv"
  echo "== test_bytes=${fp} =="
  taskset -c "$CORE" ./cache_bench --experiment hit_rate --test-bytes "$fp" --seed "$SEED" > "$OUT"
  echo "  $(grep '^# result' "$OUT")"
  RAW_FILES+=("$OUT")
done

SUMMARY="${RAW_ROOT}/hit_rate_sweep_${TS}.csv"
python3 scripts/summarize_software_hit_rate.py "${RAW_FILES[@]}" -o "$SUMMARY"

echo "-- generating plots --"
LARGEST_RAW="${RAW_FILES[-1]}"
if ! python3 scripts/plot_software_hit_rate.py \
  --summary "$SUMMARY" --calib-raw "$LARGEST_RAW" \
  --boundary "L1:32768" --boundary "L2:262144" --boundary "LLC:31457280" --boundary "DRAM:536870912" \
  -o "${PROC_ROOT}/plots" --machine "$MACHINE"; then
  echo "WARNING: plotting failed -- data above is still valid; re-run plot_software_hit_rate.py by hand." >&2
fi

echo "-- compressing raw per-access CSVs --"
gzip -f "${RAW_DETAIL}"/hit_rate_*.csv

echo ""
echo "== done =="
echo "== summary: ${SUMMARY} =="
echo "== record in data_raw/${MACHINE}/README.md: core=${CORE}, seed=${SEED}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
