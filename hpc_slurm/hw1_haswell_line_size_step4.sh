#!/bin/bash
#
# hw1_haswell_line_size_step4.sh -- follow-up to hw1_haswell_line_size.sh
# (job 834508), which skipped Method-A step 4 (the offset-invariance
# confirmation re-test) at every level because it had no prior candidate
# stride to override with (see scripts/run_line_size.sh's own header
# comment for why step 4 requires an explicit candidate_overrides_csv
# rather than auto-picking one). This job forces the candidate to 64 B at
# ALL THREE levels (L1=32768, L2=262144, LLC=25165824 B) -- 64 B is the
# only line-size value this machine has produced anywhere so far (Method
# B's clean detection at L1; L2/LLC's own Method B found no transition at
# all), matching the frozen prediction and every x86 lab machine's own
# confirmed 64 B. This re-tests whether that same 64 B stride looks
# alignment-independent (line_size_offset_elbow/boxplots) at L2 and LLC
# too, not just L1.
#
#SBATCH --job-name=hw1_line_size_step4
#SBATCH --output=data_raw/hazel_haswell/hw1_haswell_line_size_step4_%j.log
#SBATCH --error=data_raw/hazel_haswell/hw1_haswell_line_size_step4_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=haswell

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

echo "=== Running scripts/run_line_size.sh (HAZEL_MODE=1), candidate=64B at all 3 levels ==="
HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_haswell "${CORE:-0}" \
  32768,262144,25165824 8,16,32,64,128,256 64,64,64

echo
echo "=== Done ==="
