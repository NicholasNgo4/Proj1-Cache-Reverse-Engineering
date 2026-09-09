#!/bin/bash
#
# run_line_size_sweep.sh
#
# Phase-I (timing-only) cache-line-size sweep driver. Builds cache_bench if
# needed, pins it to one logical core with taskset, runs the
# --experiment line_size sweep, and writes the raw CSV under
# data_raw/<machine>/line_size/. On Hazel, use `srun --cpu-bind=cores
# ./cache_bench ...` directly instead (see hpc_slurm/), taskset is for the
# ECE lab machines.
#
# --footprint-bytes must be chosen near a known capacity boundary (e.g. the
# machine's L1 size) or the line-size knee is invisible -- see
# scripts/run_line_size_full.sh, which picks it automatically from an
# existing capacity summary.
#
# Usage:
#   ./scripts/run_line_size_sweep.sh <machine_name> [core] [extra cache_bench args...]
#
# Example:
#   ./scripts/run_line_size_sweep.sh artemisia 4 --footprint-bytes 39321 --min-stride 8 --max-stride 256
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

OUT_DIR="data_raw/${MACHINE}/line_size"
mkdir -p "$OUT_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="${OUT_DIR}/line_size_${TS}.csv"

echo "Running line_size sweep on ${MACHINE}, core ${CORE} -> ${OUT_FILE}" >&2
taskset -c "$CORE" ./cache_bench --experiment line_size "$@" | tee "$OUT_FILE" > /dev/null

echo "Done. Raw data: ${OUT_FILE}" >&2
echo "Next: python3 scripts/summarize_raw.py ${OUT_FILE} -o data_processed/${MACHINE}/line_size/summary.csv" >&2
