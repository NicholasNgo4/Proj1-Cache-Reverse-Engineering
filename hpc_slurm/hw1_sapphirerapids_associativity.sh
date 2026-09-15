#!/bin/bash
#
# hw1_sapphirerapids_associativity.sh -- Phase-I associativity experiment, sapphirerapids
# generation, via scripts/run_associativity_full.sh (HAZEL_MODE=1). Same
# boundary values as line_size (see data_raw/hazel_sapphirerapids/README.md's
# capacity/ section): L1=49152 B (best-guess -- NOT 32768B, see capacity findings), L2=2097152 B (reasoned),
# LLC=39903168 B / ~38.05 MiB (provisional). No ASSOC_ALLOW_AUTO -- explicit
# cache_bytes_csv given, per this script's own hand-confirmed-only policy.
#
#SBATCH --job-name=hw1_associativity
#SBATCH --output=data_raw/hazel_sapphirerapids/hw1_sapphirerapids_associativity_%j.log
#SBATCH --error=data_raw/hazel_sapphirerapids/hw1_sapphirerapids_associativity_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=sapphirerapids

set -euo pipefail

echo "=== Machine identification (Phase Discipline whitelist only) ==="
hostname
uname -a
grep -m1 -E 'model name|Hardware|Processor' /proc/cpuinfo
CORE=$(numactl -s 2>/dev/null | awk '/physcpubind/{print $2}')
echo "Assigned logical CPU: ${CORE:-unknown}, SLURM_JOB_ID=${SLURM_JOB_ID:-unset}"
echo

if ! git merge-base --is-ancestor predictions-frozen HEAD 2>/dev/null; then
  echo "predictions-frozen is NOT an ancestor of HEAD -- refusing to run." >&2
  exit 1
fi

source hpc_slurm/hazel_python_env.sh

echo "=== Running scripts/run_associativity_full.sh (HAZEL_MODE=1) ==="
HAZEL_MODE=1 ./scripts/run_associativity_full.sh hazel_sapphirerapids "${CORE:-0}" 49152,2097152,39903168

echo
echo "=== Done ==="
