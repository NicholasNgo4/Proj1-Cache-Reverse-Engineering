#!/bin/bash
#
# run_line_size.sh -- the ONE line-size pipeline script (folds together what
# used to be run_line_size_family.sh + run_line_size_full.sh +
# run_line_size_sweep.sh). For each cache level given (from this machine's
# own already-established capacity-experiment boundaries), runs TWO
# independently-designed Phase-I methods and reports whether they agree:
#
#   Method A -- family of curves (PROJECT 1.pdf Figure 3 / "Example B"),
#   all 5 required steps, scoped to this level's own narrow footprint window:
#     1. Hold footprint and measurement method constant across every curve --
#        same pinned core, timer, samples, warm-up, alignment policy, and
#        repetition count for every stride/offset combination below.
#     2. Sweep only the byte stride s across an unbiased candidate list
#        (default 8/16/32/64/128/256B, the assignment's own example), using
#        the random pointer-chase order to defeat a stream/stride prefetcher.
#        sequential is run alongside purely as a prefetcher-sensitive control
#        curve and is never trusted alone for the inference.
#     3. Collect >=10^6 timed samples per (stride, footprint) point for every
#        candidate curve and plot them together -- one plot PER CACHE LEVEL,
#        not one plot spanning every level at once (see "why per level"
#        below).
#     4. Take a candidate stride for THIS LEVEL'S OWN WINDOW from the caller
#        (candidate_overrides_csv -- see below; no auto-detection, the user
#        inspects line_size_family_curve.png and decides), then RE-TEST it:
#        bracket it with strides just below/at/above it at 8-byte granularity, and
#        repeat the whole bracketed sweep at a fixed 0/8/16/24/32/40/48/56B
#        span of node-0 offsets past the aligned buffer base (--offset-bytes)
#        to confirm the transition is a genuine hardware property and not an
#        artifact of always starting every node at the same position
#        relative to a physical line.
#
#   Method B -- single curve, ramp-saturation (the older, independently-
#   designed method): hold working-set footprint FIXED at ~2x this level's
#   boundary, sweep byte stride linearly, and read the line size off where
#   the resulting ramp SATURATES (scripts/detect_line_size.py) -- coarse
#   sweep -> dense bracket around the detected estimate -> 2 independent
#   repeats -> plots.
#
#   Step 5 (both methods, every level): print a combined agreement table.
#   Two independently-designed methods landing on the same number, at the
#   same cache level, is much stronger Phase-I evidence than either alone;
#   freeze the result and print an explicit reminder that comparing against
#   PMU counters and the documented/system-reported line size is Phase II.
#
# Why per level, not one global sweep (Method A): a single elbow detector run
# across the ENTIRE footprint range will lock onto whichever transition
# crosses its threshold FIRST -- on a real machine that's often a small,
# early bump near the L1 boundary, even when a much more dramatic stride-
# dependent separation exists later near L2/L3. Running each known capacity-
# level boundary through its own narrow, independent footprint window (rather
# than 1 KiB-256 MiB+ in one shot) stops one level's transition from masking
# or being mistaken for another's.
#
# The boundaries themselves MUST come from this machine's own capacity
# experiment (data_raw/<machine>/capacity/, data_processed/<machine>/
# capacity/) -- this script does not guess them or read them from sysfs
# (Phase I stays a timing-only, blind measurement; sysfs/documented specs
# are for the Phase II comparison, not for steering Phase I). Look up your
# machine's own boundaries in data_raw/<machine>/README.md's capacity/
# section (the `--boundary` values already passed to plot_capacity.py) and
# pass them here explicitly.
#
# Why 8-byte bracket granularity in Method A step 4: struct node
# (main_code/common/pointer_chase.h) is exactly one 8-byte pointer, so nodes
# cannot be spaced closer than 8 bytes apart without overlapping in memory --
# 8 bytes is the finest granularity "just below/at/above the candidate" can
# even mean. It also evenly divides every realistic line-size candidate
# (32/64/128B), so the bracket lands exactly on/around those values.
#
# Why a fixed 0-56B offset span (not scaled to the candidate): a small/wrong
# candidate would otherwise shrink the tested offsets to a few bytes, far
# too fine to probe a different position relative to a real physical line
# (essentially always >=32B on any real machine); a fixed span covering one
# full period of the most common real line size (64B) means the same thing
# regardless of which candidate is being refined.
#
# A per-offset elbow-vs-stride plot only shows a MARKER at strides where that
# offset actually produced a detectable elbow within the level's window --
# gaps are real gaps (drawn as NaN, so the line breaks), never silently
# bridged across missing measurements. The printed step-4 verdict states
# how many of the tested offsets actually reported a value before citing a
# spread across them -- "all offsets agree" is only trustworthy once you've
# checked how many offsets that claim actually covers.
#
# Usage:
#   ./scripts/run_line_size.sh <machine> <core> <boundaries_csv> [coarse_strides_csv] [candidate_overrides_csv]
#
# boundaries_csv: comma-separated capacity-level boundaries in bytes, from
#   THIS machine's own capacity experiment (see data_raw/<machine>/
#   README.md's capacity/ section). No default -- pick these deliberately,
#   don't guess.
# candidate_overrides_csv: same length as boundaries_csv; a number forces
#   that level's Method-A step-4 candidate stride. Leaving a field blank (or
#   "auto") SKIPS Method-A step 4 for that level -- there is no auto-detection
#   here: an earlier version picked the candidate itself from the coarse
#   pass's own elbow inference, but that single, un-repeated 6-points/octave
#   sweep proved unstable across independent runs/cores (see
#   data_raw/sunbird/README.md's line_size/ section, and CLAUDE.md) --
#   sometimes agreeing with its own step-4 offset check while still not
#   being the true line size, because a bracket entirely below the true line
#   size can look alignment-independent for the wrong reason (packing
#   multiple nodes per line is roughly offset-insensitive there too). Inspect
#   this level's own data_processed/<machine>/line_size/level_<boundary>/
#   plots/line_size_family_curve.png (steps 1-3 always run regardless of
#   whether a candidate is supplied) and pick the candidate yourself, then
#   re-run with it filled in. Method B always auto-detects independently
#   (ramp-saturation off a single coarse sweep, not the same failure mode) --
#   not affected by this.
#
# Example (Sunbird's own established L1/mid/plateau boundaries, ~32 KiB /
# ~20 MiB / ~150 MiB -- see data_raw/sunbird/README.md's capacity/ section):
#   ./scripts/run_line_size.sh sunbird 2 32768,20971520,157286400
#   # after inspecting each level's line_size_family_curve.png:
#   ./scripts/run_line_size.sh sunbird 2 32768,20971520,157286400 8,16,32,64,128,256 64,,32
#
# Output (per level, keyed by its boundary in bytes):
#   data_raw/<machine>/line_size/level_<boundary>/family_<stride>_<pattern>_<ts>.csv        (A, steps 1-3)
#   data_raw/<machine>/line_size/level_<boundary>/refine_<stride>_off<offset>_<ts>.csv       (A, step 4)
#   data_raw/<machine>/line_size/level_<boundary>/singlecurve_{coarse,dense,dense_rep1,dense_rep2}_{random,sequential}_<ts>.csv   (B)
#   data_processed/<machine>/line_size/level_<boundary>/family_<stride>_<pattern>_summary.csv
#   data_processed/<machine>/line_size/level_<boundary>/refine_<stride>_off<offset>_summary.csv
#   data_processed/<machine>/line_size/level_<boundary>/singlecurve_*_summary.csv
#   data_processed/<machine>/line_size/level_<boundary>/plots/line_size_family_{curve,boxplots}.{png,pdf}     (A)
#   data_processed/<machine>/line_size/level_<boundary>/plots/line_size_offset_{elbow,boxplots}.{png,pdf}     (A, step 4)
#   data_processed/<machine>/line_size/level_<boundary>/plots/line_size_curve.{png,pdf}, line_size_boxplots.{png,pdf}   (B)
#   data_raw/<machine>/line_size/run_line_size_<ts>.log   full transcript, all levels, both methods
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <boundaries_csv> [coarse_strides_csv] [candidate_overrides_csv]" >&2
  echo "  boundaries_csv: comma-separated capacity-level boundaries in bytes," >&2
  echo "  from this machine's OWN capacity experiment -- see" >&2
  echo "  data_raw/<machine>/README.md's capacity/ section. No default." >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
