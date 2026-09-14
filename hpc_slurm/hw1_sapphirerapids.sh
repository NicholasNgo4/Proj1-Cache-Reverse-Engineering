#!/bin/bash
#
# hw1_sapphirerapids.sh -- Phase III Hazel pilot job, sapphirerapids generation.
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
# Builds in a PER-JOB, isolated directory (hazel_build/$SLURM_JOB_ID/, a
# throwaway copy of main_code/+Makefile, cleaned up on exit) rather than the
# shared repo checkout -- this script is meant to be submitted for every
# generation in Table 4, and several of these jobs may land in the RUNNING
# state at the same time; a `make clean && make` running directly in the
# shared checkout races across concurrent jobs (confirmed the hard way: a
# same-batch submission of 8 of these sister scripts produced a missing-.o
# link failure on one job and cannot be trusted not to have silently
# corrupted a "successful" build on another -- see data_raw/hazel_turin/
# README.md). Do not remove this isolation to "simplify" the script.
#
# The real 1,000,000-sample cache-reverse-engineering suite is gated behind
# a runtime check for the predictions-frozen git tag (see below) -- this
# encodes README.md's Phase Discipline rule 3 as code instead of relying on
# a human remembering to check PREDICTION_FREEZE.md before every run. The
# check is an ANCESTRY check (`git merge-base --is-ancestor`), not an exact
# HEAD-equality check -- the freeze remains valid for every commit made
# after the tag (e.g. this script itself), not just the exact tagged commit.
#
#SBATCH --job-name=hw1_cache
#SBATCH --output=data_raw/hazel_sapphirerapids/hw1_sapphirerapids_%j.log
#SBATCH --error=data_raw/hazel_sapphirerapids/hw1_sapphirerapids_%j.err.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --partition=compute_partners
#SBATCH --constraint=sapphirerapids

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
echo "SLURM_JOB_CONSTRAINT (feature match)=${SLURM_JOB_CONSTRAINT:-sapphirerapids}"
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
echo "=== Build (isolated per-job directory, avoids races with sibling jobs) ==="
REPO_ROOT="$(pwd)"
BUILD_DIR="${REPO_ROOT}/hazel_build/${SLURM_JOB_ID:-manual}"
cleanup() { rm -rf "${BUILD_DIR}"; }
trap cleanup EXIT
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"
cp -r main_code Makefile "${BUILD_DIR}/"
( cd "${BUILD_DIR}" && make )
echo
echo "=== Smoke test: srun --cpu-bind=cores ./cache_bench (tiny capacity probe) ==="
srun --cpu-bind=cores "${BUILD_DIR}/cache_bench" --experiment capacity \
  --min-bytes 4096 --max-bytes 65536 --samples 1000

echo
echo "=== Phase Discipline gate check: is predictions-frozen an ancestor of HEAD? ==="
if git merge-base --is-ancestor predictions-frozen HEAD 2>/dev/null; then
  echo "predictions-frozen is an ancestor of HEAD -- real cache-suite runs are permitted"
  echo "from a separate, dedicated job script once the full-suite pipeline is built."
else
  echo "predictions-frozen is NOT an ancestor of HEAD -- this job intentionally stops"
  echo "after the smoke test. No cache-reverse-engineering suite may run yet."
fi

echo
echo "=== Done ==="
