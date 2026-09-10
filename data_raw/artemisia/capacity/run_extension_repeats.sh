#!/bin/bash
# Manual follow-up to run_capacity_full.sh: reproducibility repeats for
# (1) the 256MiB-1GiB tail-extension window (top plateau was still climbing
#     at the default 256MiB ceiling) and (2) the muddy 8-96MiB middle
#     transition window. Run under tmux so it survives independent of the
#     driving Claude Code session.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."

RAW_DIR="data_raw/artemisia/capacity"
PROC_DIR="data_processed/artemisia/capacity"
CORE=23
SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
PPO=48

echo "== repeats of 256MiB-1GiB tail-extension window (checking for genuine top plateau) =="
for r in 1 2; do
  TS="$(date -u +%Y%m%dT%H%M%SZ)"
  for pattern in random sequential; do
    OUT="${RAW_DIR}/capacity_denseExt2_rep${r}_${pattern}_${TS}.csv"
    taskset -c "$CORE" ./cache_bench --experiment capacity --pattern "$pattern" \
      --samples "$SAMPLES" --batch-size "$BATCH" \
      --min-bytes 268435456 --max-bytes 1073741824 --points-per-octave "$PPO" \
      --warmup-passes "$WARMUP" --seed "$SEED" > "$OUT"
    echo "  rep${r} wrote $(wc -l < "$OUT") lines -> $OUT"
    python3 scripts/summarize_raw.py "$OUT" -o "${PROC_DIR}/denseExt2_rep${r}_${pattern}_summary.csv" >/dev/null
  done
done

echo "== repeats of muddy 8MiB-96MiB middle-transition window =="
for r in 1 2; do
  TS="$(date -u +%Y%m%dT%H%M%SZ)"
  for pattern in random sequential; do
    OUT="${RAW_DIR}/capacity_denseMid_rep${r}_${pattern}_${TS}.csv"
    taskset -c "$CORE" ./cache_bench --experiment capacity --pattern "$pattern" \
      --samples "$SAMPLES" --batch-size "$BATCH" \
      --min-bytes 8388608 --max-bytes 100663296 --points-per-octave "$PPO" \
      --warmup-passes "$WARMUP" --seed "$SEED" > "$OUT"
    echo "  rep${r} wrote $(wc -l < "$OUT") lines -> $OUT"
    python3 scripts/summarize_raw.py "$OUT" -o "${PROC_DIR}/denseMid_rep${r}_${pattern}_summary.csv" >/dev/null
  done
done
echo "== EXTENSION_REPEATS_ALL_DONE =="