BOUNDARIES_CSV="$3"
STRIDES_CSV="${4:-8,16,32,64,128,256}"
CANDIDATE_OVERRIDES_CSV="${5:-}"

# ---- shared method constants ----
SAMPLES=1000000
BATCH=1000
SEED=12345
ALIGN_BYTES=4096

# ---- Method A (family of curves) constants ----
MIN_BYTES_FLOOR=1024
MAX_BYTES_CEILING=268435456    # 256 MiB -- keeps a deep/DRAM-adjacent level's
                                # window from running away to GiB-scale random-
                                # pattern sweeps (see README.md's tmux/wall-time
                                # notes); the transition itself sits well inside
                                # this even for a boundary near 150 MiB.
WINDOW_LO_DIVISOR=8             # level window = [boundary/8, boundary*4], so
WINDOW_HI_MULT=4                # each level sees a flat baseline on both sides
                                 # of its own transition, not just the elbow.
POINTS_PER_OCTAVE=6
WARMUP_A=2
BRACKET_STEP=8       # see header comment: finest granularity structurally possible
OFFSET_SPAN=64        # see header comment: fixed span, not scaled to candidate

# ---- Method B (single curve, ramp-saturation) constants ----
FOOTPRINT_MULTIPLIER=2.0   # footprint_bytes = ceil(boundary * MULTIPLIER) -- needs
                           # to leave several dense-sweep plateau points between the
                           # line-size knee and the capacity-driven fall-off (see
                           # scripts/detect_line_size.py's docstring); 1.2-1.5x left
                           # too few clean points on Sunbird, 2.0x reliably works.
