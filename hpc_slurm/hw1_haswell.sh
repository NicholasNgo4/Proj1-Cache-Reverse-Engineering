#!/bin/bash
#
# hw1_haswell.sh -- Phase III Hazel pilot job, haswell generation.
#
# THIS JOB IS AN ACCESS/BUILD CHECK, NOT THE FULL CACHE SUITE. It identifies
# the allocated node (whitelisted commands only, per README.md's Phase
# Discipline: hostname, uname -a, /proc/cpuinfo model name, lscpu -e core
# topology -- no full lscpu, no cpuid, no cache-size fields), builds
# cache_bench, and runs one tiny --experiment capacity smoke test under
# `srun --cpu-bind=cores` to prove the binary runs correctly bound to a real
# core on a Hazel compute node. Do NOT run taskset here -- that's the lab
# machines' pinning method (see scripts/run_capacity_sweep.sh's header);
# on Hazel, --cpu-bind=cores does the pinning.
#
# The real 1,000,000-sample cache-reverse-engineering suite is gated behind
# a runtime check for the predictions-frozen git tag (see below) -- this
# encodes README.md's Phase Discipline rule 3 as code instead of relying on
# a human remembering to check PREDICTION_FREEZE.md before every run.
#
#SBATCH --job-name=hw1_cache
#SBATCH --output=data_raw/hazel_haswell/hw1_haswell_%j.log
#SBATCH --error=data_raw/hazel_haswell/hw1_haswell_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=haswell

set -euo pipefail

echo "=== Machine identification (Phase Discipline whitelist only) ==="
hostname
uname -a
grep -m1 -E 'model name|Hardware|Processor' /proc/cpuinfo
lscpu -e=CPU,CORE,SOCKET,NODE
echo
echo "=== Slurm job context ==="
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-unset}"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "SLURM_CPUS_ON_NODE=${SLURM_CPUS_ON_NODE:-unset}"
echo "SLURM_JOB_CONSTRAINT (feature match)=${SLURM_JOB_CONSTRAINT:-haswell}"
if command -v numactl >/dev/null 2>&1; then
  numactl -s || true
else
  echo "numactl not available; NUMA node info from lscpu -e above"
fi
echo
echo "=== Toolchain ==="
gcc --version | head -1
echo
echo "=== Benchmark commit ==="
BENCH_COMMIT=$(git rev-parse HEAD)
echo "cache_bench git commit: ${BENCH_COMMIT}"
echo
echo "=== Build ==="
make clean
make
echo
echo "=== Smoke test: srun --cpu-bind=cores ./cache_bench (tiny capacity probe) ==="
srun --cpu-bind=cores ./cache_bench --experiment capacity \
  --min-bytes 4096 --max-bytes 65536 --samples 1000

echo
echo "=== Phase Discipline gate check: is HEAD tagged predictions-frozen? ==="
if git tag --points-at HEAD | grep -q '^predictions-frozen$'; then
  echo "HEAD is tagged predictions-frozen -- real cache-suite runs are permitted"
  echo "from a separate, dedicated job script once the full-suite pipeline is built."
else
  echo "HEAD is NOT tagged predictions-frozen -- this job intentionally stops"
  echo "after the smoke test. No cache-reverse-engineering suite may run yet."
fi

echo
echo "=== Done ==="
