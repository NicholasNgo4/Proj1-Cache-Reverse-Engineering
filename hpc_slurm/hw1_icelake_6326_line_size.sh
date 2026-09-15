#!/bin/bash
#
# hw1_icelake_6326_line_size.sh -- Phase-I line-size experiment, icelake_6326
# generation, via scripts/run_line_size.sh (HAZEL_MODE=1). Boundaries used
# (see data_raw/hazel_icelake_6326/README.md's capacity/ section for how each
# was derived): L1=32768 B (best-guess), L2=1310720 B (reasoned --
# NOT independently confirmed this pass, no visible L2 knee in the capacity
# sweep), LLC=25874000 B / ~24.68 MiB (confirmed edge; the LLC->DRAM
# climb first clearly departs the plateau). Candidate strides left blank
# (auto skip of Method A step 4) -- no prior run to pick a candidate from.
#
#SBATCH --job-name=hw1_line_size
#SBATCH --output=data_raw/hazel_icelake_6326/hw1_icelake_6326_line_size_%j.log
#SBATCH --error=data_raw/hazel_icelake_6326/hw1_icelake_6326_line_size_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=icelake_6326

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
HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_icelake_6326 "${CORE:-0}" 32768,1310720,25874000

echo
echo "=== Done ==="