MIN_STRIDE_B=8
MAX_STRIDE_B=1024
STRIDE_STEP_COARSE_B=8
STRIDE_STEP_DENSE_B=1
WARMUP_B=3
REPEATS_B=2

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_DIR="data_raw/${MACHINE}/line_size"
PROC_DIR="data_processed/${MACHINE}/line_size"
mkdir -p "$RAW_DIR" "$PROC_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_DIR}/run_line_size_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_line_size: machine=${MACHINE} core=${CORE} seed=${SEED} =="
echo "== timestamp=${TS} boundaries=${BOUNDARIES_CSV} coarse_strides=${STRIDES_CSV} =="

make -s

compute_bracket() {
  local c=$1 step=$2
  local vals=()
  local v
  for v in $((c - 3 * step)) $((c - 2 * step)) $((c - step)) "$c" \
           $((c + step)) $((c + 2 * step)) $((c + 3 * step)); do
    if [ "$v" -ge 8 ]; then
      vals+=("$v")
    fi
  done
  printf '%s\n' "${vals[@]}" | sort -n -u | paste -sd, -
}

compute_offsets() {
  local step=$1 span=$2
  local vals=()
  local o=0
  while [ "$o" -lt "$span" ]; do
    vals+=("$o")
    o=$((o + step))
  done
  printf '%s\n' "${vals[@]}" | sort -n -u | paste -sd, -
}

run_sweep_b() {
  # run_sweep_b <footprint> <pattern> <min_stride> <max_stride> <step> <out_csv>
  local footprint="$1" pattern="$2" min="$3" max="$4" step="$5" out="$6"
  taskset -c "$CORE" ./cache_bench --experiment line_size --pattern "$pattern" \
    --samples "$SAMPLES" --batch-size "$BATCH" \
    --footprint-bytes "$footprint" --min-stride "$min" --max-stride "$max" \
    --stride-step "$step" --align-bytes "$ALIGN_BYTES" \
    --warmup-passes "$WARMUP_B" --seed "$SEED" > "$out"
  echo "  wrote $(wc -l < "$out") lines -> $out"
}

IFS=',' read -ra BOUNDARIES <<< "$BOUNDARIES_CSV"
IFS=',' read -ra STRIDES <<< "$STRIDES_CSV"
OVERRIDES=()
if [ -n "$CANDIDATE_OVERRIDES_CSV" ]; then
  IFS=',' read -ra OVERRIDES <<< "$CANDIDATE_OVERRIDES_CSV"
fi

LEVEL_ESTIMATES_A=()   # "boundary:estimate" pairs, Method A
LEVEL_ESTIMATES_B=()   # "boundary:estimate" pairs, Method B

