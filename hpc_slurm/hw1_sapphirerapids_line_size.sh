#!/bin/bash
#
# hw1_sapphirerapids_line_size.sh -- Phase-I line-size experiment, sapphirerapids
# generation, via scripts/run_line_size.sh (HAZEL_MODE=1). Boundaries used
# (see data_raw/hazel_sapphirerapids/README.md's capacity/ section for how each
# was derived): L1=49152 B (best-guess -- NOT 32768B, see capacity findings), L2=2097152 B (reasoned --
# NOT independently confirmed this pass, no visible L2 knee in the capacity
# sweep), LLC=39903168 B / ~38.05 MiB (provisional edge where the LLC->DRAM
# climb first clearly departs the plateau). Candidate strides left blank
# (auto skip of Method A step 4) -- no prior run to pick a candidate from.
#
#SBATCH --job-name=hw1_line_size
#SBATCH --output=data_raw/hazel_sapphirerapids/hw1_sapphirerapids_line_size_%j.log
#SBATCH --error=data_raw/hazel_sapphirerapids/hw1_sapphirerapids_line_size_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
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

echo "=== Running scripts/run_line_size.sh (HAZEL_MODE=1) ==="
HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_sapphirerapids "${CORE:-0}" 49152,2097152,39903168

echo
echo "=== Done ==="
