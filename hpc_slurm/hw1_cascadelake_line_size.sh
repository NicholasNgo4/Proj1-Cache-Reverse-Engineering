#!/bin/bash
#
# hw1_cascadelake_line_size.sh -- Phase-I line-size experiment, cascadelake
# generation, via scripts/run_line_size.sh (HAZEL_MODE=1). Boundaries used
# (see data_raw/hazel_cascadelake/README.md's capacity/ section for how each
# was derived): L1=32768 B (confirmed by timing), L2=1048576 B (reasoned --
# NOT independently confirmed this pass, no visible L2 knee in the capacity
# sweep), LLC=16777216 B / 16 MiB (provisional edge where the LLC->DRAM
# climb first clearly departs the plateau). Candidate strides left blank
# (auto skip of Method A step 4) -- no prior run to pick a candidate from.
#
#SBATCH --job-name=hw1_line_size
#SBATCH --output=data_raw/hazel_cascadelake/hw1_cascadelake_line_size_%j.log
#SBATCH --error=data_raw/hazel_cascadelake/hw1_cascadelake_line_size_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=cascadelake

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
HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_cascadelake "${CORE:-0}" 32768,1048576,16777216

echo
echo "=== Done ==="
