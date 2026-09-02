#!/bin/bash
#
# run_capacity_sweep.sh
#
# Phase-I (timing-only) cache-capacity sweep driver. Builds cache_bench if
# needed, pins it to one logical core with taskset, runs the
# --experiment capacity sweep, and writes the raw CSV under
# data_raw/<machine>/capacity/. On Hazel, use `srun --cpu-bind=cores
# ./cache_bench ...` directly instead (see hpc_slurm/), taskset is for the
# ECE lab machines.
#
# Usage:
#   ./scripts/run_capacity_sweep.sh <machine_name> [core] [extra cache_bench args...]
#
# Example:
#   ./scripts/run_capacity_sweep.sh artemisia 4 --samples 1000000 --max-bytes 67108864
#
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <machine_name> [core] [extra cache_bench args...]" >&2
  exit 1
fi

MACHINE="$1"; shift
CORE="${1:-4}"
if [ $# -ge 1 ]; then
  shift
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

make -s

OUT_DIR="data_raw/${MACHINE}/capacity"
mkdir -p "$OUT_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="${OUT_DIR}/capacity_${TS}.csv"

echo "Running capacity sweep on ${MACHINE}, core ${CORE} -> ${OUT_FILE}" >&2
taskset -c "$CORE" ./cache_bench --experiment capacity "$@" | tee "$OUT_FILE" > /dev/null

echo "Done. Raw data: ${OUT_FILE}" >&2
echo "Next: python3 scripts/summarize_raw.py ${OUT_FILE} -o data_processed/${MACHINE}/capacity/summary.csv" >&2
