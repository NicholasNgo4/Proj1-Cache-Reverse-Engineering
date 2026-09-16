#!/bin/bash
#
# hw1_icelake_8358_miss_latency.sh -- Phase-I miss/next-level-latency experiment,
# icelake_8358 generation, via scripts/run_miss_latency_full.sh (HAZEL_MODE=1).
# Same boundary values as the other icelake_8358 experiments (see
# data_raw/hazel_icelake_8358/README.md's capacity/ section). Three transitions,
# matching this project's <SOURCE>_to_<DEST> naming convention:
#   L1_to_L2:    target inside L1 (32768),   evict past L1, inside L2 (262144)
#   L2_to_LLC:   target inside L2 (262144),  evict past L2, inside LLC (25165824)
#   LLC_to_DRAM: target inside LLC (25165824), evict past LLC, into DRAM (536870912)
# inclusion_policy's calibration (a later, separate job) depends on this
# job's raw output -- must complete first.
#
#SBATCH --job-name=hw1_miss_latency
#SBATCH --output=data_raw/hazel_icelake_8358/hw1_icelake_8358_miss_latency_%j.log
#SBATCH --error=data_raw/hazel_icelake_8358/hw1_icelake_8358_miss_latency_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
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

echo "=== Running scripts/run_miss_latency_full.sh (HAZEL_MODE=1) ==="
HAZEL_MODE=1 ./scripts/run_miss_latency_full.sh hazel_icelake_8358 "${CORE:-0}" \
  L1_to_L2:32768:1310720,L2_to_LLC:1310720:50331648,LLC_to_DRAM:50331648:536870912

echo
echo "=== Done ==="