for idx in "${!BOUNDARIES[@]}"; do
  BOUNDARY="${BOUNDARIES[$idx]}"
  OVERRIDE="${OVERRIDES[$idx]:-}"
  if [ "$OVERRIDE" = "auto" ]; then OVERRIDE=""; fi

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
  echo "## LEVEL boundary=${BOUNDARY}B -- Method A window=[${LEVEL_MIN},${LEVEL_MAX}] bytes"
  echo "############################################################"

  ### Method A, steps 1-3: coarse family-of-curves pass for this level only ###
  COARSE_SUMMARIES=()
  for stride in "${STRIDES[@]}"; do
    for pattern in random sequential; do
      echo "-- [L${BOUNDARY} A coarse] stride=${stride}B pattern=${pattern} offset=0B --"
      RAW="${RAW_LEVEL_DIR}/family_${stride}_${pattern}_${TS}.csv"
      taskset -c "$CORE" ./cache_bench --experiment line_size_family \
        --stride "$stride" --min-bytes "$LEVEL_MIN" --max-bytes "$LEVEL_MAX" \
        --points-per-octave "$POINTS_PER_OCTAVE" --align-bytes "$ALIGN_BYTES" \
        --offset-bytes 0 \
        --samples "$SAMPLES" --batch-size "$BATCH" --warmup-passes "$WARMUP_A" \
        --seed "$SEED" --pattern "$pattern" > "$RAW"
      echo "  wrote $(wc -l < "$RAW") lines -> $RAW"
      SUM="${PROC_LEVEL_DIR}/family_${stride}_${pattern}_summary.csv"
      python3 scripts/summarize_raw.py "$RAW" -o "$SUM" >/dev/null
      COARSE_SUMMARIES+=("$SUM")
    done
  done

  echo "-- [L${BOUNDARY} A steps 1-3] generating coarse family-of-curves plots --"
  python3 scripts/plot_line_size_family.py \
    "${COARSE_SUMMARIES[@]}" \
    -o "$PLOT_LEVEL_DIR" --machine "$MACHINE" \
    --title-suffix "(Phase I timing-only, level boundary=${BOUNDARY}B window=[${LEVEL_MIN},${LEVEL_MAX}])"
  echo "   (the per-stride elbow / line-size-estimate lines just above are"
  echo "   plot_line_size_family.py's own diagnostic guess from ONE un-repeated coarse"
  echo "   sweep -- NOT auto-applied below; see ${PLOT_LEVEL_DIR}/line_size_family_curve.png"
  echo "   and decide the step-4 candidate yourself)"

  if [ -n "$OVERRIDE" ]; then
    CANDIDATE="$OVERRIDE"
    echo "== [L${BOUNDARY} A step 4] candidate=${CANDIDATE}B (manual, from line_size_family_curve.png) =="
  else
    echo "== [L${BOUNDARY} A] no candidate given for this level -- inspect" >&2
    echo "   ${PLOT_LEVEL_DIR}/line_size_family_curve.png yourself and re-run with an" >&2
    echo "   explicit candidate stride in candidate_overrides_csv for this level (no" >&2
    echo "   auto-detection: it proved unreliable across runs/cores, see the script's" >&2
    echo "   header comment). Skipping Method-A step 4." >&2
    LEVEL_ESTIMATES_A+=("${BOUNDARY}:none")
    CANDIDATE=""
  fi
  if [ -n "$CANDIDATE" ]; then
    if ! [[ "$CANDIDATE" =~ ^[0-9]+$ ]] || [ "$CANDIDATE" -lt 8 ]; then
      echo "candidate stride must be an integer >= 8 (got '$CANDIDATE') for level ${BOUNDARY}" >&2
      exit 1
    fi

    ### Method A, step 4: bracket the candidate + repeat at several node-0 offsets ###
    BRACKET_CSV="$(compute_bracket "$CANDIDATE" "$BRACKET_STEP")"
    OFFSETS_CSV="$(compute_offsets "$BRACKET_STEP" "$OFFSET_SPAN")"
    echo "== [L${BOUNDARY} A step 4] bracket=${BRACKET_CSV}B (8B granularity) offsets=${OFFSETS_CSV}B pattern=random =="

    IFS=',' read -ra BRACKET <<< "$BRACKET_CSV"
    IFS=',' read -ra OFFSETS <<< "$OFFSETS_CSV"

    REFINE_SUMMARIES=()
    for offset in "${OFFSETS[@]}"; do
      for stride in "${BRACKET[@]}"; do
        echo "-- [L${BOUNDARY} A refine] stride=${stride}B offset=${offset}B pattern=random --"
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

    echo "-- [L${BOUNDARY} A step 4] generating cross-alignment confirmation plots --"
    python3 scripts/plot_line_size_offset.py \
      "${REFINE_SUMMARIES[@]}" \
      -o "$PLOT_LEVEL_DIR" --machine "$MACHINE" --candidate-stride "$CANDIDATE" \
      --title-suffix "(Phase I timing-only, level boundary=${BOUNDARY}B, step-4 alignment refinement)"

    LEVEL_ESTIMATES_A+=("${BOUNDARY}:${CANDIDATE}")
  fi

  ### Method B: single-curve ramp-saturation at footprint ~= boundary * MULTIPLIER ###
  FOOTPRINT_BYTES=$(python3 -c "import math; print(math.ceil(${BOUNDARY} * ${FOOTPRINT_MULTIPLIER}))")
  echo ""
  echo "-- [L${BOUNDARY} B] single-curve method, footprint_bytes=${FOOTPRINT_BYTES} (${FOOTPRINT_MULTIPLIER}x boundary) --"

  B_SUMMARIES=()
  echo "-- [L${BOUNDARY} B coarse] stride ${MIN_STRIDE_B}-${MAX_STRIDE_B} bytes (step ${STRIDE_STEP_COARSE_B}) --"
  BCOARSE_R="${RAW_LEVEL_DIR}/singlecurve_coarse_random_${TS}.csv"
  BCOARSE_S="${RAW_LEVEL_DIR}/singlecurve_coarse_sequential_${TS}.csv"
  run_sweep_b "$FOOTPRINT_BYTES" random "$MIN_STRIDE_B" "$MAX_STRIDE_B" "$STRIDE_STEP_COARSE_B" "$BCOARSE_R"
  run_sweep_b "$FOOTPRINT_BYTES" sequential "$MIN_STRIDE_B" "$MAX_STRIDE_B" "$STRIDE_STEP_COARSE_B" "$BCOARSE_S"
  BCOARSE_R_SUM="${PROC_LEVEL_DIR}/singlecurve_coarse_random_summary.csv"
  BCOARSE_S_SUM="${PROC_LEVEL_DIR}/singlecurve_coarse_sequential_summary.csv"
  python3 scripts/summarize_raw.py "$BCOARSE_R" -o "$BCOARSE_R_SUM" >/dev/null
  python3 scripts/summarize_raw.py "$BCOARSE_S" -o "$BCOARSE_S_SUM" >/dev/null
  B_SUMMARIES+=("$BCOARSE_R_SUM" "$BCOARSE_S_SUM")

  mapfile -t B_ESTIMATE_ARR < <(python3 scripts/detect_line_size.py "$BCOARSE_R_SUM" --machine-readable 2>/dev/null || true)
  B_ESTIMATE="${B_ESTIMATE_ARR[0]:-}"
  echo "-- [L${BOUNDARY} B] detected line-size estimate (bytes): ${B_ESTIMATE:-none} --"

  B_PLOT_BOUNDARY_ARGS=()
  if [ -n "$B_ESTIMATE" ]; then
    BDMIN=$(python3 -c "print(max(${MIN_STRIDE_B}, int(${B_ESTIMATE} / 2)))")
    BDMAX=$(python3 -c "print(min(${MAX_STRIDE_B}, int(${B_ESTIMATE} * 2) + 1))")
    if [ "$BDMAX" -le "$BDMIN" ]; then
      echo "-- [L${BOUNDARY} B] skipping dense sweep (degenerate range ${BDMIN}-${BDMAX}) --"
    else
      echo "-- [L${BOUNDARY} B] dense sweep around estimate ${B_ESTIMATE} bytes: ${BDMIN}-${BDMAX} (step ${STRIDE_STEP_DENSE_B}) --"
      BDR="${RAW_LEVEL_DIR}/singlecurve_dense_random_${TS}.csv"
      BDS="${RAW_LEVEL_DIR}/singlecurve_dense_sequential_${TS}.csv"
      run_sweep_b "$FOOTPRINT_BYTES" random "$BDMIN" "$BDMAX" "$STRIDE_STEP_DENSE_B" "$BDR"
      run_sweep_b "$FOOTPRINT_BYTES" sequential "$BDMIN" "$BDMAX" "$STRIDE_STEP_DENSE_B" "$BDS"
      BDR_SUM="${PROC_LEVEL_DIR}/singlecurve_dense_random_summary.csv"
      BDS_SUM="${PROC_LEVEL_DIR}/singlecurve_dense_sequential_summary.csv"
      python3 scripts/summarize_raw.py "$BDR" -o "$BDR_SUM" >/dev/null
      python3 scripts/summarize_raw.py "$BDS" -o "$BDS_SUM" >/dev/null
      B_SUMMARIES+=("$BDR_SUM" "$BDS_SUM")

      for r in $(seq 1 "$REPEATS_B"); do
        echo "  -- [L${BOUNDARY} B] repeat ${r}/${REPEATS_B} of the dense window --"
        BRR="${RAW_LEVEL_DIR}/singlecurve_dense_rep${r}_random_${TS}.csv"
        BRS="${RAW_LEVEL_DIR}/singlecurve_dense_rep${r}_sequential_${TS}.csv"
        run_sweep_b "$FOOTPRINT_BYTES" random "$BDMIN" "$BDMAX" "$STRIDE_STEP_DENSE_B" "$BRR"
        run_sweep_b "$FOOTPRINT_BYTES" sequential "$BDMIN" "$BDMAX" "$STRIDE_STEP_DENSE_B" "$BRS"
        BRR_SUM="${PROC_LEVEL_DIR}/singlecurve_dense_rep${r}_random_summary.csv"
        BRS_SUM="${PROC_LEVEL_DIR}/singlecurve_dense_rep${r}_sequential_summary.csv"
        python3 scripts/summarize_raw.py "$BRR" -o "$BRR_SUM" >/dev/null
        python3 scripts/summarize_raw.py "$BRS" -o "$BRS_SUM" >/dev/null
        B_SUMMARIES+=("$BRR_SUM" "$BRS_SUM")
      done
    fi
    B_PLOT_BOUNDARY_ARGS=(--boundary "$B_ESTIMATE")
  else
    echo "-- [L${BOUNDARY} B] no transition detected in the coarse sweep; skipping dense/repeat stages --"
  fi

  echo "-- [L${BOUNDARY} B] generating single-curve plots --"
  python3 scripts/plot_line_size.py \
    "${B_SUMMARIES[@]}" \
    -o "$PLOT_LEVEL_DIR" --machine "$MACHINE" \
    --title-suffix "(Phase I timing-only, level boundary=${BOUNDARY}B, single-curve method)" \
    "${B_PLOT_BOUNDARY_ARGS[@]}"

  LEVEL_ESTIMATES_B+=("${BOUNDARY}:${B_ESTIMATE:-none}")
