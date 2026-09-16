#!/bin/bash
#
# hw1_capacity_relook.sh -- generic reproducibility re-run of
# scripts/run_capacity_full.sh for one Hazel generation, writing into a
# SEPARATE nested subdirectory under that machine's own data_raw/
# data_processed tree (data_raw/<machine>/capacity_rerun/capacity/..., via
# a MACHINE_ARG of the form "hazel_<gen>/capacity_rerun") rather than
# overwriting the original run's own capacity/ directory. Several
# generations' capacity curves came back noisy/anomalous on the first pass
# (see CLAUDE.md / each data_raw/<machine>/README.md's capacity/ section) --
# this re-run is purely for reproducibility comparison; the original data is
# kept as-is, not clobbered. Same nested-subdirectory convention as
# hw1_line_size_relook.sh's own capacity_rerun precedent.
#
# One shared script for all 9 generations -- per-run specifics (constraint,
# output/error log paths) are passed via sbatch command-line overrides at
# submit time, e.g.:
#   sbatch --constraint=haswell \
#     --output=data_raw/hazel_haswell/hw1_capacity_relook_%j.log \
#     --error=data_raw/hazel_haswell/hw1_capacity_relook_%j.err.log \
#     --export=ALL,MACHINE_ARG=hazel_haswell/capacity_rerun \
#     hpc_slurm/hw1_capacity_relook.sh
#
# Capacity ONLY -- deliberately does not chain into line_size/associativity/
# latency/inclusion_policy the way the original first-pass jobs did.
#
#SBATCH --job-name=hw1_cap_relook
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
#SBATCH --partition=compute_partners

set -euo pipefail

: "${MACHINE_ARG:?must set MACHINE_ARG via --export, e.g. hazel_haswell/capacity_rerun}"

echo "=== Machine identification (Phase Discipline whitelist only) ==="
hostname
uname -a
grep -m1 -E 'model name|Hardware|Processor' /proc/cpuinfo
lscpu -e=CPU,CORE,SOCKET,NODE
CORE=$(numactl -s 2>/dev/null | awk '/physcpubind/{print $2}')
echo "Assigned logical CPU (physcpubind, informational -- srun --cpu-bind=cores does the real pinning): ${CORE:-unknown}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-unset}"
echo

echo "=== Phase Discipline gate check: is predictions-frozen an ancestor of HEAD? ==="
if ! git merge-base --is-ancestor predictions-frozen HEAD 2>/dev/null; then
  echo "predictions-frozen is NOT an ancestor of HEAD -- refusing to run." >&2
  exit 1
fi
echo "OK -- predictions-frozen confirmed ancestor of HEAD, proceeding."
echo

source hpc_slurm/hazel_python_env.sh

echo "=== Running scripts/run_capacity_full.sh (HAZEL_MODE=1) for ${MACHINE_ARG} ==="
HAZEL_MODE=1 ./scripts/run_capacity_full.sh "${MACHINE_ARG}" "${CORE:-0}"

echo
echo "=== Done ==="
