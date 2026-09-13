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
- Source file(s): 
- Run command + arguments: 
- Dependent-chain batch size N used: 
- Regular vs. randomized control included? 

### inclusion_policy/
- Source file(s): 
- Run command + arguments: 
- Eviction/reload construction: 

### pmu/ (Phase II only — leave blank until Phase I is frozen)
- `perf list` output filename: 
- Events collected + exact semantics on this CPU: 
- Run command + arguments: 

## Reservation Log (if applicable)
- Reserved core/package: 
- Time window: 
