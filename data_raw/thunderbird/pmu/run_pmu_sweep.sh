#!/bin/bash
# Phase II PMU corroboration sweep for Thunderbird.
#
# Independently checks the Phase-I timing-based capacity boundaries using
# armv8_pmuv3 raw hardware cache-miss counters instead of latency, by running
# the SAME cache_bench pointer-chase (capacity experiment, one size per
# invocation) under `perf stat`, sweeping working-set size across the L1/L2/
# (candidate LLC) region. Two perf stat calls per size (6 general-purpose
# PMUv3 counters on this core; 8 raw events requested total, so split into
# two groups of 4 to avoid multiplexing).
#
# Usage: ./run_pmu_sweep.sh <core> <output_csv>
set -euo pipefail
CORE="${1:-3}"
OUT="${2:-pmu_sweep_$(date -u +%Y%m%dT%H%M%SZ).csv}"
BIN=./cache_bench
SAMPLES=1000000
SEED=12345

SIZES=(4096 16384 32768 49152 65536 81920 98304 131072 262144 524288 \
       1048576 2097152 4194304 8388608 16777216 25165824 31457280 \
       37748736 50331648 67108864 134217728 268435456 536870912)

echo "size_bytes,l1d_cache,l1d_cache_refill,l2d_cache,l2d_cache_refill,l3d_cache,l3d_cache_refill,mem_access,bus_access,cache_references,cache_misses" > "$OUT"

for SZ in "${SIZES[@]}"; do
  echo "== size=$SZ ==" >&2

  # Group A: L1 + L2 raw events
  A=$(taskset -c "$CORE" perf stat -x, \
      -e armv8_pmuv3_0/l1d_cache/,armv8_pmuv3_0/l1d_cache_refill/,armv8_pmuv3_0/l2d_cache/,armv8_pmuv3_0/l2d_cache_refill/ \
      "$BIN" --experiment capacity --min-bytes "$SZ" --max-bytes "$SZ" --points-per-octave 1 \
      --samples "$SAMPLES" --pattern random --seed "$SEED" 2>&1 >/dev/null | grep -E '^[0-9]' || true)

  L1D=$(echo "$A"   | awk -F, '$3 ~ /^armv8_pmuv3_0\/l1d_cache\/u?$/{print $1}')
  L1DR=$(echo "$A"  | awk -F, '$3 ~ /^armv8_pmuv3_0\/l1d_cache_refill\/u?$/{print $1}')
  L2D=$(echo "$A"   | awk -F, '$3 ~ /^armv8_pmuv3_0\/l2d_cache\/u?$/{print $1}')
  L2DR=$(echo "$A"  | awk -F, '$3 ~ /^armv8_pmuv3_0\/l2d_cache_refill\/u?$/{print $1}')

  # Group B: L3 raw events + mem_access + bus_access
  B=$(taskset -c "$CORE" perf stat -x, \
      -e armv8_pmuv3_0/l3d_cache/,armv8_pmuv3_0/l3d_cache_refill/,armv8_pmuv3_0/mem_access/,armv8_pmuv3_0/bus_access/ \
      "$BIN" --experiment capacity --min-bytes "$SZ" --max-bytes "$SZ" --points-per-octave 1 \
      --samples "$SAMPLES" --pattern random --seed "$SEED" 2>&1 >/dev/null | grep -E '^[0-9]' || true)

  L3D=$(echo "$B"  | awk -F, '$3 ~ /^armv8_pmuv3_0\/l3d_cache\/u?$/{print $1}')
  L3DR=$(echo "$B" | awk -F, '$3 ~ /^armv8_pmuv3_0\/l3d_cache_refill\/u?$/{print $1}')
  MEM=$(echo "$B"  | awk -F, '$3 ~ /^armv8_pmuv3_0\/mem_access\/u?$/{print $1}')
  BUS=$(echo "$B"  | awk -F, '$3 ~ /^armv8_pmuv3_0\/bus_access\/u?$/{print $1}')

  # Group C: generic cache-references/cache-misses (perf's own mapping)
  C=$(taskset -c "$CORE" perf stat -x, -e cache-references,cache-misses \
      "$BIN" --experiment capacity --min-bytes "$SZ" --max-bytes "$SZ" --points-per-octave 1 \
      --samples "$SAMPLES" --pattern random --seed "$SEED" 2>&1 >/dev/null | grep -E '^[0-9]' || true)
  CREF=$(echo "$C"  | awk -F, '$3 ~ /^cache-references(:u)?$/{print $1}')
  CMISS=$(echo "$C" | awk -F, '$3 ~ /^cache-misses(:u)?$/{print $1}')

  echo "$SZ,$L1D,$L1DR,$L2D,$L2DR,$L3D,$L3DR,$MEM,$BUS,$CREF,$CMISS" >> "$OUT"
done

echo "Done. Wrote $OUT" >&2
