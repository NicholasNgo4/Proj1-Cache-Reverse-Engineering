#!/bin/bash
#
# hw1_icelake_8358_associativity.sh -- Phase-I associativity experiment, icelake_8358
# generation, via scripts/run_associativity_full.sh (HAZEL_MODE=1). Same
# boundary values as line_size (see data_raw/hazel_icelake_8358/README.md's
# capacity/ section): L1=32768 B (best-guess), L2=1310720 B (reasoned),
# LLC=50331648 B / 48 MiB (best-guess placeholder, unresolved). No ASSOC_ALLOW_AUTO -- explicit
# cache_bytes_csv given, per this script's own hand-confirmed-only policy.
#
#SBATCH --job-name=hw1_associativity
#SBATCH --output=data_raw/hazel_icelake_8358/hw1_icelake_8358_associativity_%j.log
#SBATCH --error=data_raw/hazel_icelake_8358/hw1_icelake_8358_associativity_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=icelake_8358

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
HAZEL_MODE=1 ./scripts/run_associativity_full.sh hazel_icelake_8358 "${CORE:-0}" 32768,1310720,50331648

echo
echo "=== Done ==="
