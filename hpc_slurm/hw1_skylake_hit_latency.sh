#!/bin/bash
#
# hw1_skylake_hit_latency.sh -- Phase-I hit-latency experiment, skylake
# generation, via scripts/run_hit_latency_full.sh (HAZEL_MODE=1). Same
# boundary values as line_size/associativity (see
# data_raw/hazel_skylake/README.md's capacity/ section): L1=32768 B
# (confirmed), L2=262144 B (reasoned), LLC=25165824 B / 24 MiB
# (provisional), DRAM=536870912 B / 512 MiB (matches every lab machine's
# own convention).
#
#SBATCH --job-name=hw1_hit_latency
#SBATCH --output=data_raw/hazel_skylake/hw1_skylake_hit_latency_%j.log
#SBATCH --error=data_raw/hazel_skylake/hw1_skylake_hit_latency_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=skylake

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

echo "=== Running scripts/run_hit_latency_full.sh (HAZEL_MODE=1) ==="
HAZEL_MODE=1 ./scripts/run_hit_latency_full.sh hazel_skylake "${CORE:-0}" \
  L1:32768,L2:1048576,LLC:23726560,DRAM:536870912

echo
echo "=== Done ==="
