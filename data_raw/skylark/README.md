# skylark — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: skylark.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): AMD EPYC 7532 32-Core Processor (x2 sockets, 64 logical CPUs total)
- ISA / architecture: x86_64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): AMD, Zen 2 ("Rome" server line) — TODO: confirm against team's MACHINE_RESEARCH.md convention, not filled in here to avoid duplicating/contradicting that table
- Introduction year (per the team's stated year convention): see MACHINE_RESEARCH.md
- Process node (if reliably documented): TODO
- Kernel version: 5.14.0-611.38.1.el9_7.x86_64
- Page size: 4096 bytes
- SMT siblings idle during runs? `lscpu` reports Thread(s) per core = 1 (SMT appears disabled machine-wide, not just for this run) — no sibling to idle/reserve

## Environment
- Compiler + version: gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-14)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): `main_code/x86_64/timer_x86.h` — LFENCE+RDTSC to start, RDTSCP+LFENCE to stop (serialized TSC read pair)
- Affinity/binding command used: `taskset -c 10` (see `scripts/run_capacity_full.sh`)
- NUMA/locality method: none explicit — no `numactl` pinning in the script, only `taskset -c 10`. Core 10 is on NUMA node0 (node0 = CPUs 0-31, node1 = CPUs 32-63) per `lscpu -e`; memory locality was not independently verified/pinned.
- Git commit hash of the code used for these results: 881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9 (main run, 2026-09-08 12:00:20 -0400) — NOTE: the manual tail-extension2 follow-up (see below) was run afterward against the same checkout; if any code changed between the two, re-check `git log` before treating this hash as covering all skylark capacity data.

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/capacity.c`, `main_code/common/main.c`, `main_code/x86_64/timer_x86.h`
- Build command: `make` (from repo root)
- Run command + arguments: `./scripts/run_capacity_full.sh skylark 10 134217728` (coarse_max=128 MiB; script internally invokes `taskset -c 10 ./cache_bench --experiment capacity --pattern <random|sequential> --samples 1000000 ...` per sweep stage — coarse, tail-extension, 3x dense-around-boundary, 2x repeat of deepest boundary, dense-past-deepest-boundary tail check)
- Sample count: 1,000,000 (timed; warm-up excluded)
- Random seed(s): 12345
- Raw output filename(s): `data_raw/skylark/capacity/capacity_{coarse,coarse_ext,dense0,dense1,dense2,dense2_rep1,dense2_rep2,denseTail}_{random,sequential}_20260908T160607Z.csv.gz` (gzipped after the fact, ~9x smaller, to keep repo size manageable; summaries below were generated from the uncompressed originals before compression)
- Processing script -> data_processed path: `data_processed/skylark/capacity/{coarse,coarse_ext,dense0,dense1,dense2,dense2_rep1,dense2_rep2,denseTail}_{random,sequential}_summary.csv`, plotted via `scripts/plot_capacity.py` into `data_processed/skylark/capacity/plots/{capacity_curve,capacity_boxplots}.{png,pdf}`. **Regenerated 2026-09-10** with `--boundary 32768 --boundary 16777216 --boundary 18295680 --boundary 21757352` to add the newly-identified L1 edge (see below).
- Detected boundaries (bytes): 16777216, 18295680, 21757352 (auto-detected by `run_capacity_full.sh`, dense-resampled and repeated 2x at the deepest one)
- **L1 boundary (backfilled 2026-09-10, from the already-collected coarse sweep — no
  new run needed):** `run_capacity_full.sh`'s auto-detector reported nothing below
  16.7 MiB at its default thresholds, but the coarse random-pattern data itself shows
  a clean flat plateau at 6.07-6.24 ticks/access from 1,024 to 32,768 bytes (41
  points, low noise), with the ramp starting immediately after (35,728 B -> 7.06
  ticks) and climbing steadily onward. **This gives L1 = 32,768 bytes (32 KiB)** —
  same value independently found the same way for Upgrade (see that machine's
  README) and matching Sunbird's hand-confirmed L1, via the same flat-then-ramp
  signature in each machine's own data, not assumed from one another. The
  auto-detector missed it for the same reason documented on Thunderbird: no single
  adjacent-point jump in the 8-points/octave coarse data clears the default
  `--min-abs-ticks 3.0`, even though the region is genuinely flat before and
  climbing after. Re-running `detect_cache_hierarchy.py` with `--min-abs-ticks 0.5
  --rel-threshold 0.1` recovers it: `L1: <= 32,768 bytes`. **PROVISIONAL** (clean in
  the data; not yet cross-checked by an independent test the way Sunbird's L1 was by
  its associativity knee).
- **Candidate L2/L3 shelf, ~4-16.8 MiB (backfilled 2026-09-10):** after the L1 ramp
  (6.24 ticks at 32,768 B climbing to 26.3 ticks at 4,194,304 B), the coarse data
  goes essentially flat from 4.19 MiB to 16.78 MiB — 17 points ranging only
  26.3-33.2 ticks with no monotonic trend (e.g. 27.6, 28.1, 27.0, 27.4, 27.9, 27.2,
  27.6 ticks bouncing in place across 5-9 MiB) — then jumps sharply to 52.4 ticks at
  18,295,680 B, a clear knee. At relaxed detector thresholds this whole 4-16.8 MiB
  span groups into one level (`detect_cache_hierarchy.py --min-abs-ticks 0.5
  --rel-threshold 0.1` reports `L7: 1,048,576–16,777,216 bytes, 27.22 ticks,
  33 points`). This reads like a genuine second plateau (candidate L2 or combined
  L2+L3, can't distinguish further without more targeted data) sitting before the
  already-confirmed L3->DRAM transition at ~16.8-22 MiB below — but at only
  8 points/octave this is not yet confirmed flat the same rigorous way Sunbird's
  plateaus were (40+ dense points, <2% run-to-run spread, independent repeats).
  **Would need a new 48-points/octave dense sweep across ~1-16 MiB on `skylark`
  itself to confirm — not resolvable from data already in this checkout** (this
  session has no access to `skylark`, only to this git checkout's already-collected
  data; analysis above used only already-committed `data_processed/skylark/capacity/`
  CSVs).
- Excluded runs (if any) and reason: none excluded. Note: the automated pipeline's own plotting step failed partway through the run (`ModuleNotFoundError: No module named 'matplotlib'` on this machine — see `data_raw/skylark/capacity/run_capacity_full_20260908T160607Z.log`); all data generation stages completed successfully before that failure. matplotlib (+ pillow, cycler, fonttools, kiwisolver) was installed via `pip3 install --user` and the plotting step was re-run standalone with the same summary-file set and boundaries the script would have used — `data_processed/skylark/capacity/plots/` is now up to date with all of the above data.
- Follow-up (not part of the automated `run_capacity_full.sh` pipeline): a manual tail-extension2 check further out (536870912-2147483648 bytes, i.e. 512 MiB-2 GiB), core=10, seed=12345, samples=1,000,000, warmup=3, points-per-octave=48 (same parameters as the script's own dense sweeps), to check for a further plateau beyond what the script's own tail-extension (128-512 MiB) covered.
  - `orig` pass: `run_capacity_ext2_20260908T171553Z.log` -> `data_raw/skylark/capacity/capacity_denseTail2_orig_{random,sequential}_20260908T171553Z.csv.gz` -> `data_processed/skylark/capacity/denseTail2_orig_{random,sequential}_summary.csv` (97 points each, complete).
  - `rep1` repeat: an initial attempt was interrupted partway (86/97 random points, no sequential); discarded and rerun cleanly as `run_capacity_ext2_rep1_20260908T220010Z.log` -> `capacity_denseTail2_rep1_{random,sequential}_20260908T220010Z.csv.gz` -> `denseTail2_rep1_{random,sequential}_summary.csv` (97 points each, complete).
  - Reproducibility: orig vs rep1 medians at 2147483648 bytes (2 GiB) agree within ~0.2% (279.05 vs 278.45 ticks/access, random pattern) -- no anomaly.
  - Finding: median latency rises only ~2% across the whole 512 MiB-2 GiB range (272.9 -> ~279 ticks/access, random pattern), flattening out by ~1.7 GiB. This region reads as an already-settled DRAM-latency plateau, not an open transition -- no further cache-level boundary detected out to 2 GiB.
  - Folded into `data_processed/skylark/capacity/plots/` -- `capacity_curve.{png,pdf}`/`capacity_boxplots.{png,pdf}` now span the full sweep out to 2 GiB (title-suffix "Phase I timing-only, extended to 2 GiB"), built from all coarse/dense/repeat/tail/tail2 summaries together. Confirms the ~16-22 MiB L3->DRAM transition is followed by a genuine flat plateau (~280 ticks/access) all the way to 2 GiB, not an unresolved further climb.

### line_size/
- Source file(s): `main_code/common/line_size.h`, `main_code/common/main.c`,
  `main_code/x86_64/timer_x86.h`, `scripts/run_line_size.sh`,
  `scripts/detect_line_size.py`, `scripts/plot_line_size.py`,
  `scripts/plot_line_size_family.py`, `scripts/plot_line_size_offset.py`,
  `scripts/summarize_raw.py`
- Build command: `make` (from repo root)
- Run command + arguments (main pass, both levels, both methods):
  `./scripts/run_line_size.sh skylark 10 32768,18295680 8,16,32,64,128,256 64,128`
  — boundaries are this machine's own capacity-experiment L1 (32,768 B,
  PROVISIONAL, see capacity/ above) and the deepest of the three detected
  L3->DRAM-transition boundaries (18,295,680 B). Two earlier attempts at
  these same boundaries/strides are kept for the record, both without the
  `candidate_overrides_csv` 5th argument (Method-A step 4 is designed to be
  skipped on a first pass, per `run_line_size.sh`'s header comment, so a
  human can inspect `line_size_family_curve.png` and choose real candidates
  before rerunning):
  `data_raw/skylark/line_size/run_line_size_20260912T191440Z.log` died
  partway through plotting (`ModuleNotFoundError: No module named
  'matplotlib'`, same failure mode as this machine's capacity run, fixed the
  same way with `pip3 install --user matplotlib`);
  `..._20260912T191646Z.log` completed the no-overrides first pass end to
  end, but (with step 4 skipped by design) also had Method B report `none`
  at both levels on that particular pass. Not investigated further: Method
  B's summary CSVs are overwritten (not timestamped) by each subsequent run,
  and the third attempt below is the one actually treated as authoritative.
  The third attempt
  (`./scripts/run_line_size.sh skylark 10 32768,18295680 8,16,32,64,128,256 64,128`,
  logged to `run_line_size_20260912T192816Z.log`) supplied the candidates
  chosen from the first pass's plots and is the one whose numbers are
  reported below; it completed cleanly end to end.
- Sample count: 1,000,000 per (stride, footprint, offset, pattern) point,
  seed=12345, core=10 (same core as the capacity/associativity runs on this
  machine), `-O0` build per repo convention.
- Notes on alignment/candidate strides tested: Method A (family of curves)
  swept the assignment's own example strides (8/16/32/64/128/256 B) at each
  level's own footprint window, then bracketed the chosen candidate at 8-byte
  granularity (the finest possible — `struct node` is one 8-byte pointer) and
  re-tested it at 8 node-0 offsets spanning 0-56 B in 8-byte steps to confirm
  the transition survives different alignments relative to a physical line
  (not an artifact of every node always starting at the same offset).

**Level 32,768 B (L1) — CONFIRMED, both methods agree.**
- Method A (family of curves): manual candidate=64B (chosen from
  `data_processed/skylark/line_size/level_32768/plots/line_size_family_curve.png`
  after inspecting the raw per-stride elbow diagnostic, which is NOT
  auto-applied — see `run_line_size.sh`'s header comment). Step-4
  cross-alignment refinement confirms 64B stable across offsets.
- Method B (single-curve, ramp-saturation): footprint=65,536 B (2x boundary,
  the script's default multiplier), coarse sweep (stride 8-1024 B, step 8 B)
  auto-detects 64B; dense sweep + 2 reproducibility repeats around it (all
  seeded independently: 12345/12346/12347) confirm 64B every time. See
  `data_processed/skylark/line_size/level_32768/plots/line_size_{curve,boxplots,family_curve,family_boxplots,offset_elbow,offset_boxplots}.{png,pdf}`.
- **Both methods agree: 64 bytes.** Matches the near-universal x86 cache
  line size and Sunbird's own confirmed 64B result
  (`data_raw/sunbird/README.md`).

**Level 18,295,680 B (deepest L3->DRAM-transition boundary) — Method A
confirmed 128B; Method B's own default 2x-footprint pass initially found
NOTHING (missing measurement) — backfilled 2026-09-12 by rerunning Method B
at a larger footprint multiplier. Read the whole subsection below before
citing a number for this level: the two methods now agree numerically, but
NOT with Level 32,768's answer, and that disagreement itself is the
headline finding.**

- Method A (family of curves): manual candidate=128B (chosen from
  `data_processed/skylark/line_size/level_18295680/plots/line_size_family_curve.png`).
  Step-4 cross-alignment refinement: elbow stable across 8/8 tested offsets
  (23,051,008-25,873,920 B footprint, 1.12x spread) — "consistent with a
  genuine, alignment-independent transition."
- Method B (single-curve), original attempt (`run_line_size_20260912T192816Z.log`,
  the pipeline's default `FOOTPRINT_MULTIPLIER=2.0` -> footprint=36,591,360 B):
  coarse sweep (stride 8-1024 B, step 8) rose smoothly from ~168 ticks at
  stride=8B to a single peak of ~274 ticks at stride=128B, then declined
  *continuously* (not flat) all the way down through ~136 ticks by
  stride=248B before a sharp final cliff to ~28 ticks by stride~312B+.
  `detect_line_size.py` correctly reported "no ramp-saturation plateau
  detected" — there genuinely was no flat run of 5 points within 1% anywhere
  in the pre-drop segment, only a smooth one-sided hump. **This was the
  correct, honest output of the tool, not a bug**: manually loosening
  `--flat-tolerance`/`--confirm` against this same data (tried 0.03/3 and
  0.02/2) does technically produce an answer (64B), but only by locking onto
  3-4 adjacent points on a still-visibly-rising slope (218/218/221 ticks,
  climbing to 274 a few points later) — not a real plateau. Rejected as
  p-hacking the detector, not a genuine measurement.
- **Root cause**: at `FOOTPRINT_MULTIPLIER=2.0`, the model's predicted
  post-saturation flat window (from `stride=line_size` to
  `stride=2*line_size`, i.e. only 128-256B if line_size=128B) is too narrow
  and too close to where the ~18.3 MB boundary itself is not a sharp knee
  (see capacity/ above — this is the "dense-resampled and repeated 2x"
  boundary, itself softer than a clean step) — the ramp and the fall-off
  blend into one continuous curve with no flat segment between them at this
  particular (large, chiplet-LLC-adjacent) boundary. 2.0x reportedly "works
  reliably" per the script's own header comment, but that was characterized
  on Sunbird's much-shallower ~20 MB boundary, not verified against a
  boundary this deep on a different microarchitecture.
- **Backfilled 2026-09-12 (`run_line_size_methodB_footprint4x_20260912T204919Z.log`)**:
  reran Method B at `--footprint-bytes 73182720` (4x boundary instead of the
  script's default 2x), core=10, samples=1,000,000, both patterns, otherwise
  identical to `run_line_size.sh`'s own Method-B steps (coarse
  stride 8-1024B step 8, then dense stride 64-257B step 1 bracketing the
  coarse estimate, then 2 independently-seeded repeats: base seed=12345,
  rep1=12346, rep2=12347).
  - Coarse pass (8B-step, full 1,000,000 samples): now shows a genuine long
    flat plateau (~270-277 ticks) from stride=128B through the end of the
    dense window (257B) before the eventual capacity-driven drop (~520B) —
    `detect_line_size.py` at its unmodified DEFAULT thresholds now cleanly
    reports **128B**, matching Method A at this level exactly, with no
    threshold tuning needed.
  - Dense pass (1B-step) + both repeats: all three (base/rep1/rep2)
    reproducibly report the DEFAULT detector's estimate as **65B**, not
    128B. Manually inspecting the dense data shows why: strides that are
    exact multiples of 8 sit systematically ~0.47% below their immediate
    (non-multiple-of-8) neighbors in the true 128-257B plateau region (mean
    275.33 vs 276.63 ticks/access, n=17 vs 112, over stride 128-256B) — an
    alignment/pointer_chase-packing artifact, not a second cache-topology
    fact. That small periodic dip happens to satisfy the detector's tight
    1%-over-5-points flat-tolerance in an early, narrow window (strides
    65-69B) while the underlying curve is still genuinely climbing (251 ->
    277 ticks over the next ~70 bytes) — a reproducible FALSE POSITIVE
    (same wrong answer, 65B, from 3 independently-seeded runs — a systematic
    detector blind spot at this data's specific shape, not run-to-run
    noise). The real, visually obvious plateau in the same dense data is the
    long flat run from ~128B to the window's own right edge (257B): 130
    points, mean 276.5 ticks, essentially all within +-0.7% of each other
    except the period-8 dips just described.
  - **Conclusion for this level's Method B: 128 bytes**, taking the coarse
    pass's clean, threshold-default, unmodified answer and the dense pass's
    visual (not auto-detected) plateau start over the dense pass's own
    mis-triggered 65B — see plots:
    `data_processed/skylark/line_size/level_18295680/plots/line_size_{curve,boxplots}.{png,pdf}`
    (regenerated 2026-09-12 to include the fp4x coarse/dense/rep1/rep2 data;
    `--boundary 128` marks the confirmed candidate).
- **Both methods now agree at this level: 128 bytes. But this does NOT match
  Level 32,768's 64-byte answer** — real x86 hardware essentially never has a
  genuinely different physical line size at different cache levels, so a
  clean 2x disagreement between two internally-well-corroborated
  measurements is itself the more interesting result, not a resolved
  answer. Not investigated further within Phase I timing-only discipline;
  candidate confounds worth checking in Phase II or with a redesigned test
  (neither confirmed): (1) this AMD EPYC 7532 (Zen 2 "Rome") has a
  chiplet/CCD L3 built from multiple slices with address-hashing between
  them (unlike Sunbird's presumably more monolithic LLC) — a stride-128
  access pattern could interact with that hashing differently than
  stride-64 does, independent of the physical line size; (2) an effect
  structurally similar to the DTLB/page-indexed confound already documented
  for the associativity experiment on other machines (see this repo's
  `CLAUDE.md`) — worth a dedicated follow-up before trusting either number
  as the machine's "true" line size over the other.
- Per `run_line_size.sh`'s own step-5 discipline: **do not average 64B and
  128B into one number** — report the disagreement, as done here.

**Family-of-curves-only rerun (2026-09-12), boundaries taken from the
consolidated `CAPACITY_RESULTS.md` rather than re-derived from this file —
new L2-candidate level added, existing two levels reproduced for a
consistency check.** Ran Method A steps 1-3 only (coarse per-stride sweep +
`line_size_family_curve.png`; no Method B, no step-4 offset refinement) at
three boundaries: L1=32,768 B (exact, per `CAPACITY_RESULTS.md`), a new
**L2 candidate=8,388,608 B** (8 MiB, the midpoint of `CAPACITY_RESULTS.md`'s
~4-16.8 MiB unconfirmed candidate-shelf range — not tested by any prior
line_size run on this machine), and the existing LLC-transition boundary
18,295,680 B (within `CAPACITY_RESULTS.md`'s ~16-22 MiB onset range; same
value already used above). Core=10, seed=12345, samples=1,000,000,
strides=8/16/32/64/128/256B, random pattern, one-off script (not
`run_line_size.sh` itself, to skip Method B/step-4 — logic mirrors its
Method-A loop exactly), log:
`data_raw/skylark/line_size/run_line_size_familyonly_20260912T213811Z.log`.
- **L1 (32,768 B) and LLC-transition (18,295,680 B) levels reproduce the
  already-confirmed shapes above** — visually inspecting the new
  `line_size_family_curve.png` at each: L1's curves fan out starting right
  at the 32,768 B boundary with larger strides (64/128B) climbing faster,
  consistent with the already-confirmed 64B answer; the LLC-transition
  level's 128B/256B curves saturate first and together, consistent with the
  already-confirmed 128B answer. (The plot's own auto-diagnostic elbow
  line — printed to the log, e.g. "smallest candidate stride whose elbow
  agrees... is 8B" — is the known-unreliable single-un-repeated-sweep
  heuristic documented in `run_line_size.sh`'s header comment, NOT a
  citable answer on its own; it disagrees with the already-confirmed 64B/
  128B numbers here for exactly the reason that comment describes, and is
  not evidence against them.)
- **New L2-candidate level (8,388,608 B): all 6 stride curves stay flat and
  overlapping across the entire tested window below ~2^24 (16.78 MiB),
  with the only separation appearing once the curves enter the
  already-known LLC transition** (window was `[1,048,576, 33,554,432]`,
  i.e. spans past the ~16.78 MiB onset). This is a null result for line-size
  purposes at this candidate — no stride-dependent elbow inside the
  candidate shelf itself — but it IS consistent with `CAPACITY_RESULTS.md`'s
  own characterization of this region as a flat, featureless candidate
  shelf (26.3-33.2 ticks, no monotonic trend) rather than a real boundary
  with its own line-size-relevant transition. Not pursued further under
  Phase-I family-of-curves-only scope; would need this region's own
  ~48-points/octave capacity dense sweep (already flagged as an open TODO
  in `CAPACITY_RESULTS.md`) before a line-size test here would even be
  targeting a confirmed boundary.
- Raw/summary files use a distinct timestamp
  (`20260912T213811Z`) from the earlier authoritative run
  (`20260912T192816Z`) — nothing was overwritten; both are preserved.

**Second family-of-curves-only rerun (2026-09-12), boundaries given directly
as L1/L2/L3 = 32,768 / 524,288 / 8,388,608 B (32 KiB / 512 KiB / 8 MiB) —
not re-derived from this machine's own capacity sweep.** Same one-off
Method-A-steps-1-3-only script/parameters as the rerun above (core=10,
seed=12345, samples=1,000,000, strides=8/16/32/64/128/256B, random pattern),
log: `data_raw/skylark/line_size/run_line_size_familyonly_20260912T220233Z.log`.
- **L1 (32,768 B)**: fans out right at the boundary as before, consistent
  with the already-confirmed 64B result.
- **L2 (524,288 B, new level)**: `line_size_family_curve.png` shows one
  continuous rising ramp across the whole [65,536, 2,097,152] window with no
  flat elbow anywhere — matches this machine's own capacity data, which has
  no confirmed shelf at 512 KiB (that byte value sits inside the already-
  documented single L1->LLC ramp region, not at a boundary this machine's
  own timing data supports).
- **L3 (8,388,608 B)**: same level directory/window as the earlier rerun's
  "L2 candidate" (8,388,608 B) — reproduces that result byte-for-byte (flat
  overlapping curves until ~16.78 MiB, then merging into the already-known
  LLC transition); see that bullet above.

**Reproducibility repeat (rep1, seed=12346) of the above, 2026-09-12.**
Same 3 boundaries/core/strides, independent seed (12346 vs. the original
12345), processed summaries/plots kept separate under each level's own
`rep1/` subdirectory (`data_processed/skylark/line_size/level_<boundary>/
rep1/plots/`) so neither seed's output overwrote the other — log:
`data_raw/skylark/line_size/run_line_size_familyonly_rep1_20260912T221257Z.log`.
- **L1 and L3 reproduce closely across seeds** (per-stride auto-elbow bytes
  agree exactly or within one grid step at 8/16/32/64B for both levels; L1's
  128B/256B auto-elbow shifts between seeds, but that diagnostic is already
  flagged as unreliable/not-citable above — the visual curve shapes match).
- **L2 (524,288 B) reproduces the "no real elbow" finding, not a numeric
  answer**: rep1's `line_size_family_curve.png` is visually the same
  continuous, featureless ramp as the seed=12345 run (curves overlapping
  through ~2^18, fanning out only in the gradual mid-ramp, no plateau
  anywhere in [65,536, 2,097,152]); the auto-elbow diagnostic is noisy and
  inconsistent between seeds here (e.g. 128B found no elbow at all in
  rep1) — expected/consistent behavior for a diagnostic run on data with no
  genuine transition, not a discrepancy to resolve. **Confirms, across two
  independent seeds, that 512 KiB is not a boundary this machine's own
  timing data supports.**

**Step-4 offset refinement (2026-09-12), user-chosen candidates (not derived
from any auto-detector): L1=32B, L2=64B, L3=64B.** Ran the bracket
(8B granularity around each candidate) + 8-offset (0-56B) cross-alignment
sweep, seed=12345, same windows as the coarse passes above, log:
`data_raw/skylark/line_size/run_line_size_step4only_20260912T222756Z.log`.
All three levels' printed verdict says "elbow stable across the 8/8
offsets" — **but none of the three should be read as confirming its
candidate as the true line size**, for three different reasons:
- **L1 candidate=32B**: offset-stable (52,000-58,368 B, 1.12x spread), but
  `line_size_offset_elbow.png` for this level is visibly jagged across
  bracket strides (not a clean flat line), and — more importantly — this
  is exactly the documented false-positive pattern already called out in
  `run_line_size.sh`'s own header comment (and first observed on Sunbird,
  see that machine's README / this repo's `CLAUDE.md`): **a candidate
  stride below the true line size packs multiple nodes per physical line,
  which can look alignment-independent for the wrong reason.** This
  level's true line size is already doubly-confirmed as **64B** (Method A
  visual read + Method B ramp-saturation, both on the original authoritative
  run at this same 32,768 B boundary) — this step-4 result at 32B does not
  overturn that; it reproduces the known failure mode, not a competing
  answer.
- **L2 candidate=64B**: offset elbow values are NOT tightly clustered —
  they jump around a ~1.3x band (741,440-1,048,560 B) non-monotonically
  across both bracket stride and offset in `line_size_offset_elbow.png`
  ("stable" only in the sense that the auto-detector's 1.26x-spread
  threshold was satisfied). This level's own family-of-curves data (both
  seeds, see above) shows **no plateau/elbow anywhere in the window at
  all** — a continuous featureless ramp. Read together, this step-4 result
  is best explained as the detector clustering on noise in a region with no
  genuine transition, not confirmation of a real 64B-related boundary at
  512 KiB.
- **L3 candidate=64B**: all 8 offsets land on the exact same elbow value
  (~26,632,128-26,632,160 B, 1.00x spread — reproduces perfectly, visible
  as a single overlapping line in the plot). That precision is real, but
  the detected footprint (~26.6 MiB) is far outside this level's own
  [2,097,152, 33,554,432] B window's boundary of interest (8 MiB) and
  matches this machine's independently-documented, already-characterized
  LLC->DRAM transition — the same transition directly tested above at
  boundary=18,295,680 B, where the full-rigor run (Method A + Method B,
  both agreeing) found **128B, not 64B**. This step-4 "confirmation" is the
  detector re-locking onto that same distant, unrelated transition (it's
  inside this level's wide window too), not evidence about anything near
  8 MiB specifically.
- **Bottom line**: per-level "8/8 offsets agree" is a necessary but not
  sufficient check — none of these three results should be cited as a new
  or competing line-size number; the already-established values (64B at
  the confirmed L1 boundary, 128B at the confirmed LLC-transition boundary,
  and no evidence of any real transition at 512 KiB or 8 MiB on this
  machine) still stand.

**L1-only family-of-curves rerun (2026-09-13), seed=12345 (fresh timing
sample, not a new seed).** Log:
`data_raw/skylark/line_size/run_line_size_familyonly_20260913T134703Z.log`.
Reproduces the already-established shape at this boundary: curves fan out
right at 32,768 B, 64B/128B stride climbing fastest — consistent with the
already doubly-confirmed **64B** answer. Auto-elbow diagnostic again
disagrees run-to-run (this pass: 8B/16B/32B/128B cluster ~58,368 B, 64B
outlier at 36,736 B, 256B at 51,968 B) — same known-unreliable-on-its-own
caveat as every earlier pass at this level; not cited on its own.
**Note:** this rerun overwrote the processed `family_*_summary.csv` files
under `level_32768/` with fresh (seed=12345) data — raw CSVs are kept
under their own timestamp, nothing lost, but if the exact numbers from the
2026-09-12 write-up above are needed again, they're only in the raw CSVs
now, not the processed summaries.

**Several more family-of-curves reruns (2026-09-13), seed=12345, same 3
boundaries (32,768 / 524,288 / 8,388,608 B) — repeated verbatim several
times at the user's request, each overwriting the previous run's processed
summaries/plots at the same path (raw CSVs kept, uniquely timestamped).
Logs**: `run_line_size_familyonly_2026091314{1326,1424,2553,4152}Z.log`.
**No new findings** — each rerun reproduces the same shapes already
documented above (L1 fans out at the boundary consistent with 64B; L2 is a
continuous featureless ramp; L3 stays flat until merging into the known
LLC transition). A seed=12346 reproducibility repeat of all 3 was also run
the same day, written to each level's own `rep1/` subdirectory (not
overwriting the seed=12345 data): log
`run_line_size_familyonly_rep1_20260913T144928Z.log`.

**Second step-4 run (2026-09-13), candidates L1=32B, L2=64B, L3=128B**
(L3's candidate changed from 64B to 128B vs. the step-4 run above; L1/L2
unchanged). Log:
`data_raw/skylark/line_size/run_line_size_step4only_20260913T145558Z.log`.
- **L1 (32B) and L2 (64B)**: same shape/caveats as the first step-4 run —
  offset-stable within a ~1.1-1.3x band, but for the same already-documented
  reasons (L1: below-true-line-size packing artifact vs. the doubly-
  confirmed 64B; L2: clustering on noise in a window with no real elbow)
  neither should be read as new evidence.
- **L3 candidate=128B: a cleaner, more interesting result — but still not
  citable, and for a new reason.** `line_size_offset_elbow.png` at this
  level now shows a genuinely sharp, perfectly offset-independent (all 8
  offsets exactly overlapping) step: flat ~23,726,464 B for bracket
  strides 104-128B, then a clean jump to ~26,632,072 B for strides
  136-152B, split exactly at the 128B candidate. That crispness is real.
  **But the direction is backwards from what a genuine line-size elbow
  should do**: per this method's own model (a stride below the true line
  size packs multiple nodes per physical line, so it needs a LARGER
  footprint before enough distinct lines are touched to trip the knee —
  see the doubly-confirmed L1 case and the original level_18295680 run,
  both of which show elbow footprint *decreasing* as stride increases,
  then flattening once stride reaches/exceeds the true line size). Here
  it's the opposite: the *smaller* bracket strides (104-128B) give the
  *smaller* elbow, and the *larger* strides (136-152B) give the *larger*
  one. That inversion is inconsistent with a real per-stride packing
  effect, and is much better explained by this level's window being
  dominated by the same distant, already-characterized real LLC transition
  documented above (~23.7-26.6 MiB is well within that transition's own
  climbing region) — the sharp, clean split is most likely this coarse
  (6-points-per-octave) sweep's detector landing on a different one of a
  handful of shared grid points depending on tiny, stride-independent
  noise, not a genuine stride-dependent signal. **Still not evidence for a
  real boundary near 8 MiB, and still not evidence for 128B (or any
  stride) being this level's line size.**

**Third step-4 run (2026-09-13), candidates back to L1=32B, L2=64B,
L3=64B** (same triplet as the first step-4 run, 2026-09-12). Log:
`data_raw/skylark/line_size/run_line_size_step4only_20260913T150308Z.log`.
Reproduces that run closely: L1 46,336-58,368 B (1.26x), L2 832,192-934,144 B
(1.12x), L3 23,726,528-26,632,128 B (1.12x, still squarely inside the known
real LLC transition). Same caveats as the first step-4 run apply — none of
the three are new evidence for their candidate as a real line size.

**Fourth step-4 run (2026-09-13), candidates L1=64B, L2=64B, L3=64B.** Log:
`data_raw/skylark/line_size/run_line_size_step4only_20260913T150727Z.log`.
Plots: `data_processed/skylark/line_size/level_{32768,524288,8388608}/
plots/line_size_offset_{elbow,boxplots}.{png,pdf}` (overwrote the prior
step-4 run's plots/summaries at the same paths; raw CSVs kept separately
under this run's own timestamp).
- **L1 candidate=64B: for the first time, the script's own verdict is
  "NOT stable"** — elbow varies 1.41x across offsets (36,736-51,968 B),
  printed with "transition may be alignment-sensitive, do not cite this
  candidate as a clean line-size result without further investigation."
  Notably different from every 32B-candidate L1 run above, which all
  reported clean 8/8 offset agreement. Worth flagging rather than
  smoothing over: this is the one step-4 result so far where the tool
  itself declined to certify stability, at the one candidate (64B) that
  matches this level's independently, doubly-confirmed real line size —
  plausibly consistent with the docstring's own caveat that a candidate
  AT/above the true line size (unlike one packing multiple nodes below
  it) is the case where genuine alignment sensitivity could show up. Not
  chasing this further this pass; noted for anyone continuing this work.
- **L2 (64B) and L3 (64B)**: same shapes/caveats as the earlier 64B/64B
  step-4 runs above — L2 offset-stable in a band with no underlying real
  elbow (noise); L3 offset-stable but squarely inside the known real LLC
  transition, not evidence about an 8 MiB boundary.

### associativity/
- Source file(s): `main_code/common/associativity.c`, `main_code/common/associativity.h`, `main_code/common/main.c`
- Build command: `make` (from repo root)
- Run command + arguments: `./scripts/run_associativity_full.sh skylark 10 32768,524288,8388608` (explicit hand-supplied `cache_bytes_csv`, NOT auto-detected — see below for where these three values came from)
- `cache_bytes` used per level (node-to-node stride, forces every probed node into the same cache set): L1=32,768 B, L2=524,288 B (512 KiB), L3/LLC=8,388,608 B (8 MiB) — taken from `CAPACITY_RESULTS.md`'s per-machine capacity table as manually curated there (2026-09-12), **not** from this machine's own `data_processed/skylark/capacity/` analysis above, which only established a *region* (candidate L2/L3 shelf ~4-16.8 MiB, one dominant ramp) rather than a single confirmed capacity value for L2 or L3 — see the discrepancy note below.
- Conflict-set construction method: cyclic dependent pointer chase over `num_ways` nodes spaced exactly `cache_bytes` apart (same set-index bits by construction regardless of unknown line size/way count — see `associativity.h`), num_ways swept 2-40 (way_step=1), both random and sequential-control patterns, 1,000,000 timed samples/point, batch_size=1000, 3 warmup passes, base seed=12345 + 2 reproducibility repeats (seeds 12346, 12347)
- Core/timestamp: core=10, timestamp=20260912T224538Z, full transcript in `data_raw/skylark/associativity/run_associativity_full_20260912T224538Z.log`
- Raw output: `data_raw/skylark/associativity/{L1,L2,L3_LLC}/associativity_{base,rep1,rep2}_{random,sequential}_20260912T224538Z.csv.gz`
- Processed summaries + plots: `data_processed/skylark/associativity/{L1,L2,L3_LLC}/*.csv`, `data_processed/skylark/associativity/{L1,L2,L3_LLC}/plots/associativity_{curve,boxplots}.{png,pdf}`

**Results and trustworthiness (read before citing any of these numbers):**
- **L1 (32,768 B): associativity = 8-way — TRUSTWORTHY.** Single sharp knee at num_ways=9, identical across base and both repeats (9, 9, 9), flat plateau before (~6.1 ticks) and after (~9.7 ticks), random and sequential curves overlap. Matches Sunbird's independently hand-confirmed 8-way L1 via the same clean-single-knee signature.
- **L2 (524,288 B): auto-detected "9-way" — NOT TRUSTWORTHY, likely an L1-aliasing artifact.** The curve is a multi-step staircase (jump at num_ways=9, partial drop, second jump at 13, a third rise starting ~37), not a single knee — see `associativity_curve.png`. The detector locked onto the *first* jump, which lands at exactly the same num_ways as L1's own knee. This is suspicious rather than confirmatory: 524,288 B is an exact 16x multiple of L1's own 32,768 B stride, so every node probed here also aliases into the same L1 set as every other probed node — this measurement is plausibly just re-detecting L1's 8-way limit, not L2's real associativity. This is the same unresolved stride-vs-true-structure confound already documented in `CAPACITY_INFERENCE_STATUS.md` for Sunbird's own L2 candidates (multi-step staircases at both 131,072 B and 262,144 B, "not a clean knee," open mechanistic question). Do not cite "L2 = 8-way" for skylark from this run.
- **L3/LLC (8,388,608 B): auto-detected "8-way" — NOT TRUSTWORTHY, and not even internally reproducible.** Also a multi-step staircase (small step at num_ways=8, another at 12, the dominant transition actually starts around num_ways=25-34 up to ~270 ticks/access) rather than one clean knee. Worse, the pipeline's own built-in reproducibility check disagreed across seeds: base=8, repeat1=8, repeat2=7 — printed as an explicit `WARNING: ... do NOT treat this level's associativity as resolved` by `run_associativity_full.sh` itself. Do not cite "L3 = 8-way" for skylark from this run.
- **Known discrepancy with this machine's own capacity data (flag for report writing):** `CAPACITY_RESULTS.md`'s L2=512 KiB / L3=~8 MiB values used as the stride here do not match what skylark's own capacity sweep above independently found — that data shows one candidate shelf spanning ~4-16.8 MiB (PROVISIONAL-WEAK, not resolved to a single boundary) rather than two separate levels at 512 KiB and 8 MiB. Per team decision (2026-09-12), the associativity experiment was still run at the manually-selected 512 KiB / 8 MiB values despite this open disagreement; the multi-step/non-reproducible results above are consistent with (though not conclusive proof of) `cache_bytes` not matching either level's true capacity, exactly as `associativity.h`'s own design notes predict for a wrong-by-construction stride.

### latency/
Two sub-experiments, `hit_latency` and `miss_latency`, run 2026-09-13
(unattended session; user not present). Footprint/target/evict byte values
taken **only from `CAPACITY_RESULTS.md`** (L1 = 32,768 B, L2 = 524,288 B,
LLC ≈ 8 MiB = 8,388,608 B, using N * 1,048,576 for "~N MiB" per project-wide
direction) — the associativity section above already flags a discrepancy
between this machine's own capacity data (one candidate ~4-16.8 MiB shelf,
not two separate L2/L3 boundaries) and `CAPACITY_RESULTS.md`'s picked
values; per the same project-wide direction that applies to this run,
`CAPACITY_RESULTS.md` is used anyway and this discrepancy is repeated here
rather than re-litigated.
- Idle-core check before running: `who`/`ps` showed no other logged-in
  users, but `ps aux` found another student's process (`msabap`,
  `cache_bench_x86 --exp nextlevel`) pinned via `psr=3` to core 3 at ~99.8%
  CPU the entire session — avoided. Two `/proc/stat` snapshots taken 3s
  apart confirmed core 6 idle (0 busy ticks out of ~724 total in the
  window, i.e. <1% busy); core 6 used for both runs below.
- Build command: `git pull && make clean && make` (from repo root); `python3 -c "import matplotlib"` confirmed working (3.9.4) before running.
- Git commit hash of the code used: `e343732c0b57beece621da8e7c3a9bd8be236d25`

**hit_latency (dependent chain + independent-load diagnostic control):**
- Source file(s): `main_code/common/{main.c,latency.c,latency.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Run command + arguments: `./scripts/run_hit_latency_full.sh skylark 6 L1:32768,L2:524288,LLC:8388608,DRAM:536870912` (pinned via `taskset -c 6`). DRAM's 536,870,912 B (512 MiB) footprint is not a `CAPACITY_RESULTS.md` boundary — it's a "deep in the DRAM plateau" pick, matching the same convention every other machine's hit_latency run used.
- Per level: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each run at `--load-mode {dependent,independent}` × `--pattern {random,sequential}` (4 combinations), 1,000,000 timed accesses per combination (batch size 1000, `DEFAULT_BATCH_SIZE`), 3 untimed warm-up passes.
- Regular vs. randomized control included: yes, both `--pattern random` and `--pattern sequential` run at every (level, load_mode) combination.
- Raw output filename(s): `data_raw/skylark/latency/hit/<LEVEL>/hit_latency_{base,rep1,rep2}_{dependent,independent}_{random,sequential}_20260913T061014Z.csv.gz`
- Processing: `scripts/summarize_raw.py` per raw file → `data_processed/skylark/latency/hit/<LEVEL>/*_summary_20260913T061014Z.csv` → `scripts/plot_hit_latency.py` → `data_processed/skylark/latency/hit/<LEVEL>/plots/hit_latency_boxplots.{png,pdf}`.
- **Result (dependent, random pattern, base run median, n=1000 each): a clean, monotonically increasing 4-tier ladder — L1 ≈ 6.24 ticks, L2 ≈ 16.15 ticks, LLC ≈ 27.22 ticks, DRAM ≈ 274.87 ticks.** At every level and both patterns, `--load-mode independent` measured faster than `dependent` (e.g. LLC random: 7.48 vs 27.22; DRAM random: 46.49 vs 274.87), confirming the independent-load control correctly exposes memory-level parallelism at every level — the expected signature, not itself the reported latency. Sequential-pattern dependent latency stayed essentially flat (~6.1-6.2 ticks) at every level including DRAM, consistent with hardware prefetching hiding the miss cost entirely for a fully predictable stride — this is expected behavior, not a bug.
- No `[UNEXPECTED -- investigate]` flags fired at any level/pattern (checked all 8 combinations' printouts from `plot_hit_latency.py`'s required MLP-exposing check).

**miss_latency (forced eviction + single-shot reload):**
- Source file(s): same list as hit_latency above.
- Eviction-set calibration done before picking final parameters (core 6, random pattern, 100 trials, `target-bytes 8388608`): a candidate `evict-bytes` of 16,777,216 (2x the ~8 MiB LLC capacity) measured ~67.7 ms/trial (6.77s/100). Extrapolated to the full base+2reps × 2-pattern run (1,200 trials total across all three transitions, LLC_to_DRAM dominating) ≈ 81s — comfortably under the ~15 min budget, so no need to shrink; used 16,777,216 B as-is (did not jump to a much larger value, per the explicit caution against repeating Sunbird's original 512 MiB-evict-set mistake).
- Run command + arguments: `./scripts/run_miss_latency_full.sh skylark 6 L1_to_L2:32768:524288,L2_to_LLC:524288:8388608,LLC_to_DRAM:8388608:16777216` (core 6, same idleness check as hit_latency above; `--batch-size 1` passed automatically by the script only to satisfy `main.c`'s cross-experiment `--samples`/`--batch-size` validation, has no effect on miss_latency's own single-shot-per-trial logic).
- Per transition: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--pattern {random,sequential}`. 200 trials per (transition, pattern, run), 3 untimed warmup passes before the first timed trial and again before every subsequent trial.
- Raw output filename(s): `data_raw/skylark/latency/miss/<TRANSITION>/miss_latency_{base,rep1,rep2}_{random,sequential}_20260913T061426Z.csv.gz`
- Processing: `scripts/summarize_raw.py` → `data_processed/skylark/latency/miss/<TRANSITION>/*_summary_20260913T061426Z.csv` → `scripts/plot_miss_latency.py --hit-latency-summary <matching hit_latency dependent/random summaries>` → `data_processed/skylark/latency/miss/<TRANSITION>/plots/miss_latency_boxplots.{png,pdf}`.
- **Result (random pattern, base run median, n=200 each): L1→L2 ≈ 96.0 ticks, L2→LLC ≈ 120.0 ticks, LLC→DRAM ≈ 360.0 ticks** — monotonically increasing, consistent with genuinely deeper eviction at each transition.
- Run-to-run spread: `plot_miss_latency.py`'s >20%-spread stderr warning fired on two of the three transitions' random pattern — **L1_to_L2** (medians 96.0/120.0/120.0 across base/rep1/rep2, 21.4% spread) and **L2_to_LLC** (medians 120.0/96.0/144.0, 40.0% spread); **LLC_to_DRAM did not trigger the warning** (medians 360.0/360.0/384.0, ~6.4% spread). Per instructions, these two flagged transitions were NOT re-run to make the warning disappear — recorded as-is, consistent with this project's established pattern of real shared-machine interference showing up as scattered single-run spikes (see Sunbird/Crux/Charnwood/Thunderbird/Ookay's capacity/associativity write-ups) rather than necessarily a methodological flaw; not independently traced to a specific interfering process for this run.
- **Single-shot measurement overhead, isolated via a dedicated control (2026-09-13):** `taskset -c 6 ./cache_bench --experiment miss_latency --target-bytes 32768 --evict-bytes 512 --pattern random --samples 2000 --batch-size 1 --seed 12345`, then `tail -n +3 | awk -F, '{a[NR]=$5;...} END{asort(a); print a[int(n/2)]}'` → **median = 72 ticks**. `evict-bytes=512` is only ~8 cache lines spread across L1's sets — overwhelmingly unlikely to actually evict the target's own line — so this is a control, not a real L1 miss. Compared to this machine's own batched L1 hit_latency dependent/random median (6.24 ticks, above), the gap is **~65.8 ticks of fixed single-shot measurement overhead** (unamortized `lfence`/`rdtsc`/`rdtscp` + post-function-call pipeline state — see `main_code/common/latency.h`'s `run_miss_latency_experiment` "KNOWN LIMITATION" docstring), not real miss cost. This means every raw miss_latency median above is "true reload latency + ~66 ticks," not a clean number.
- **Approximate overhead-corrected incremental penalty** (raw miss median minus source-level's own batched hit_latency dependent/random median, then minus the ~65.8-tick overhead measured above — presented as approximate, not precise, per the caveat just above): L1→L2 ≈ 96.0 − 6.24 − 65.8 ≈ **24 ticks**; L2→LLC ≈ 120.0 − 16.15 − 65.8 ≈ **38 ticks**; LLC→DRAM ≈ 360.0 − 27.22 − 65.8 ≈ **267 ticks**. Still monotonically increasing after correction, consistent with genuinely deeper eviction at each transition — but treat the absolute values as approximate, same caution as every other machine's uncorrected miss_latency numbers.
- Not yet done: the L1_to_L2 and L2_to_LLC repeat-spread hasn't been traced to a specific interfering process (no `mpstat`/`ps` check was run again mid-sweep, only before the whole run started); the single-shot overhead above was only measured once, at the L1 footprint, not independently re-measured at L2/LLC/DRAM footprints.

### inclusion_policy/
Run 2026-09-13, same session as this file's other backfills. Boundary values
from `CAPACITY_RESULTS.md` only (L1 = 32,768 B, L2 = 524,288 B, LLC =
8,388,608 B) — per project-wide direction, taken as given rather than
re-derived from this machine's own capacity/ region above (which never
resolved a single L2/LLC boundary, only a broad ~4-16.8 MiB candidate
shelf — see capacity/ section).
- Idle-core check before running: `who` showed 2 other logged-in users
  (`rrsood`, `dananth`), neither with a process pinned to a specific core
  per `ps aux --sort=-%cpu` (top CPU consumers were this session's own
  vscode-server/claude processes and an unrelated `CrashPlanService`, none
  core-pinned); `mpstat -P ALL 1 2` showed every core at ~0% utilization
  machine-wide at the time. Reused core 6 (idle-verified via two
  `/proc/stat` cpu6 snapshots 3s apart: 301/302 ticks idle, ~99.7%) — same
  core as this machine's own hit_latency/miss_latency runs above.
- Build command: `git pull && make clean && make` (from repo root). Git
  commit hash of the code used: `9ded3a929d5ac354a2bcdfb19e18c297e0ecb3c5`
  (post-merge of Sunbird's hardened `run_inclusion_policy_full.sh`/
  `ASSUMED_LINE_SIZE_BYTES` env-var override, commit a6c0368, with this
  machine's own hit_latency/miss_latency commit).
- Source file(s): `main_code/common/{main.c,inclusion_policy.c,inclusion_policy.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- **Line size used per pairing — NOT a single constant for this machine,
  per this machine's own line_size/ section's headline finding (64B at the
  confirmed L1 boundary, but 128B at the confirmed deep LLC->DRAM
  transition — a genuine, unresolved 2x disagreement, not averaged
  together).** Ran as two separate invocations so each pairing's
  `--evict-bytes` scaling uses the line size confirmed nearest its own
  lower-level target, via `run_inclusion_policy_full.sh`'s
  `ASSUMED_LINE_SIZE_BYTES` env-var override (added for exactly this
  cross-machine situation, see that script's header comment and
  `CLAUDE.md`'s associativity section):
  - `ASSUMED_LINE_SIZE_BYTES=64 ./scripts/run_inclusion_policy_full.sh skylark 6 L1_vs_L2:32768:524288:L2_to_LLC` (ts `20260913T180514Z`) — 64B matches this machine's doubly-confirmed L1 line size, and there is no evidence of a different line size at the L2 candidate footprint (line_size/ found no elbow there at all — a null result, not counter-evidence for 64B).
  - `ASSUMED_LINE_SIZE_BYTES=128 ./scripts/run_inclusion_policy_full.sh skylark 6 L2_vs_LLC:524288:8388608:LLC_to_DRAM,L1_vs_LLC:32768:8388608:LLC_to_DRAM` (ts `20260913T180533Z`) — 128B matches this machine's confirmed line size at the real, deep LLC->DRAM transition (both pairings evict past LLC, so both use the LLC-region line size).
- Wall-time calibration done before committing to a full run (20 trials
  each, core 6, random pattern): 32 MiB evict_bytes (L1_vs_L2 scale) ran in
  0.027s (~1.4 ms/trial); 256 MiB evict_bytes (L2_vs_LLC/L1_vs_LLC scale)
  ran in 0.226s (~11.3 ms/trial). Both far faster than Sunbird's dense-buffer
  miss_latency calibration (~74-604 ms/trial) — this experiment's eviction
  buffer only touches one line per 4096 B page (`--evict-stride-bytes
  4096`), so even a 256 MiB footprint is only 65,536 page touches per lap,
  not a dense walk. No `tmux` needed; full 3-pairing run (calibration +
  base + 2 repeats x 2 patterns each) completed in well under a minute.
- Eviction/reload construction: identical mechanism to Sunbird's (see
  `main_code/common/inclusion_policy.h`'s module doc comment) —
  target/control freshly page-aligned at offset 0, eviction buffer one node
  per page at fixed offset 2048 B, `--evict-bytes` computed as
  `lower_level_bytes * 4096 / ASSUMED_LINE_SIZE_BYTES` (so L1_vs_L2:
  524,288 * 4096/64 = 33,554,432 B (32 MiB); L2_vs_LLC and L1_vs_LLC:
  8,388,608 * 4096/128 = 268,435,456 B (256 MiB) each).
- Per pairing: calibration (500 single-shot trials, evict_bytes=target_bytes,
  nothing evicted) + base + 2 reproducibility repeats (seed 12345/12346/12347),
  both eviction-walk traversal patterns, 200 single-shot trials each
  (`--batch-size 1`, same cross-experiment-validation-only caveat as
  `miss_latency`), 3 untimed warm-up passes.
- Raw output filename(s): `data_raw/skylark/inclusion_policy/<pairing>/inclusion_policy_{calibration,base,rep1,rep2}_{random,sequential}_<ts>.csv.gz`
- Processing: `scripts/summarize_raw.py` per raw file → `data_processed/skylark/inclusion_policy/<pairing>/*_summary_<ts>.csv` → `scripts/classify_inclusion_policy.py` (reads raw base/random data directly) → `scripts/plot_inclusion_policy.py` (matplotlib confirmed working this session, no plotting failure).

**Same three caveats as Sunbird's writeup apply here (assumed line
size — resolved per-pairing above, not a blanket assumption; DTLB pressure
at large eviction footprint; L2 target's index not fitting in one page) —
see `data_raw/sunbird/README.md`'s inclusion_policy/ section for the full
argument. One ADDITIONAL caveat specific to this machine, more load-bearing
than usual: `CAPACITY_RESULTS.md`'s LLC value for Skylark (8,388,608 B =
8 MiB) is very likely an UNDERESTIMATE of this machine's real LLC
capacity** — this machine's own capacity/ section never confirmed a clean
LLC boundary at 8 MiB; the closest thing it found was a genuine knee
starting around 16.8-21.8 MiB (three auto-detected boundary candidates in
that range), with 8 MiB sitting inside the earlier, unresolved ~4-16.8 MiB
candidate shelf rather than at a confirmed edge. If the real LLC capacity
is closer to ~20 MiB than 8 MiB, then L2_vs_LLC/L1_vs_LLC's 256 MiB
eviction footprint (32x the ASSUMED 8 MiB, per the scaling formula) is
only ~12-13x the more-plausible ~20 MiB real capacity — comfortably
enough to blow way past a boundary that size in absolute byte terms, so
this doesn't necessarily invalidate the results, but it does mean the
"32x" safety margin baked into the scaling constant is smaller than
intended for this machine specifically. Noted as a reason to read the
LLC-involving verdicts below with slightly reduced confidence, not as
grounds to discard them.

**Results, one per pairing (n=200 target/control trials each, base/random
run unless noted):**

- **L1_vs_L2** (survived-class 73.104 ticks, invalidated-class 120.0 ticks
  from `L2_to_LLC`, classification boundary 93.66 ticks): target median
  72.0 ticks (68.0% survived-like, 31.5% ambiguous, 0.5% invalidated-like),
  control median 72.0 ticks (72.0% survived-like, 27.5% ambiguous, 0.5%
  invalidated-like). Paired check (target slower than its own trial's
  control): only 11.0%. **Verdict: UNCERTAIN per the classifier** (mixed
  result), and notably weaker than Sunbird's clean 90%-survived L1_vs_L2
  result — target and control came back nearly indistinguishable here
  (72.0 ticks median, both), unlike Sunbird's own 84-vs-68 split. Read as:
  a WEAK lean toward non-inclusive (majority survived-like, negligible
  invalidated-like, same qualitative direction as Sunbird's clean result)
  rather than a clean classification — the near-identical target/control
  medians suggest this specific 32 MiB eviction footprint isn't cleanly
  differentiating "L1 survived" from "baseline single-shot overhead" the
  way Sunbird's run did, not that the underlying policy differs from
  Sunbird's.
- **L2_vs_LLC** (survived-class 83.808 ticks, invalidated-class 360.0 ticks
  from `LLC_to_DRAM`, boundary 173.70 ticks): target median 120.0 ticks
  (99.5% survived-like, 0.5% ambiguous, 0% invalidated-like), control
  median 96.0 ticks (100.0% survived-like). Paired check: 74.0% (target
  slower than its own control most of the time, even though neither
  channel crosses into the invalidated zone). **Verdict: EXCLUSIVE /
  NON-INCLUSIVE** by the classifier — but per the LLC-underestimate caveat
  above and caveat 3 (L2's index almost certainly doesn't fit in one page),
  read this as the least trustworthy of the three, same as Sunbird's own
  L2_vs_LLC pairing was its weakest link.
- **L1_vs_LLC** (survived-class 83.328 ticks, invalidated-class 360.0 ticks
  from `LLC_to_DRAM`, boundary 173.20 ticks): target median 96.0 ticks
  (100.0% survived-like), control median 72.0 ticks (100.0% survived-like).
  Paired check: 51.0%. **Verdict: EXCLUSIVE / NON-INCLUSIVE.** Notably
  DIFFERENT from Sunbird's own L1_vs_LLC result, which leaned inclusive
  (75% invalidated-like) — on Skylark, the skip-level L1 copy survived
  LLC-scale eviction pressure essentially every trial. Given the
  LLC-capacity-underestimate caveat above, this could mean either (a)
  Skylark's LLC genuinely does not maintain inclusion of L1 lines
  (unlike Sunbird's Haswell-era Xeon, a very different microarchitecture —
  AMD Zen 2 chiplet designs are not known to use an inclusive LLC the way
  older Intel monolithic ring-bus designs did), or (b) the eviction
  footprint, while 32x the assumed LLC capacity, undershoots the real one
  enough that genuine LLC-scale eviction never actually happened. (a) is
  the more likely explanation given AMD's publicly known non-inclusive L3
  design on this generation (Zen 2 "Rome") — noted here only as a
  post-hoc plausibility check, not consulted while forming the reading
  above, same discipline as Sunbird's own aside.
- Not yet done, any pairing: multiple different target addresses/sets
  (same open item as Sunbird's writeup); a dedicated re-check of whether
  256 MiB eviction genuinely saturates this machine's real (likely
  ~16-22 MiB) LLC given the capacity-underestimate caveat above; the
  huge-pages TLB mitigation noted in Sunbird's caveat 2.

**Best-guess synthesis:** all three pairings lean the SAME direction on
Skylark (non-inclusive/exclusive-like), unlike Sunbird's mixed
non-inclusive-L2/leaning-inclusive-LLC pattern. Combined with AMD Zen 2's
publicly documented non-inclusive L3 design (post-hoc plausibility check
only, per the aside above) and the L2_vs_LLC/L1_vs_LLC caveat about a
likely-underestimated LLC capacity value, the best-supported single story
for this machine is a cache hierarchy where **no level tested here is
inclusive of the level(s) below it** — L1 vs L2 leans this way weakly, and
L2 vs LLC / L1 vs LLC lean this way strongly (though the LLC-involving
pairings carry the added capacity-estimate caveat above, so "strongly"
here means "the classifier's numbers are clean," not "high confidence in
the absolute claim").

### pmu/ (Phase II — 2026-09-14)
Phase I frozen/tagged (`phase1-timing-only`) before anything below was run,
per `README.md`'s Phase Discipline. See `CLAUDE.md`'s "Phase II" subsection
and `data_processed/skylark/PHASE2_VALIDATION_TABLE.md` for the full
methodology/results write-up and literature citation — this section is the
raw-data/reproduction-detail record, same convention as Sunbird's and
Thunderbird's.

- Used the existing, now-canonical pipeline (`scripts/run_pmu_verification.sh`
  + `scripts/summarize_pmu.py`, built by Sunbird's session) unmodified — no
  new code this session.
- Core selection: session's `Cpus_allowed_list` was `0-31`. `mpstat -P ALL`
  showed cores 0 (65% busy), 2 (98%), and 3 (100%) pinned by other students'
  processes (`incl_pmu`, `cache_bench_x86 --exp nextlevel`, `latency_bench`,
  confirmed via `taskset -pc <pid>`); core 5 read 0% busy across two
  `mpstat` samples taken a few seconds apart. Core 5 used.
- Machine-specific PMU check done before the full run: this AMD Zen 2 PMU
  (`AuthenticAMD`, EPYC 7532) reliably schedules the `cache-references,
  cache-misses`, `L1-dcache-loads,L1-dcache-load-misses`, and
  `cycles,instructions` 2-event groups at 100%. **`LLC-loads`/
  `LLC-load-misses` come back `<not supported>` (not `<not counted>`) at
  every level** — a harder failure than a scheduling conflict: this PMU has
  no LLC-scoped generic-event alias perf can map to on this CPU. Also
  hand-checked: AMD's own raw uncore L3 events (`l3_accesses`, `l3_misses`,
  PMU unit `amd_l3`, found via `perf list`) fail identically, even
  system-wide (`perf stat -a`) — consistent with `perf_event_paranoid=2`
  blocking unprivileged access to the socket-scoped uncore PMU; no `sudo`
  available to check whether root access resolves it.
- Run command: `./scripts/run_pmu_verification.sh skylark 5
  L1:32768,L2:524288,LLC:8388608` (footprints from `CAPACITY_RESULTS.md`,
  same three values already used for this machine's `latency/` and
  `inclusion_policy/` runs). base_seed=12345 (repeats use base_seed+index),
  samples=1,000,000/run, batch_size=1000, warmup_passes=3, dependent load
  mode, random pattern, timestamp `20260914T002932Z`.
- Raw output: `data_raw/skylark/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz` (perf
  stat's own `-x,` CSV output, one file per group×run_tag) and
  `*_bench_*.csv.gz` (cache_bench's own CSV from the same invocation).
  Transcript: `data_raw/skylark/pmu/run_pmu_verification_20260914T002932Z.log`.
- Processed: `data_processed/skylark/pmu/{L1,L2,LLC}/pmu_summary_20260914T002932Z.csv`
  (one row per run_tag + a median-of-3 row).
- System-reported cache info (same run): `data_raw/skylark/pmu/
  system_reported_cache_info.txt` — `lscpu --caches`, full `lscpu`, and
  per-instance `/sys/devices/system/cpu/cpu5/cache/index*/` fields
  (core 5), plus a spot-check of cores 0/4/6/8/12's L3 `shared_cpu_list` to
  confirm the sharing pattern was machine-wide, not core-5-specific.
- Headline results (full detail and caveats:
  `data_processed/skylark/PHASE2_VALIDATION_TABLE.md`): size/ways/sets/line
  match exactly across Phase I timing, system-report, AND Agner Fog's Zen 2
  literature table (Table 22.3, p. 237) at L1D and L2 — system-reported L2
  associativity independently confirms Phase I's confound-blocked 8-way
  best guess, same story as Sunbird's L2 row. **LLC size: system-reported
  16,777,216 B (16 MiB) confirms Phase I's own suspicion that its
  8 MiB `CAPACITY_RESULTS.md` value was an underestimate**, landing almost
  exactly at the bottom of Phase I's ~16.8-21.8 MiB re-look bracket.
  **LLC associativity disagrees (Phase I best-guess 8-way vs.
  system-reported 16-way)**, same confound-resolution pattern as Sunbird's
  and Thunderbird's LLC/L2 rows. **Line size disagrees**: Phase I confirmed
  128 B at the LLC-region transition by two independent methods, but
  system-report says 64 B uniformly at every level — flagged as an open
  question (leading hypothesis: Zen 2's adjacent-line/stream prefetcher
  creating an apparent 128 B granularity for a stride-based probe once the
  working set spills past L2, not a real doubled physical line — not
  confirmed this phase). **Sharing scope is the standout finding**: this
  LLC is shared by only 2 logical cores per instance (`shared_cpu_list`
  e.g. `4-5`), not the whole socket as Phase I guessed — resolved via AMD's
  published EPYC 7532 spec (8 CCDs × 2 CCX/CCD × 16 MiB/CCX = 256 MiB total
  L3 per socket, this SKU's known "cache-doubled" binning that runs only 2
  of 4 possible cores per CCX while granting each CCX its full L3), not a
  measurement artifact.

### software_hit_rate/ (Problem 8.5 — 2026-09-14)
Software-only, timing-derived cache hit-rate estimator
(`main_code/software_hit_rate/`, no PMU access anywhere in that file) plus
its Phase-II PMU validation, same pipeline and redesigned harness used on
Sunbird and Thunderbird (see `data_raw/sunbird/README.md`'s and
`data_raw/thunderbird/README.md`'s own `software_hit_rate/` sections for the
original design, the invalid first attempt, and the 2026-09-14 redesign
that fixed it — none of that history is re-derived here). See
`main_code/software_hit_rate/software_hit_rate.h`'s module doc comment for
the full method (calibration -> ROC threshold selection -> Rogan-Gladen
prevalence correction -> bootstrap CI).

#### Sweep (parts 1-3, standalone, no perf)
- Source file(s): `main_code/software_hit_rate/software_hit_rate.{c,h}`,
  `scripts/run_software_hit_rate_sweep.sh`,
  `scripts/summarize_software_hit_rate.py`, `scripts/plot_software_hit_rate.py`.
- Run command: `./scripts/run_software_hit_rate_sweep.sh skylark 10
  4096,16384,32768,65536,131072,262144,524288,1048576,4194304,8388608,16777216,31457280,67108864,134217728,268435456,536870912`
  — core=10 (same core as this machine's capacity/associativity runs;
  confirmed idle via two `mpstat -P 10` samples a few seconds apart
  immediately before running, both 100% idle), seed=12345,
  calib_samples=20000, test_samples=50000, bootstrap_reps=2000,
  pattern=random, timestamp `20260914T041244Z`. Footprint list is the
  script's own default sweep with **524,288 B (this machine's own L2
  boundary) inserted** — the unmodified default only contains Sunbird's L2
  value (262,144 B), not Skylark's, and this project's explicit-only
  discipline says not to reuse another machine's boundary silently.
- **Bug found and fixed in `run_software_hit_rate_sweep.sh` itself, not just
  worked around**: at the time this run started, the script unconditionally
  hardcoded `--boundary L1:32768 --boundary L2:262144 --boundary
  LLC:31457280 --boundary DRAM:536870912` (Sunbird's own values) into its
  `plot_software_hit_rate.py` call — a latent bug for any non-Sunbird
  machine (L1 happened to match Skylark's own boundary by coincidence, both
  machines having a 32 KiB L1, but L2/LLC did not: Skylark is 524,288 B /
  8,388,608 B, not 262,144 B / 31,457,280 B). This run's own plots were
  first regenerated by hand with the correct markers (the underlying
  data/CSV was never affected, only the reference lines drawn on top of
  it): `python3 scripts/plot_software_hit_rate.py --summary
  data_raw/skylark/software_hit_rate/hit_rate_sweep_20260914T041244Z.csv
  --calib-raw data_raw/skylark/software_hit_rate/raw/hit_rate_536870912_20260914T041244Z.csv.gz
  --boundary L1:32768 --boundary L2:524288 --boundary LLC:8388608 --boundary
  DRAM:536870912 -o data_processed/skylark/software_hit_rate/plots --machine
  skylark`. The script itself was then fixed the same session: it now takes
  an optional 4th `boundary_spec` argument (`L1:<bytes>,L2:<bytes>,
  LLC:<bytes>,DRAM:<bytes>`, same `<level>:<bytes>` format
  `run_hit_rate_pmu_validation.sh` already uses) and builds its
  `--boundary` flags from that instead of the hardcoded values, defaulting
  to Sunbird's own boundaries only when the argument is omitted (preserving
  the script's prior default behavior for a bare Sunbird re-run). A future
  run on any other machine should pass this argument explicitly rather than
  relying on the default, same explicit-only discipline as the footprint
  list itself.
- Raw output: `data_raw/skylark/software_hit_rate/raw/hit_rate_<bytes>_20260914T041244Z.csv.gz`
  (full per-access CSV per point). Transcript:
  `data_raw/skylark/software_hit_rate/run_software_hit_rate_sweep_20260914T041244Z.log`.
- Processed: `data_raw/skylark/software_hit_rate/hit_rate_sweep_20260914T041244Z.csv.gz`
  (one row per footprint, gzipped by hand after the plot regeneration below
  consumed it — see the `.gitignore` note under the PMU validation
  subsection); plots (regenerated with correct boundaries, see
  above): `data_processed/skylark/software_hit_rate/plots/{hit_rate_sweep,calibration_distributions}.{png,pdf}`.
- Headline results: Hhat=1.0000 for every footprint through 131,072 B,
  i.e. **including this machine's own 32,768 B L1 boundary itself** — unlike
  Sunbird, whose Hhat dipped to 0.8664 right at its own exact L1 boundary,
  Skylark shows no such dip at 32,768 B. Falls off gradually and
  monotonically from there: 262,144 B->0.9958, 524,288 B (L2
  boundary)->0.9396, 1,048,576 B->0.8017.
  **Non-monotonic anomaly, not smoothed over**: Hhat partially *recovers*
  above that dip — 4,194,304 B->0.9202 and 8,388,608 B (this machine's
  `CAPACITY_RESULTS.md` LLC value, itself already flagged elsewhere in this
  README as a likely underestimate)->0.9198 — both higher than the
  1,048,576 B point, before resuming its fall at 16,777,216 B (this
  machine's Phase-II system-reported *true* LLC capacity)->0.8538,
  31,457,280 B->0.4408, and on down to 0.0000 at the 536,870,912 B DRAM
  reference point. Not re-investigated further this session (Phase I
  timing-only, no capacity/associativity re-run triggered by this), but a
  plausible reading given the deep hierarchy anomalies already documented
  elsewhere in this file: 1,048,576 B sits inside the same broad,
  PROVISIONAL-WEAK ~4-16.8 MiB "one continuous ramp, no confirmed shelf"
  candidate region this machine's own `capacity/` section already flags as
  unresolved (see that section above) — a genuinely noisy, not-yet-settled
  part of this machine's own capacity curve, not obviously a software_hit_rate-specific
  artifact.

#### PMU validation (part 4)
- Source file(s): `scripts/run_hit_rate_pmu_validation.sh`,
  `scripts/compare_hit_rate_pmu.py` (unmodified from Sunbird's/Thunderbird's
  redesigned version — no Skylark-specific code path exists or was needed).
- Run command: `./scripts/run_hit_rate_pmu_validation.sh skylark 10
  L1:32768,L2:524288,LLC:8388608,DRAM:536870912` (core 10, re-confirmed idle
  via `mpstat -P 10` immediately before running — same core as the sweep
  above and this machine's capacity/associativity runs). Footprint values
  are this machine's own `CAPACITY_RESULTS.md` numbers, same three L1/L2/LLC
  values already used for this machine's `latency/`, `inclusion_policy/`,
  and `pmu/` sections. Tested footprints after the script's own L1/L2/LLC
  halving (a "safely inside the level" point, not the exact edge — see
  Sunbird's writeup for why): L1=16384, L2=262144, LLC=4194304,
  DRAM=536870912 (unchanged). base_seed=12345 (repeats use base_seed+index),
  timestamp `20260914T042323Z`.
- Raw output: `data_raw/skylark/software_hit_rate/pmu/{L1,L2,LLC,DRAM}/
  *_{calibonly,bench,hitlatpmu,perfstat}_{base,rep1,rep2}_20260914T042323Z.csv.gz`
  (gzipped by hand after the run — `run_hit_rate_pmu_validation.sh` does not
  compress its own output the way `run_software_hit_rate_sweep.sh` does;
  `.gitignore` only tracks `data_raw/**/*.csv.gz`, not bare `.csv`, so this
  step is required before committing, same as every other machine's raw
  data here). Transcript:
  `data_raw/skylark/software_hit_rate/pmu/run_hit_rate_pmu_validation_20260914T042323Z.log`.
- Processed: `data_processed/skylark/software_hit_rate/pmu_validation_20260914T042323Z.csv`.
- Headline results (median of base+2 repeats):

  | Level | Tested footprint | Hhat | H_pmu | rel. error |
  |---|---|---|---|---|
  | L1  | 16,384 B    | 1.0000 | 0.6758 | 48.0% |
  | L2  | 262,144 B   | 0.9993 | 0.9916 | 0.78% |
  | LLC | 4,194,304 B | 0.8775 | 0.5532 | 57.9% |
  | DRAM | 536,870,912 B | 0.0001 | 0.5093 | 99.98% |

  **L2's agreement is the tightest of any machine/level yet tested in this
  investigation (0.78%, vs. Sunbird's 12.4% and Thunderbird's 6.4% at their
  own L2 rows)** — a clean corroboration on this machine specifically.

  **L1's 48.0% disagreement is worse than either prior machine (Sunbird
  30.1%, Thunderbird 0.08%) and is best explained by a limitation this
  machine's own Phase II PMU work already documented, not a new bug.**
  `data_processed/skylark/PHASE2_VALIDATION_TABLE.md`'s PMU caveats already
  flag that this AMD Zen 2 PMU's generic `cache-references`/`cache-misses`
  alias is unreliable at L1 scale specifically: at an L1-resident footprint
  it recorded only ~69,146 `cache-references` against ~7.6 million
  `L1-dcache-loads` in the same earlier run (a ~110x gap), suggesting the
  generic alias tracks something closer to L2-scope request traffic than
  true L1 traffic on this CPU, so its miss-rate ratio is unstable at the
  small absolute counts an L1 footprint produces. This run's own raw counts
  reproduce exactly that signature: only 41,019-43,916 `cache-references`
  per run at the L1 footprint (same order of magnitude as the earlier
  ~69,146), with `cache-misses` at 13,298-14,251 of those — a ~31-33% "miss"
  rate that is very plausibly this same small-sample AMD-generic-counter
  noise, not a real ~32% L1 miss rate for a footprint that fits entirely in
  L1. Hhat=1.0000 (from the unwrapped, non-PMU measurement) is the more
  trustworthy number here, consistent with every other machine's clean L1
  result.

  **LLC's 57.9% disagreement carries an extra caveat specific to this
  machine, on top of the usual single-threshold-classifier limitation
  documented on Sunbird/Thunderbird**: the *tested* footprint here
  (4,194,304 B, i.e. half of this machine's `CAPACITY_RESULTS.md` LLC value)
  is only 4 MiB, but this README's `pmu/` section above already established
  that Skylark's `CAPACITY_RESULTS.md` LLC value (8 MiB) is itself a
  documented underestimate — the Phase-II system-reported true LLC capacity
  is 16 MiB. Half of the *true* boundary would be 8 MiB, not 4 MiB, so this
  "LLC" row is actually testing a footprint that sits in the tail of the
  L2-to-LLC transition rather than safely inside the real LLC — consistent
  with Hhat=0.8775 (still fairly high, not yet DRAM-like) and the
  intermediate, disagreeing-with-itself H_pmu media (0.5443-0.5557 across
  the 3 runs) rather than a clean, confidently-classified LLC-scale result.
  Not re-run at a corrected 8,388,608 B (half of 16,777,216 B) this
  session — flagged as the natural follow-up rather than done here, to keep
  this run's footprint choice traceable to the same `CAPACITY_RESULTS.md`
  values already used for every other Skylark experiment.

  **DRAM's near-total disagreement (99.98%) is the same expected,
  already-documented generic-counter-semantics limitation as Sunbird's
  (99.9%) and Thunderbird's (100%) DRAM rows** — this machine's raw
  `DRAM_perfstat` output shows `cache-misses`/`cache-references` ratios
  implying roughly a ~49-51% "hit" rate for a fully random 512 MiB working
  set that should almost never hit, the same generic-alias-does-not-mean-
  any-cache-vs-DRAM finding this project has now reproduced on all 3
  machines tested. Hhat's near-zero (0.0000-0.0015 across 3 runs) is the
  trustworthy number; H_pmu is not, at this footprint, on this PMU.

  **Overall reading, consistent with both prior machines**: this estimator
  reliably detects L1/L2-scale residency (L2's 0.78% error is this
  investigation's cleanest result yet) but cannot be validated as a general
  "any cache level" detector at LLC/DRAM scale — partly the classifier's own
  single-threshold design (documented on Sunbird/Thunderbird), and on this
  machine specifically also compounded by the generic AMD PMU counter's own
  L1-scale and LLC-scope limitations already flagged in this machine's
  `pmu/` section above. `nmi_watchdog=1` and `systemd-detect-virt: none`
  (bare metal) were both re-checked and match Sunbird's own environment —
  ruled out as an explanation for anything specific to this machine's
  numbers.

## Final Inferred Cache Table (Skylark, Phase I best guess, 2026-09-13)

Lives at `data_processed/skylark/FINAL_CACHE_TABLE.md`, alongside this
machine's other processed benchmark outputs (`capacity/`, `line_size/`,
`associativity/`, `latency/`, `inclusion_policy/`), same convention as
Sunbird's. The full per-pairing reasoning and caveats behind it remain in
this file's `associativity/` and `inclusion_policy/` sections above.

## Reservation Log (if applicable)
- Reserved core/package: 
- Time window: 
