#!/bin/bash
#
# hw1_sapphirerapids_miss_latency.sh -- Phase-I miss/next-level-latency experiment,
# sapphirerapids generation, via scripts/run_miss_latency_full.sh (HAZEL_MODE=1).
# Same boundary values as the other sapphirerapids experiments (see
# data_raw/hazel_sapphirerapids/README.md's capacity/ section). Three transitions,
# matching this project's <SOURCE>_to_<DEST> naming convention:
#   L1_to_L2:    target inside L1 (32768),   evict past L1, inside L2 (262144)
#   L2_to_LLC:   target inside L2 (262144),  evict past L2, inside LLC (25165824)
#   LLC_to_DRAM: target inside LLC (25165824), evict past LLC, into DRAM (536870912)
# inclusion_policy's calibration (a later, separate job) depends on this
# job's raw output -- must complete first.
#
#SBATCH --job-name=hw1_miss_latency
#SBATCH --output=data_raw/hazel_sapphirerapids/hw1_sapphirerapids_miss_latency_%j.log
#SBATCH --error=data_raw/hazel_sapphirerapids/hw1_sapphirerapids_miss_latency_%j.err.log
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

echo "=== Running scripts/run_miss_latency_full.sh (HAZEL_MODE=1) ==="
HAZEL_MODE=1 ./scripts/run_miss_latency_full.sh hazel_sapphirerapids "${CORE:-0}" \
  L1_to_L2:49152:2097152,L2_to_LLC:2097152:39903168,LLC_to_DRAM:39903168:536870912

echo
echo "=== Done ==="
