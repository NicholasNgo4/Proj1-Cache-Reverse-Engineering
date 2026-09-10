#!/bin/bash
# Full capacity-experiment redo on an idle core (20), superseding the
# original core-23 run which shared its socket with other students'
# processes (see data_processed/artemisia/capacity_prior_core23/ for the
# archived prior results and data_raw/artemisia/README.md for the
# documented anomalies that motivated this redo).
#
# Mirrors the original methodology exactly: primary pipeline via
# run_capacity_full.sh, then the same two manual follow-up windows
# (256 MiB-1 GiB tail extension, 8-96 MiB mid-transition) with 2
# independent repeats each, run under tmux so it survives disconnection.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."

RAW_DIR="data_raw/artemisia/capacity"
PROC_DIR="data_processed/artemisia/capacity"
CORE=20
SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
PPO=48

echo "== stage 1: primary pipeline (scripts/run_capacity_full.sh artemisia ${CORE}) =="
bash scripts/run_capacity_full.sh artemisia "$CORE"

echo "== stage 2: base 256MiB-1GiB tail-extension sweep (checking for a top plateau) =="
TS="$(date -u +%Y%m%dT%H%M%SZ)"
for pattern in random sequential; do
  OUT="${RAW_DIR}/capacity_denseExt2_${pattern}_${TS}.csv"
  taskset -c "$CORE" ./cache_bench --experiment capacity --pattern "$pattern" \
    --samples "$SAMPLES" --batch-size "$BATCH" \
    --min-bytes 268435456 --max-bytes 1073741824 --points-per-octave "$PPO" \
    --warmup-passes "$WARMUP" --seed "$SEED" > "$OUT"
  echo "  wrote $(wc -l < "$OUT") lines -> $OUT"
  python3 scripts/summarize_raw.py "$OUT" -o "${PROC_DIR}/denseExt2_${pattern}_summary.csv" >/dev/null
done

echo "== stage 3: repeats of 256MiB-1GiB tail-extension window =="
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

echo "== stage 4: repeats of 8MiB-96MiB middle-transition window =="
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

echo "== stage 5: regenerate combined plots =="
python3 scripts/plot_capacity.py ${PROC_DIR}/*_summary.csv \
  -o "${PROC_DIR}/plots" --machine artemisia \
  --title-suffix "(Phase I timing-only, auto pipeline + manual tail/mid extension repeats, core 20)" \
  --boundary 49152 --boundary 2097152 --boundary 94371840

echo "== FULL_REDO_CORE20_ALL_DONE =="