done

### Step 5: infer, freeze, cross-level AND cross-method agreement, remind about Phase II ###
echo ""
echo "############################################################"
echo "## step 5: cross-level, cross-method agreement summary"
echo "############################################################"
ALL_KNOWN=()
for i in "${!BOUNDARIES[@]}"; do
  BOUNDARY="${BOUNDARIES[$i]}"
  a="${LEVEL_ESTIMATES_A[$i]##*:}"
  b="${LEVEL_ESTIMATES_B[$i]##*:}"
  echo "   level boundary=${BOUNDARY}B -> method A (family of curves) = ${a}B, method B (single curve) = ${b}B"
  [ "$a" != "none" ] && ALL_KNOWN+=("$a")
  [ "$b" != "none" ] && ALL_KNOWN+=("$b")
done
ALL_SORTED="$(printf '%s\n' "${ALL_KNOWN[@]}" | sort -n -u | paste -sd, -)"
N_UNIQUE="$(printf '%s\n' "${ALL_KNOWN[@]}" | sort -n -u | wc -l)"
if [ "$N_UNIQUE" -le 1 ] && [ -n "$ALL_SORTED" ]; then
  echo "== every level/method that produced an estimate AGREES on ${ALL_SORTED}B -- strong Phase-I evidence =="
elif [ -n "$ALL_SORTED" ]; then
  echo "== estimates DISAGREE (distinct values seen: ${ALL_SORTED}) -- do not average these into" >&2
  echo "   one number; report the disagreement itself and investigate per-level/per-method before Phase II" >&2
else
  echo "== no level/method produced a usable estimate -- widen windows or strides before citing anything" >&2
fi

echo "== done: all levels, both methods, complete =="
echo "== this is a FROZEN PHASE-I TIMING-ONLY result -- compare against PMU counters"
echo "   and the documented/system-reported line size in Phase II before treating it as"
echo "   confirmed (see README.md's Phase I/II/III discipline)."
echo "== plots per level: data_processed/${MACHINE}/line_size/level_<boundary>/plots/line_size_family_{curve,boxplots}.{png,pdf} (A, steps 1-3),"
echo "          .../line_size_offset_{elbow,boxplots}.{png,pdf} (A, step 4), .../line_size_{curve,boxplots}.{png,pdf} (B) =="
echo "== record in data_raw/${MACHINE}/README.md: boundaries=${BOUNDARIES_CSV}, core=${CORE},"
echo "   seed=${SEED}, samples=${SAMPLES}, coarse_strides=${STRIDES_CSV}, per-level/per-method estimates as above,"
echo "   timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
