#!/bin/bash
# Ad hoc follow-up script (not part of scripts/): redo the 2 reproducibility
# repeats on the 256MiB-1GiB tail-extension window, inside tmux so they
# survive a VSCode/remote-server restart. The main tail sweep (random +
# sequential + summaries) already completed and is untouched by this script.
set -euo pipefail
cd /home/nsngo/ECE592/Proj1-Cache-Reverse-Engineering

TS="20260909T001422Z"
RAW_DIR="data_raw/thunderbird/capacity"
PROC_DIR="data_processed/thunderbird/capacity"
CORE=3
SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
PPO_DENSE=48
TAIL_MAX=1073741824
MLOG="${RAW_DIR}/manual_followup_${TS}.log"

run_sweep() {
  local pattern="$1" min="$2" max="$3" ppo="$4" out="$5"
  taskset -c "$CORE" ./cache_bench --experiment capacity --pattern "$pattern" \
    --samples "$SAMPLES" --batch-size "$BATCH" \
    --min-bytes "$min" --max-bytes "$max" --points-per-octave "$ppo" \
    --warmup-passes "$WARMUP" --seed "$SEED" > "$out"
  echo "  wrote $(wc -l < "$out") lines -> $out"
}
summarize() { python3 scripts/summarize_raw.py "$1" -o "$2" >/dev/null; }

{
echo "== resumed under tmux (session: capbench) =="
for r in 1 2; do
  echo "  -- repeat ${r}/2 of tail-extension window (256MiB-${TAIL_MAX}) --"
  run_sweep random     268435456 "$TAIL_MAX" "$PPO_DENSE" "${RAW_DIR}/capacity_denseTail_rep${r}_random_${TS}.csv"
  run_sweep sequential 268435456 "$TAIL_MAX" "$PPO_DENSE" "${RAW_DIR}/capacity_denseTail_rep${r}_sequential_${TS}.csv"
  summarize "${RAW_DIR}/capacity_denseTail_rep${r}_random_${TS}.csv" "${PROC_DIR}/denseTail_rep${r}_random_summary.csv"
  summarize "${RAW_DIR}/capacity_denseTail_rep${r}_sequential_${TS}.csv" "${PROC_DIR}/denseTail_rep${r}_sequential_summary.csv"
done
echo "== ALL TAIL REPEATS DONE =="
} | tee -a "$MLOG"
