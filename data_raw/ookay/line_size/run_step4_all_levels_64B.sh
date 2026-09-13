#!/bin/bash
# Ad hoc: run Method-A step 4 (bracket + offset refinement) for all 3 Ookay
# levels at a user-specified candidate stride of 64B, mirroring
# run_line_size.sh's own step-4 block exactly (same constants), without
# redoing steps 1-3 or Method B (already done and unchanged).
set -euo pipefail

MACHINE=ookay
CORE=2
SAMPLES=1000000
BATCH=1000
SEED=12345
ALIGN_BYTES=4096
MIN_BYTES_FLOOR=1024
MAX_BYTES_CEILING=268435456
WINDOW_LO_DIVISOR=8
WINDOW_HI_MULT=4
POINTS_PER_OCTAVE=6
WARMUP_A=2
BRACKET_STEP=8
OFFSET_SPAN=64
CANDIDATE=64

RAW_DIR="data_raw/${MACHINE}/line_size"
PROC_DIR="data_processed/${MACHINE}/line_size"

compute_bracket() {
  local c=$1 step=$2
  local vals=() v
  for v in $((c - 3 * step)) $((c - 2 * step)) $((c - step)) "$c" \
           $((c + step)) $((c + 2 * step)) $((c + 3 * step)); do
    if [ "$v" -ge 8 ]; then vals+=("$v"); fi
  done
  printf '%s\n' "${vals[@]}" | sort -n -u | paste -sd, -
}

compute_offsets() {
  local step=$1 span=$2
  local vals=() o=0
  while [ "$o" -lt "$span" ]; do vals+=("$o"); o=$((o + step)); done
  printf '%s\n' "${vals[@]}" | sort -n -u | paste -sd, -
}

TS="$(date -u +%Y%m%dT%H%M%SZ)"
echo "== step4 all levels: machine=${MACHINE} core=${CORE} candidate=${CANDIDATE}B seed=${SEED} ts=${TS} =="

for BOUNDARY in 32768 262144 8388608; do
  LEVEL_MIN=$((BOUNDARY / WINDOW_LO_DIVISOR))
  if [ "$LEVEL_MIN" -lt "$MIN_BYTES_FLOOR" ]; then LEVEL_MIN=$MIN_BYTES_FLOOR; fi
  LEVEL_MAX=$((BOUNDARY * WINDOW_HI_MULT))
  if [ "$LEVEL_MAX" -gt "$MAX_BYTES_CEILING" ]; then LEVEL_MAX=$MAX_BYTES_CEILING; fi
  if [ "$LEVEL_MAX" -le "$LEVEL_MIN" ]; then LEVEL_MAX=$((LEVEL_MIN * 8)); fi

  RAW_LEVEL_DIR="${RAW_DIR}/level_${BOUNDARY}"
  PROC_LEVEL_DIR="${PROC_DIR}/level_${BOUNDARY}"
  PLOT_LEVEL_DIR="${PROC_LEVEL_DIR}/plots"
  mkdir -p "$RAW_LEVEL_DIR" "$PROC_LEVEL_DIR" "$PLOT_LEVEL_DIR"

  echo ""
  echo "############################################################"
  echo "## LEVEL boundary=${BOUNDARY}B -- step 4, candidate=${CANDIDATE}B, window=[${LEVEL_MIN},${LEVEL_MAX}]"
  echo "############################################################"

  BRACKET_CSV="$(compute_bracket "$CANDIDATE" "$BRACKET_STEP")"
  OFFSETS_CSV="$(compute_offsets "$BRACKET_STEP" "$OFFSET_SPAN")"
  echo "== bracket=${BRACKET_CSV}B offsets=${OFFSETS_CSV}B pattern=random =="

  IFS=',' read -ra BRACKET <<< "$BRACKET_CSV"
  IFS=',' read -ra OFFSETS <<< "$OFFSETS_CSV"

  REFINE_SUMMARIES=()
  for offset in "${OFFSETS[@]}"; do
    for stride in "${BRACKET[@]}"; do
      echo "-- [L${BOUNDARY} refine] stride=${stride}B offset=${offset}B pattern=random --"
      RAW="${RAW_LEVEL_DIR}/refine_${stride}_off${offset}_${TS}.csv"
      taskset -c "$CORE" ./cache_bench --experiment line_size_family \
        --stride "$stride" --min-bytes "$LEVEL_MIN" --max-bytes "$LEVEL_MAX" \
        --points-per-octave "$POINTS_PER_OCTAVE" --align-bytes "$ALIGN_BYTES" \
        --offset-bytes "$offset" \
        --samples "$SAMPLES" --batch-size "$BATCH" --warmup-passes "$WARMUP_A" \
        --seed "$SEED" --pattern random > "$RAW"
      echo "  wrote $(wc -l < "$RAW") lines -> $RAW"
      SUM="${PROC_LEVEL_DIR}/refine_${stride}_off${offset}_summary.csv"
      python3 scripts/summarize_raw.py "$RAW" -o "$SUM" >/dev/null
      REFINE_SUMMARIES+=("$SUM")
    done
  done

  echo "-- [L${BOUNDARY} step 4] generating cross-alignment confirmation plots --"
  python3 scripts/plot_line_size_offset.py \
    "${REFINE_SUMMARIES[@]}" \
    -o "$PLOT_LEVEL_DIR" --machine "$MACHINE" --candidate-stride "$CANDIDATE" \
    --title-suffix "(Phase I timing-only, level boundary=${BOUNDARY}B, step-4 alignment refinement)"
done

echo ""
echo "== step4 all levels DONE (ts=${TS}) =="
