#!/bin/bash
#
# hw1_broadwell_capacity.sh -- Phase-I capacity experiment, broadwell generation,
# full 1,000,000-sample pipeline (scripts/run_capacity_full.sh in
# HAZEL_MODE=1: srun --cpu-bind=cores instead of taskset, isolated per-job
# build). This is the first of several per-experiment jobs for this
# generation (capacity must run and its boundaries be reviewed before
# line_size/associativity/latency/inclusion_policy can run -- same
# discipline this project already follows on every lab machine, see
# CLAUDE.md's per-machine writeups). QOS `short` on compute_partners caps
# walltime at 2h, and this project's own experience on the lab machines
# ("roughly an hour per full sweep... anything covering ~100+ MiB working
# sets") means the full capacity+tail+repeats pipeline can plausibly
# approach that -- requesting time just under the cap rather than trying to
# fit everything (all 5 experiment types) into one job.
#
#SBATCH --job-name=hw1_capacity
#SBATCH --output=data_raw/hazel_broadwell/hw1_broadwell_capacity_%j.log
#SBATCH --error=data_raw/hazel_broadwell/hw1_broadwell_capacity_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=broadwell

set -euo pipefail

echo "=== Machine identification (Phase Discipline whitelist only) ==="
hostname
uname -a
grep -m1 -E 'model name|Hardware|Processor' /proc/cpuinfo
lscpu -e=CPU,CORE,SOCKET,NODE
CORE=$(numactl -s 2>/dev/null | awk '/physcpubind/{print $2}')
echo "Assigned logical CPU (physcpubind, informational -- srun --cpu-bind=cores does the real pinning): ${CORE:-unknown}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-unset}"
echo

echo "=== Phase Discipline gate check: is predictions-frozen an ancestor of HEAD? ==="
if ! git merge-base --is-ancestor predictions-frozen HEAD 2>/dev/null; then
  echo "predictions-frozen is NOT an ancestor of HEAD -- refusing to run the cache suite." >&2
  exit 1
fi
echo "OK -- predictions-frozen confirmed ancestor of HEAD, proceeding."
echo

source hpc_slurm/hazel_python_env.sh

echo "=== Running scripts/run_capacity_full.sh (HAZEL_MODE=1) ==="
HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_broadwell "${CORE:-0}"

echo
echo "=== Done ==="
