#!/bin/bash
#
# hw1_genoa_inclusion_policy.sh -- Phase-I inclusion/exclusion experiment,
# genoa generation, via scripts/run_inclusion_policy_full.sh (HAZEL_MODE=1).
# Same boundary values as the other genoa experiments (see
# data_raw/hazel_genoa/README.md's capacity/ section): L1=32768 B
# (confirmed), L2=262144 B (reasoned), LLC=25165824 B / 24 MiB (provisional).
# ASSUMED_LINE_SIZE_BYTES left at its default (64) -- genoa's own
# line_size/ result only produced an estimate at L1 (64 B, matches the
# frozen prediction); L2/LLC's Method B found no transition, so 64 B is
# the only measured value anywhere on this machine, not a blind carry-over.
#
# MUST run after this generation's miss_latency job completes -- the
# invalidated-transition calibration below reads miss_latency's own raw
# output for the matching transition name (see run_inclusion_policy_full.sh's
# header comment). Submit with a dependency on that job, e.g.:
#   sbatch --dependency=afterok:<miss_latency_job_id> \
#     hpc_slurm/hw1_genoa_inclusion_policy.sh
#
#SBATCH --job-name=hw1_inclusion_policy
#SBATCH --output=data_raw/hazel_genoa/hw1_genoa_inclusion_policy_%j.log
#SBATCH --error=data_raw/hazel_genoa/hw1_genoa_inclusion_policy_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=genoa

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

echo "=== Running scripts/run_inclusion_policy_full.sh (HAZEL_MODE=1) ==="
HAZEL_MODE=1 ./scripts/run_inclusion_policy_full.sh hazel_genoa "${CORE:-0}" \
  L1_vs_L2:32768:1048576:L1_to_L2,L2_vs_LLC:1048576:33554432:L2_to_LLC,L1_vs_LLC:32768:33554432:LLC_to_DRAM

echo
echo "=== Done ==="
