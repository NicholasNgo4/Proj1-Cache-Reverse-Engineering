# thunderbird — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: thunderbird.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): Ampere Q80-30 (`lscpu` model name: Neoverse-N1), 80 cores, 1 socket
- ISA / architecture: aarch64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Ampere / ARM Neoverse N1, per `MACHINE_RESEARCH.md`
- Introduction year (per the team's stated year convention): 2020 (per `MACHINE_RESEARCH.md`)
- Process node (if reliably documented): 7 nm (per `MACHINE_RESEARCH.md`)
- Kernel version: Linux 5.14.0-611.54.1.el9_7.aarch64
- Page size: 4096 bytes (`getconf PAGESIZE`)
- SMT siblings idle during runs? N/A — `lscpu` reports "Thread(s) per core: 1" for this CPU (no SMT). This session's cgroup grants `Cpus_allowed_list: 0-4` only (not the full 0-79); of those, cores 1 and 2 were occupied by other students' active processes (`python3` at ~80% CPU, a process named `associativity` at 100% CPU) at the time of core selection — confirmed via `/proc/stat` idle-time sampling, not just a `ps` snapshot. Ran on core 3, which showed near-100% idle time before the run.

## Environment
- Compiler + version: GCC 11.5.0 (Red Hat 11.5.0-14)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): ARM `CNTVCT_EL0` (DSB+ISB fenced start/stop), batched: N=1000 dependent pointer-chase steps timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/aarch64/timer_arm.h`, `main_code/common/benchmark.c`. **Pre-flight sanity check (not committed, ad hoc):** `CNTFRQ_EL0` = 25,000,000 Hz (40 ns/tick resolution), confirmed readable unprivileged and monotonic across repeated reads, and a manual 8-trial/100,000-step dependent chase over a 4096-node (L1-resident) ring gave consistent ~3.3 ns/step — non-zero, non-negative, not erratic. This 40 ns/tick resolution is coarse relative to individual accesses, but the benchmark's batching (dividing total ticks by N=1000+ steps) makes per-access quantization error negligible; see "Known issues" below for a downstream consequence of this coarse resolution.
- Affinity/binding command used: `taskset -c 3 ./cache_bench ...` (see `scripts/run_capacity_full.sh` and the manual follow-up described below)
- NUMA/locality method: no explicit NUMA pinning beyond CPU affinity; single NUMA node (node0, all 80 CPUs) per `lscpu -e=CPU,CORE,SOCKET,NODE`, so first-touch locality is moot on this machine.
- Git commit hash of the code used for these results: `881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9` (recorded at README-fill time; the actual runs spanned this and the immediately preceding commit — no code changes to `main_code/` occurred during the session)

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/aarch64/timer_arm.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments:
  - `scripts/run_capacity_full.sh thunderbird 3` — ran the coarse sweep (1 KiB-64 MiB) and its tail extension (64 MiB-256 MiB) successfully, but its automatic boundary detection returned **no boundaries** (see "Known issues" below), so its own dense-sweep/repeat/plot stages never ran and it exited with a `matplotlib`-missing error at the plotting step.
  - Everything past the coarse+tail stage was completed manually, using the same `taskset -c 3 ./cache_bench --experiment capacity ...` invocation pattern with `--samples 1000000 --batch-size 1000 --warmup-passes 3 --seed 12345`, both `--pattern random` and `--pattern sequential`:
    - Dense window A (L1-plateau edge / start of ramp): `--min-bytes 12288 --max-bytes 786432 --points-per-octave 48`
    - Dense window B (dominant steep transition + a noisy zone): `--min-bytes 4194304 --max-bytes 268435456 --points-per-octave 48`, plus 2 independent repeats of the identical command (reproducibility check on the noisiest region, same rationale as Sunbird's window C)
    - Tail-extension window (checking whether the curve actually plateaus past the original 256 MiB coarse ceiling): `--min-bytes 268435456 --max-bytes 1073741824 --points-per-octave 48`, plus 2 independent repeats (the last 2 of these were run inside a detached `tmux` session, `data_raw/thunderbird/capacity/tail_repeats.sh`, for resilience against the remote session restarting mid-run — see that script for the exact resumed commands)
- Sample count: 1,000,000 timed accesses per (size, pattern) point; warm-up (3 full untimed chase passes) excluded from that count
- Random seed(s): 12345 (xorshift32, `make_random_cycle`); sequential-pattern runs use `make_sequential_cycle` (no seed/randomness)
- Raw output filename(s): `data_raw/thunderbird/capacity/capacity_coarse_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_coarse_ext_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseA_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseB_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseB_rep{1,2}_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseTail_{random,sequential}_20260909T001422Z.csv.gz`, `capacity_denseTail_rep{1,2}_{random,sequential}_20260909T001422Z.csv.gz` (gzipped after the fact per the repo-wide `.gitignore` convention — ~9-10x smaller measured on this data; summaries in `data_processed/` were already generated from the uncompressed originals before compression, so they're unaffected — `zcat`/`gunzip` a file to inspect the raw per-batch rows). Full transcript (kept uncompressed per `.gitignore`'s `!data_raw/**/*.log` rule): `run_capacity_full_20260909T001422Z.log` (automated portion) and `manual_followup_20260909T001422Z.log` (everything after boundary detection returned nothing).
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/thunderbird/capacity/<name>_summary.csv` for each file above (run against the uncompressed CSVs before they were gzipped), then `python3 scripts/plot_capacity.py <all summary.csv...> -o data_processed/thunderbird/capacity/plots --machine thunderbird --boundary 65536 --boundary 33554432 --boundary 268435456` for the final curve and box-plot figures. The 3 `--boundary` values (64 KiB, 32 MiB, 256 MiB) were picked by eye from the dense data (see "Known issues"), not from `detect_cache_hierarchy.py`'s output.
- Excluded runs (if any) and reason: none — all raw files listed above are included in the final plots.

- **Known issues / methodology notes (read before trusting any boundary number at face value):**
  1. **`detect_cache_hierarchy.py`'s default thresholds do not work on this machine's counter.** Its default `--min-abs-ticks 3.0` was implicitly calibrated to x86 TSC-scale ticks (Sunbird's ticks/access run in the tens-to-hundreds). Thunderbird's `CNTVCT_EL0` runs at only 25 MHz, so ticks/access over the *entire* 1 KiB-1 GiB range are just ~0.08-2.4 — the absolute-tick threshold is unreachable regardless of `--rel-threshold`, so the detector silently printed zero boundaries instead of erroring, and `run_capacity_full.sh`'s dense-sweep-per-boundary loop consequently never ran. Loosening `--min-abs-ticks` to compensate (tried `--min-abs-ticks 0.02 --rel-threshold 0.15`) does not give a clean answer either: this machine's curve is a smooth continuous ramp rather than discrete steps, so the detector's "consecutive points must not regress" rule over-fragments it into ~8 spurious "levels" instead of the true handful of transitions. **All boundary values used for dense-sweep windows and plot annotations here were chosen by eyeballing the coarse-then-dense plots, not from this script's output.** This is a real bug/limitation in the shared script worth fixing later (e.g. a threshold relative to `CNTFRQ_EL0` instead of an absolute tick count), not just a Thunderbird-specific quirk — flagged in `CLAUDE.md` for whichever machine hits it next.
  2. **`matplotlib`/`numpy` were not installed** for this user on Thunderbird, so `run_capacity_full.sh` died at its final plotting step even though all the sweep data it collected was fine. Fixed with `python3 -m pip install --user matplotlib numpy`.
  3. **Curve shape is genuinely different from Sunbird's (3 flat/ramp transitions).** Thunderbird shows: a flat plateau from 1 KiB to ~64-75 KiB (~0.084 ticks / ~3.4 ns, matches the L1-resident sanity-check number above); a long, shallow, continuous ramp from ~75 KiB up through ~8 MiB (no flat shelf); a steep, dominant climb from ~16 MiB to ~60 MiB (0.8 to ~2.1 ticks); a visibly noisy ~16-70 MiB zone (individual points show 20-65% run-to-run spread across the denseB + 2 repeats, even after averaging — see `capacity_boxplots.png`); then a slow continued climb from ~70 MiB to ~256 MiB before finally flattening. **The topmost region was explicitly checked for a genuine plateau, not assumed:** across the 256 MiB-1 GiB tail-extension window (97 points x 3 independent runs = the main sweep + 2 repeats), run-to-run spread averages ~2.0% (comparable to Sunbird's confirmed-plateau spread of ~3.6%, under 2% at many points), and the residual growth from the first quarter of that range to the last quarter is only +3.4% over a 4x size increase — this is a confirmed flat DRAM-latency plateau at ~2.3-2.4 ticks/access (~92-96 ns/access), not a region still climbing. The noisy 16-70 MiB zone, by contrast, is a real transition-region property (like Sunbird's 19-25 MiB zone), not something more averaging alone cleans up — treat any single-run boundary estimate inside that zone as unreliable.
  4. Noise in the 16-70 MiB zone is consistent with transient scheduling interference on this shared, multi-user machine (this session only had exclusive-in-practice use of core 3; cores 1-2 in the allowed cpuset were actively used by other students during setup), matching the same kind of finding Sunbird's README documents in more detail for its own transition region.
- `scripts/plot_capacity.py` combines overlapping (pattern, size) rows across the coarse/dense/repeat inputs by averaging medians and widening whiskers to the union of p5/p95, annotating each combined box with the number of runs and their run-to-run spread — the terminal output from the final `plot_capacity.py` call (not separately saved as a file) lists every point it combined, most of them exactly the noisy 16-70 MiB points described above.

### line_size/
- Source file(s): `main_code/common/{main.c,line_size.c,line_size.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/aarch64/timer_arm.h`, `main_code/common/timer.h`, `scripts/{run_line_size.sh,detect_line_size.py,plot_line_size_family.py,plot_line_size_offset.py,plot_line_size.py}`
- Build command: `make` (from repo root)
- Run command + arguments: `scripts/run_line_size.sh thunderbird 3 65536,1048576,31457280` — boundaries taken from `CAPACITY_RESULTS.md`'s consolidated L1/L2/LLC values for this machine (64 KiB / 1 MiB / ~30 MiB), matching the values already used for this machine's associativity run below. Runs both of the script's independently-designed methods per level: **Method A** (family of curves — hold footprint/timer/samples/warm-up constant, sweep byte stride across `8,16,32,64,128,256` at a fixed footprint window scoped to that level, then re-test a manually-chosen candidate stride across an 8-byte-granularity bracket at 8 different node-0 offsets `0,8,...,56B` to check the transition isn't an alignment artifact) and **Method B** (single curve — fix footprint at ~2x the level's boundary, sweep stride linearly, read the line size off where the ramp saturates via `detect_line_size.py`). Core 3 (same core as the capacity run, selected there after the `/proc/stat` idle-time check documented in "Machine Identification" above).
  - **This took 5 separate invocations across the session, not one clean run — record kept honestly rather than only citing the final numbers:**
    1. `20260912T145452Z`: full pipeline at **stale** boundaries `65536,33554432,268435456` (32 MiB/256 MiB were this session's original, since-superseded capacity-boundary guesses, predating the `CAPACITY_RESULTS.md` correction) — no usable estimate at any level from either method; that superseded run's raw data (`level_33554432/`, `level_268435456/`) is **not** in the repo (excluded per the commit that landed this experiment, since it tested boundaries this machine's own capacity data no longer supports).
    2. `20260912T204851Z`: level `65536` (L1) alone, Method-A step-4 candidate `64B` (manually read off `line_size_family_curve.png`) — see results below.
    3. `20260912T212413Z`: levels `1048576,31457280` (L2, LLC) together, coarse pass only — neither level's per-stride elbow table agreed cleanly enough to auto-pick a step-4 candidate; pipeline printed "no level/method produced a usable estimate" and both step-4 stages were skipped pending a manually-chosen candidate.
    4. `20260912T214644Z`: level `1048576` (L2) alone, Method-A step-4 candidate `64B` (manual) — see results below.
    5. `20260912T215546Z`: level `31457280` (LLC) alone, Method-A step-4 candidate `128B` (manual) — see results below.
  - A further ad hoc reproducibility check (not run through `run_line_size.sh`, so **no accompanying transcript** — flagged rather than hidden) reran LLC's whole step-4 bracket (strides `104,112,120,128,136,144,152B` x offsets `0,8,...,56B`) at a second seed: raw files `data_raw/thunderbird/line_size/level_31457280/refine_*_off*_rep_20260912T221747Z.csv.gz`, processed into `data_processed/thunderbird/line_size/level_31457280/refine_*_off*_repOnly_summary.csv`. A separate, earlier ad hoc rep (`family_*_rep_20260912T213328Z.csv.gz`/`..._repOnly_summary.csv`, seed 12349) re-ran LLC's whole coarse family sweep between runs 3 and 5 above, apparently to check the "no clean split" coarse result was itself reproducible before hand-picking the 128B candidate — it was (same lack of a clean per-stride elbow agreement on repeat).
- Sample count: 1,000,000 timed accesses per (footprint, stride, pattern[, offset]) point (`SAMPLES=1000000 BATCH=1000` in `run_line_size.sh`, confirmed in every raw `.csv.gz` header: `samples_requested=1000000 batch_size=1000 num_batches=1000`) — i.e. each point in the counts below is itself a median/mean over 1,000 batches of 1,000 dependent-chase accesses; warm-up (2 untimed passes for Method A, 3 for Method B) excluded. Random seed(s): base runs 12345 (`make_random_cycle_strided`); the two undocumented ad hoc reproducibility reps above used 12349 (family-sweep repeat) and 12346 (offset-bracket repeat); sequential-pattern curves use `make_sequential_cycle_strided` (no seed).
- **Total data points collected (current, non-superseded dataset only — counted directly from the committed summary CSVs, not from a run log, since none of the 5 logs prints a running total):** 9,200 rows across 278 `*_summary.csv` files, split as L1 (`level_65536/`) 2,364 rows/70 files, L2 (`level_1048576/`) 2,364 rows/70 files, LLC (`level_31457280/`) 4,472 rows/138 files (the LLC total includes the two undocumented reproducibility reps above). Each row is one plotted point; each aggregates 1,000,000 raw timed accesses per the sample count above.
- **Per-level results (see "Known issues" below for how much to trust each):**
  - **L1** (`level_65536/`): Method A candidate **64B**, offset-refine elbow identical (82,560 B, 1.00x spread) across **all 8/8** offsets — the cleanest result of the three. Method B (single-curve): no transition detected in the coarse sweep. Cross-method summary: "AGREES on 64B" (only Method A produced an estimate).
  - **L2** (`level_1048576/`): Method A candidate **64B**, offset-refine elbow **6/8** offsets landing exactly on 1,664,448 B, the other 2 (offsets 24B, 40B) on 1,868,288 B instead (1.12x spread) — majority agreement, not full 8/8; the run's own text log says "elbow stable across the 8/8 offsets with a detectable elbow" but that only means all 8 offsets produced *some* elbow value, not that all 8 agreed on the same one — see the per-offset table in `run_line_size_20260912T214644Z.log` line 234-241 before citing this as cleanly as L1. Method B: no transition detected. Cross-method summary: "AGREES on 64B" (only Method A).
  - **LLC** (`level_31457280/`): Method A candidate **128B**, offset-refine elbow **7/8** offsets landing exactly on 49,935,232 B, offset=0B alone on 56,050,432 B (1.12x spread) — majority agreement, same caveat as L2 above. The undocumented seed-12346 reproducibility repeat (see above) reproduces the same ramp shape and elbow region (~44-56 MiB) at every offset spot-checked, consistent with (not conclusive proof of) this being a real transition rather than a one-seed artifact. Method B: no transition detected. Cross-method summary: "AGREES on 128B" (only Method A). This level sits inside this machine's own capacity data's documented noisy ~16-70 MiB transition zone (see capacity/ section above) — a genuinely distinct, deeper line-size reading here is plausible but worth the Phase II PMU check more than L1/L2's results are.
- Notes on alignment/candidate strides tested: coarse stride candidates `8,16,32,64,128,256B` (both patterns) at every level, per the script's default (the assignment's own example list); Method A's step-4 bracket around each manually-chosen candidate always used 8-byte granularity (finest possible spacing given `struct node` is one 8-byte pointer, see `run_line_size.sh`'s own header comment) across 8 fixed node-0 offsets `0,8,16,24,32,40,48,56B`. Method B's coarse sweep at every level flagged several isolated single-stride "spike" points (7 at L1, 7 at L2, 5/7 across LLC's two coarse runs) as probable page-aliasing artifacts rather than real signal — did not affect Method A's per-level results since Method A never used Method B's coarse data.

- **Known issues / methodology notes (read before citing any of these numbers):**
  1. **This is a FROZEN PHASE-I TIMING-ONLY result** (every run's log ends with this reminder verbatim) — none of the L1/L2/LLC line-size numbers above have been compared against PMU counters or this CPU's documented/system-reported line size yet; that comparison is Phase II, not done here.
  2. **Neither level's Method B (single-curve, ramp-saturation) ever detected a transition**, at any of the 5 invocations — every single-curve coarse sweep on this machine reports "no transition detected in the coarse sweep; skipping dense/repeat stages." All three cited line-size numbers above rest entirely on Method A; this machine has not produced the stronger two-independent-methods agreement that (per the script's own step-5 rationale) would be the best Phase-I evidence. Not yet root-caused — could be this machine's shallow-ramp capacity curve shape (documented in capacity/ above) making a fixed-footprint stride-sweep ramp harder to saturate cleanly than on a machine with sharper capacity transitions, but that's a hypothesis, not confirmed.
  3. **L2 and LLC's offset-refine agreement is majority (6/8, 7/8), not the full 8/8 L1 achieved** — see the per-level bullets above. Treat L1=64B as the most solid of the three; L2=64B and LLC=128B as real but slightly softer results, each with 1-2 outlier offsets not yet explained (not investigated further this session).
  4. **Two ad hoc reproducibility reruns exist in the raw/processed data with no accompanying `run_line_size_*.log` transcript** (the seed-12349 family-sweep repeat and the seed-12346 offset-bracket repeat, both LLC-only, both described above) — they were run and processed (summarized into `*_repOnly_summary.csv`) outside `run_line_size.sh`'s own logging, so their exact invocation command isn't recorded anywhere; only the raw CSV headers (which do record the seed and stride/offset/footprint parameters) and the resulting summary CSVs survive as evidence. Flagged as a process gap for future sessions to avoid repeating, not silently backfilled with a guessed command line.
  5. Just as with capacity, `detect_line_size.py`/`plot_line_size_family.py` do not auto-pick a Method-A candidate stride on this machine (or any machine — no-auto-detection is a deliberate design choice per the script's header, not an ARM-specific issue); every candidate above (64B, 64B, 128B) was chosen by eye from that level's `line_size_family_curve.png`, not computed automatically.

### associativity/
- Source file(s): `main_code/common/{main.c,associativity.c,associativity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/aarch64/timer_arm.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run command + arguments: `scripts/run_associativity_full.sh thunderbird 4 65536,1048576,31457280` — explicit `cache_bytes` override (required by the script for a "final" run; auto-detect is opt-in only), values taken from this team's consolidated `CAPACITY_RESULTS.md` (L1=64 KiB, L2=1 MiB, LLC≈30 MiB) per that file's own instruction that it, not the older per-level `CAPACITY_INFERENCE_STATUS.md` confidence gate, is the source to use for this run. Core 4 was selected after an idle-time check (`/proc/stat` sampled over 1s, `mpstat` unavailable on this machine): cores 0-4 of this session's `Cpus_allowed_list: 0-4` cgroup were all lightly loaded by this session's own IDE/tooling processes (no other students' processes observed), core 4 was the quietest (~1% busy). One command ran the full pipeline for all 3 levels: base sweep `num_ways=2-40` (both patterns) → automatic knee detection → 2 reproducibility repeats (seeds 12346, 12347) → plots, per level.
- Sample count: 1,000,000 timed accesses per (num_ways, pattern) point; warm-up (3 full untimed chase passes) excluded
- Random seed(s): base=12345, repeats=12346/12347 (`make_random_cycle_strided`); sequential-pattern runs use `make_sequential_cycle_strided` (no seed)
- Conflict-set construction method: node-to-node stride fixed at the level's own capacity (`--cache-bytes`, validated only as a multiple of the 4096 B page size, NOT required to be a power of two — see `main_code/common/main.c`/`associativity.h`), so every probed node collides into the same cache set by construction regardless of unknown line size/way count; `num_ways_probed` swept 2-40, `--way-step 1`.
- Raw output filenames: `data_raw/thunderbird/associativity/{L1,L2,L3_LLC}/associativity_{base,rep1,rep2}_{random,sequential}_20260912T224539Z.csv.gz`; full transcript `data_raw/thunderbird/associativity/run_associativity_full_20260912T224539Z.log`.
- Processing: `scripts/summarize_raw.py` per raw CSV -> `data_processed/thunderbird/associativity/<level>/{base,rep1,rep2}_{random,sequential}_summary_20260912T224539Z.csv`; plots regenerated by hand (not the pipeline's own auto call) via `scripts/plot_associativity.py` with an explicit `--estimate`, for the reason in note 1 below.

- **Known issues / methodology notes (read before citing any of these numbers):**
  1. **`detect_associativity.py`'s default `--min-abs-ticks 3.0` is unreachable on this machine, same root cause as the capacity detector's documented failure (`CAPACITY_INFERENCE_STATUS.md`).** `CNTVCT_EL0` at 25 MHz keeps every level's ticks/access under ~1.1 across the whole `num_ways=2-40` range, so the pipeline's automatic detection returned "none" (reproducibly, across base+both repeats) for all 3 levels on the first pass. Re-ran `detect_associativity.py` by hand per level with a rescaled `--min-abs-ticks` chosen by eye from that level's own curve (see note 2 for why the value differs per level) — analogous to the `--min-abs-ticks 0.5` fix already documented for capacity, just needing a smaller value here since associativity's ticks/access are themselves smaller than capacity's.
  2. **L2 and LLC's detected "knees" are very likely the same universal large-stride confound already documented at length in `CLAUDE.md`'s associativity section (Sunbird + Upgrade, 2026-09-11/12), not each level's real associativity — treat both as unresolved, not just L1 as confirmed.** All three levels' curves show the *same* small first bump at `num_ways=5` (baseline ~0.08-0.13 ticks -> ~0.16-0.23 ticks): expected for L1 (`cache_bytes=65536` is exactly this level's own capacity), but this bump also appears at L2 (`cache_bytes=1048576`) and LLC (`cache_bytes=31457280`) — both are exact multiples of 65536 (16x and 480x respectively), so a stride of L2's or LLC's own capacity *also* lands every probed node in the same L1 set, re-triggering L1's own thrashing limit as a spurious low-`num_ways` step in what's supposed to be a higher-level sweep. Using a `--min-abs-ticks` high enough to skip that spurious bump (0.25 for L2, 0.2 for LLC) does surface a second, much larger knee — but that knee lands at essentially the *same* `num_ways` (L2: base=11-way, both repeats=12-way; LLC: 10-way, fully reproducible across base+both repeats) and the *same* post-knee plateau magnitude (~0.8 ticks) for both L2 and LLC, despite L2 and LLC differing by 30x in byte capacity. This is the exact "two structurally different levels break at the same num_ways regardless of a large change in byte capacity" signature that `CLAUDE.md` already used to establish, on Sunbird and Upgrade (both x86), that any stride above roughly 1 MiB cannot currently distinguish real L2/LLC associativity from a small, fixed, page-count-limited structure (~9-10 slots there, likely TLB/page-walk-cache-related, not proven) — this Thunderbird run reproduces the same phenomenon at ~10-12 slots on a third machine and a different architecture (ARM, not x86), which is new cross-architecture evidence the confound isn't x86-DTLB-microarchitecture-specific, though it is NOT proof the exact same mechanism or slot count applies here (different CPU, no PMU cross-check yet). **Only L1's result (4-way) should be treated as reasonably solid** (clean single knee, no competing lower-level artifact possible since L1 is the smallest level tested, reproducible across base+both repeat seeds — small-stride L1 results are the one case not yet implicated by this confound, per the same caveat `CLAUDE.md` already applies to Sunbird's own L1 result). L2's and LLC's numbers below are reported because the pipeline was run and the graphs were requested, not because they're believed to be correct. This run used the plain fixed-full-capacity-stride method only; `CLAUDE.md` documents a more rigorous "derived-stride scan" technique (`scripts/run_associativity_stride_scan.sh`, validated on Upgrade) that has NOT been tried on this machine — that, or Phase II PMU verification, is the natural next step before citing an L2/LLC number here.
  3. Per-level results (random-pattern base sweep, thresholds as in note 1; reproducibility repeats used the same threshold as the base sweep for that level):
     - **L1** (`cache_bytes=65536`, `--min-abs-ticks 0.05`): estimated **4-way**, identical across base + both repeats (seeds 12345/12346/12347). Flat plateau ~0.13 ticks through `num_ways=4`, jumps to ~0.23 ticks at `num_ways=5`.
     - **L2** (`cache_bytes=1048576`, `--min-abs-ticks 0.25`, after skipping the L1-artifact bump per note 2): base sweep = **11-way**, both repeats = **12-way** (off-by-one, not perfectly reproducible — see note 2 for why this number shouldn't be over-trusted regardless).
     - **LLC** (`cache_bytes=31457280`, `--min-abs-ticks 0.2`, after skipping the L1-artifact bump per note 2): estimated **10-way**, identical across base + both repeats.
  4. Sequential-pattern control tracks the randomized-chain curve closely at every level (no divergence that would suggest a hardware prefetcher masking the knees), except L1's sequential control shows an additional, unexplained jump at `num_ways=37-40` that the randomized chain does not show at all (randomized stays flat ~0.15 through `num_ways=40`) — visible in `data_processed/thunderbird/associativity/L1/plots/associativity_curve.png`, not yet investigated, does not affect the 4-way estimate (well past it).

### latency/
Ran unattended (2026-09-13) per project-wide direction that `CAPACITY_RESULTS.md`
is the sole source for L1/L2/LLC byte values — used L1=65,536 B, L2=1,048,576 B,
LLC≈30 MiB=31,457,280 B (30×1,048,576, not 30×1,000,000) from that file's
Thunderbird row; the older per-machine capacity prose above and
`CAPACITY_INFERENCE_STATUS.md` were NOT consulted for these byte values.
Machine was idle at run time: `who`/`ps` showed no other students' processes,
and two `/proc/stat` delta samples ~3s apart showed every core in this
session's `Cpus_allowed_list: 0-4` cgroup at 0.0-0.7% busy; ran on core 4
(same core as this machine's associativity run above).

**hit_latency (dependent chain + independent-load diagnostic control):**
- Source file(s): `main_code/common/{main.c,latency.c,latency.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/aarch64/timer_arm.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run command + arguments: `./scripts/run_hit_latency_full.sh thunderbird 4 L1:65536,L2:1048576,LLC:31457280,DRAM:536870912` (DRAM's 512 MiB footprint is not itself a `CAPACITY_RESULTS.md` value — same "comfortably past LLC" pick Sunbird's README used).
- Per level: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--load-mode {dependent,independent}` × `--pattern {random,sequential}`, 1,000,000 timed accesses per combination (batch size 1000), 3 untimed warm-up passes.
- Dependent-chain batch size: 1000.
- Regular vs. randomized control included: yes, both `--pattern random` and `--pattern sequential` at every (level, load_mode).
- Raw output filename(s): `data_raw/thunderbird/latency/hit/<LEVEL>/hit_latency_{base,rep1,rep2}_{dependent,independent}_{random,sequential}_20260913T061114Z.csv.gz`. Full transcript: `data_raw/thunderbird/latency/run_hit_latency_full_20260913T061114Z.log`.
- Processing: `scripts/summarize_raw.py` per raw file → `data_processed/thunderbird/latency/hit/<LEVEL>/*_summary_20260913T061114Z.csv` → `scripts/plot_hit_latency.py` → `data_processed/thunderbird/latency/hit/<LEVEL>/plots/hit_latency_boxplots.{png,pdf}`.
- **Result (dependent, random pattern, ticks/access, base/rep1/rep2 medians, n=1000 each):** L1 = 0.136 / 0.122 / 0.124; L2 = 0.2975 / 0.278 / 0.309; LLC = **1.642** / 0.889 / 0.925; DRAM = 2.336 / 2.3355 / 2.341. At `CNTFRQ_EL0` = 25 MHz (40 ns/tick), the reproducible (rep1/rep2-based) numbers convert to roughly **L1 ≈ 5.0 ns, L2 ≈ 11.9 ns, LLC ≈ 36.3 ns, DRAM ≈ 93.4 ns** — a clean monotonic 4-tier ladder. The DRAM figure (~93.4 ns) agrees closely with this machine's independently-measured capacity-experiment DRAM plateau (~92-96 ns/access, see the capacity/ section above) — a useful cross-experiment sanity check, since the two experiments share no code path beyond the timer/pointer-chase primitives.
- **LLC base run flagged as contaminated, not used for the headline number above:** `plot_hit_latency.py` printed `note: ('dependent', 'random') has 3 overlapping summary rows with medians [1.6, 0.9, 0.9] (spread 0.8 ticks, 65.4%)`. The base run's 1.642 sits far above both repeats' 0.889/0.925 (agreeing within ~4% of each other) — consistent with the scattered single-run interference spikes already documented on this and other machines' capacity/associativity data (see CLAUDE.md), not a genuine third value. LLC's reported ~36.3 ns above uses rep1/rep2 only.
- At every level and both patterns, `--load-mode independent` measured faster than `dependent`, confirming the parallelism-exposing control worked as intended — no `[UNEXPECTED]` flags at any level:
  - L1: random 0.11 vs 0.13 [expected]; sequential 0.09 vs 0.12 [expected]
  - L2: random 0.23 vs 0.29 [expected]; sequential 0.07 vs 0.09 [expected]
  - LLC: random 0.81 vs 1.15 [expected]; sequential 0.07 vs 0.09 [expected]
  - DRAM: random 1.15 vs 2.34 [expected]; sequential 0.07 vs 0.09 [expected]
- **Notable pattern-level finding (not on the original checklist, but visible directly in the numbers above): sequential-pattern dependent-mode latency is ~0.09-0.12 ticks at EVERY level, L1 through DRAM, with no growth at all** — unlike the random-pattern ladder's clear 5→12→36→93 ns climb. This is the hardware prefetcher fully hiding a sequential dependent chase's true footprint-driven latency regardless of working-set size (the same phenomenon this project's capacity experiments already document for the `sequential` pattern not showing clean capacity boundaries). Confirms the sequential control is doing its documented job (a prefetcher-sanity check) but also means sequential-pattern numbers must never be read as level-specific hit latencies on this machine.

**miss_latency (forced eviction + single-shot reload):**
- Source file(s): same list as hit_latency above.
- Eviction-set calibration (done before picking final parameters, core 4, random pattern, 100 trials at `--target-bytes 31457280`): ~0.771 s/trial at a 60 MiB (2×LLC) eviction set, ~0.443 s/trial at 36 MiB (1.2×LLC) — roughly linear in eviction-set size on this machine, unlike Sunbird's documented superlinear (74ms→604ms, 8x bytes for >2x-worse-than-linear cost) jump between 27 MiB and 64 MiB. Extrapolating 60 MiB to the full base+2reps×2patterns (1200 trials) for just the LLC_to_DRAM transition projected to ~15.4 min, at the stated ~15 min budget edge; interpolating the two calibration points to 45 MiB (1.5×LLC) projected ~11.3 min, so **45 MiB (47,185,920 B) was used as LLC_to_DRAM's evict_bytes** — comfortable margin above LLC capacity, comfortably under the wall-time budget.
- Run command + arguments: `./scripts/run_miss_latency_full.sh thunderbird 4 L1_to_L2:65536:131072,L2_to_LLC:1048576:2097152,LLC_to_DRAM:31457280:47185920`. `L1_to_L2`'s evict_bytes (131,072 B = 2×L1) and `L2_to_LLC`'s (2,097,152 B = 2×L2) are both comfortably inside the next level's own capacity (8x and 15x margin respectively), so neither needed dedicated wall-time calibration — both completed in well under a minute total.
- Per transition: base run + 2 reproducibility repeats (seed = 12345, 12346, 12347), each at `--pattern {random,sequential}`, 200 single-shot trials per (transition, pattern, run), `--batch-size 1` (meaningless to this experiment, passed only to satisfy `main.c`'s cross-experiment `--samples`/`--batch-size` validation), 3 untimed warm-up passes.
- Raw output filename(s): `data_raw/thunderbird/latency/miss/<TRANSITION>/miss_latency_{base,rep1,rep2}_{random,sequential}_20260913T061738Z.csv.gz`. Full transcript: `data_raw/thunderbird/latency/run_miss_latency_full_20260913T061738Z.log`.
- Processing: `scripts/summarize_raw.py` → `data_processed/thunderbird/latency/miss/<TRANSITION>/*_summary_20260913T061738Z.csv` → `scripts/plot_miss_latency.py --hit-latency-summary <matching hit_latency dependent/random summaries>` → `data_processed/thunderbird/latency/miss/<TRANSITION>/plots/miss_latency_boxplots.{png,pdf}`.
- **Result (random pattern, ticks/access, base/rep1/rep2 medians, n=200 each): L1_to_L2 = 2.0 / 1.0 / 1.0 (flagged: `plot_miss_latency.py` printed a 75.0% spread note for this transition); L2_to_LLC = 2.0 / 2.0 / 2.0 (fully reproducible); LLC_to_DRAM = 4.0 / 4.0 / 4.0 (fully reproducible on median; means drifted 4.935→4.575→4.325, ~12.6% spread, consistent with the same scattered single-run interference already documented elsewhere on this machine, not a methodological flaw).** No transition showed the kind of run-to-run *disagreement in direction* that would suggest a real error — only the expected magnitude noise.
- **This machine's coarse 25 MHz counter (40 ns/tick) makes L1_to_L2 and, to a lesser extent, L2_to_LLC's raw numbers essentially unresolvable — reported for completeness, not as precise latencies.** A dedicated single-shot overhead control (`--target-bytes 65536 --evict-bytes 512 --pattern random --samples 2000`, an eviction set of only ~8 lines overwhelmingly unlikely to evict the target) gave **median = 1 tick, mean = 0.8955** (distribution: 0 ticks × 216, 1 tick × 1777, 2 ticks × 7, out of 2000) — i.e. the fixed single-shot measurement overhead alone (per `latency.h`'s documented KNOWN LIMITATION) already sits at almost exactly L1_to_L2's own measured median (1-2 ticks). **L1_to_L2's number cannot be distinguished from pure measurement overhead on this machine** — say so rather than reporting a precise-looking L1→L2 latency. L2_to_LLC's median (2 ticks, fully reproducible) is one tick above the overhead floor, a small but at-least-nonzero and reproducible signal. Only **LLC_to_DRAM (4 ticks median, ~3 ticks / ~120 ns above the 1-tick overhead floor, cleanly separated from both the overhead control and from L2_to_LLC's 2-tick median)** is confidently resolvable on this hardware: subtracting the 1-tick overhead and comparing against this level's own rep1/rep2 hit_latency baseline (~0.907 ticks ≈ 36 ns) gives a rough overhead-corrected LLC→DRAM reload cost of **~2.1 ticks ≈ 84 ns** — approximate, not a clean number, per the same caveat Sunbird's README already applies to its own miss_latency figures.
- **Second finding, not on the original checklist: sequential-pattern miss_latency collapses to ~1 tick at EVERY transition (L1_to_L2 = 1.0/1.0/1.0, L2_to_LLC = 1.0/1.0/1.0, LLC_to_DRAM = 1.0/1.0/1.0), essentially indistinguishable from the single-shot overhead floor even for LLC_to_DRAM where the random pattern clearly separates from that floor.** This mirrors the hit_latency finding above (sequential pattern hiding all footprint-driven latency growth) and is consistent with the same explanation: the eviction-set walk's sequential traversal order lets the hardware prefetcher run ahead of the walk, and very plausibly ends up re-fetching the target's own line (adjacent in the same virtually-contiguous allocation) before the timed reload fires, defeating the eviction the experiment is trying to force. **Do not use sequential-pattern miss_latency numbers as real next-level latencies on this machine — only the random-pattern numbers above are reported as (approximate) reload latencies**, consistent with `latency.h`'s framing of `--pattern` as an eviction-order control rather than a report-quality diagnostic (unlike hit_latency's independent-vs-dependent control, which IS designed to be compared).
- Not yet done: no PMU cross-check (Phase II, not started); L1_to_L2's overhead-floor problem is not resolvable within this codebase's current single-shot design (would need either a batched miss-latency variant or a much higher-resolution timer than `CNTVCT_EL0` provides); the sequential-pattern prefetch-hiding hypothesis above is plausible but not confirmed (no Phase-I-safe way to distinguish "prefetcher re-fetched the target" from "eviction walk never touched the target's set" without a topology lookup).

### inclusion_policy/
Ran 2026-09-13 (core 4, same core as this machine's associativity/latency runs;
re-verified idle via `/proc/stat` deltas immediately before running — every
core in this session's range at 0.0-1.0% busy). Boundary values from
`CAPACITY_RESULTS.md` only (L1=65,536 B, L2=1,048,576 B, LLC≈30 MiB=
31,457,280 B), same as every other experiment on this machine. All three
pairings implied by those three levels were run (L1 vs L2, L2 vs LLC, L1 vs
LLC directly).

- Source file(s): `main_code/common/{main.c,inclusion_policy.c,inclusion_policy.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/aarch64/timer_arm.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Run commands + arguments:
  - `ASSUMED_LINE_SIZE_BYTES=64 ./scripts/run_inclusion_policy_full.sh thunderbird 4 L1_vs_L2:65536:1048576:L2_to_LLC` (timestamp `20260913T180921Z`)
  - `ASSUMED_LINE_SIZE_BYTES=128 ./scripts/run_inclusion_policy_full.sh thunderbird 4 L2_vs_LLC:1048576:31457280:LLC_to_DRAM,L1_vs_LLC:65536:31457280:LLC_to_DRAM` (timestamp `20260913T180932Z`, both pairings in one invocation since they share the same lower-level line size)
  - **Per-pairing `ASSUMED_LINE_SIZE_BYTES` was set explicitly, not left at the script's default of 64**, because this machine's own `line_size/` section above found a real per-level split: 64 B at L1/L2 but 128 B at the LLC candidate. L1_vs_L2 scales its eviction footprint using L2's own confirmed 64 B; L2_vs_LLC and L1_vs_LLC both scale using LLC's own confirmed 128 B. This is the exact cross-machine gap `run_inclusion_policy_full.sh`'s `ASSUMED_LINE_SIZE_BYTES` env-var override was added to handle (see that script's header comment).
  - Resulting `--evict-bytes`: L1_vs_L2 = 67,108,864 B (64 MiB, = 1,048,576 × 4096/64); L2_vs_LLC and L1_vs_LLC both = 1,006,632,960 B (~960 MiB, = 31,457,280 × 4096/128).
  - **Wall-time calibration done before committing to the ~960 MiB LLC-scale footprint** (per this project's established practice of calibrating before a large eviction sweep, since miss_latency's own timing was documented as non-linear in eviction-set size on other machines): a 50-trial, 3-warmup-pass manual run at the full 1,006,632,960 B footprint completed in 1.317s (~26 ms/trial) — this experiment's eviction walk touches only one line per 4096 B page (`inclusion_policy.h`'s sparse construction, see caveat 3 below), so its per-trial cost scales with PAGE count, not byte count, unlike a dense sweep; at this rate the full pipeline's 1,200 main-sweep trials per pairing (200 samples × 3 runs × 2 patterns) cost well under a minute, no `tmux` needed.
- Per pairing: 200 single-shot trials (`--samples 200 --batch-size 1`) per (run, pattern), base + 2 reproducibility repeats (seed 12345/12346/12347), both eviction-walk traversal patterns, 3 untimed warm-up passes; a separate 500-trial calibration run (`--evict-bytes` = `--target-bytes`, nothing evicted) establishes each pairing's own single-shot "survived" baseline fresh, same method as Sunbird's.
- Raw output filenames: `data_raw/thunderbird/inclusion_policy/<pairing>/inclusion_policy_{calibration,base,rep1,rep2}_{random,sequential}_<ts>.csv.gz`; full transcripts `data_raw/thunderbird/inclusion_policy/run_inclusion_policy_full_{20260913T180921Z,20260913T180932Z}.log`.
- Processing: `scripts/summarize_raw.py` → `data_processed/thunderbird/inclusion_policy/<pairing>/*_summary_<ts>.csv` → `scripts/classify_inclusion_policy.py` (reads raw base/random data directly) → `scripts/plot_inclusion_policy.py` (matplotlib present on this machine as of this session — confirmed via `python3 -c "import matplotlib"` before running — so plots generated without the graceful-degradation fallback the hardened script added for machines that lack it).

- **Four load-bearing caveats — read before trusting a result:**
  1. **Assumed line size (per-level, not a single machine-wide constant) — RESOLVED for this run, not left as an unverified assumption.** Unlike Sunbird (where a single 64 B constant covers every level), this machine's own `line_size/` data shows a real split (64 B at L1/L2, 128 B at LLC), so the per-pairing `ASSUMED_LINE_SIZE_BYTES` values above are this machine's own confirmed numbers, not guesses.
  2. **DTLB pressure at large eviction scale (affects L2_vs_LLC and L1_vs_LLC, both ~245,760-page/~960 MiB eviction footprints; L1_vs_L2's ~16,384-page/64 MiB footprint is far smaller).** Both LLC-scale pairings' CONTROL channel reads noticeably slower than its own calibration baseline (L2_vs_LLC: control median 1.0 vs calibration 1.002 — actually consistent; but L2_vs_LLC's control still shows 98.5% survived-like, so the control stayed largely clean here) — see per-pairing results below for whether this looks like a real factor.
  3. **NEW finding, specific to Thunderbird, not present on Sunbird: the avoidance guarantee (target's full index fits within one page) is structurally WEAKER here even for an L1 target, not just for L2_vs_LLC.** Sunbird's L1 (32,768 B, 8-way, 64 B lines) has exactly 64 sets = 6 index bits + 6 offset bits = 12 bits, exactly one page — the avoidance construction is exact there. Thunderbird's L1 (65,536 B, 4-way confirmed, 64 B lines) has 65,536/(4×64) = 256 sets = 8 index bits + 6 offset bits = **14 bits, i.e. 4 pages' worth, not 1**. Because a VIPT L1's index bits above the 12-bit page-offset boundary depend on the PHYSICAL page frame (not just the fixed sub-page offset this method controls), the eviction walk's many touched pages will, by ordinary chance, occasionally share those extra 2 index bits with the target reload address's own page — meaning the eviction walk can incidentally land in the target's real L1 set on roughly 1-in-4 of its touched pages, not zero. This affects ALL THREE pairings tested here (any pairing with an L1 target), not just L2_vs_LLC as on Sunbird. Read every verdict below as somewhat less clean than the equivalent Sunbird result for this reason, even where the classification looks confident.
  4. **This machine's coarse 25 MHz counter (40 ns/tick) compresses the survived/invalidated calibration classes into just a few integer tick values, unlike Sunbird's much finer continuous-valued ticks.** E.g. L1_vs_L2's survived-class calibration (1.376 ticks) and invalidated-class calibration (2.0 ticks, from `L2_to_LLC`) differ by well under one tick — the classification boundary geometric mean (1.66) sits almost exactly between the two nearest achievable integer tick values (1 and 2), so individual-trial classification here is much less crisp than on an x86 machine with hundreds of resolvable tick values. Treat the resulting percentages as directionally meaningful, not precise.

- **Results, one per pairing (n=200 target/control trials each, base/random run):**
  - **L1_vs_L2** (survived-class 1.376 ticks, invalidated-class 2.0 ticks from `L2_to_LLC`, boundary 1.66): target median 1.0 ticks (84.5% survived-like, 15.5% invalidated-like), control median 1.0 ticks (99.5% survived-like). Paired check (target slower than its own control): 20.0%. **Verdict: EXCLUSIVE / NON-INCLUSIVE** — same qualitative direction as Sunbird's own L1_vs_L2 (90.0% there vs. 84.5% here), the cleanest of the three pairings on this machine too, despite caveats 3-4 above.
  - **L2_vs_LLC** (survived-class 1.002 ticks, invalidated-class 4.0 ticks from `LLC_to_DRAM`, boundary 2.00): target median 3.0 ticks (0.0% survived-like, 23.5% ambiguous, 76.5% invalidated-like), control median 1.0 ticks (98.5% survived-like). Paired check: 99.5% (target read slower than its own control on almost every trial). **Verdict: UNCERTAIN** by the strict classification, but the raw fractions lean noticeably more toward invalidated than Sunbird's own L2_vs_LLC did (76.5% invalidated-like here vs. Sunbird's 13.5% survived-like/1.5% invalidated-like/85% ambiguous — a materially different-looking result, not just a noisier version of the same one). Read with the least confidence of the three per caveat 3 above (L2 is far bigger than one page's index range on any machine, this method's weakest case by design) — the near-total 99.5% paired-slower reading suggests the eviction genuinely disturbs the target channel here, consistent with either real inclusive behavior at this pairing or the L2-target-index-doesn't-fit-in-one-page structural issue (present on both machines, worse for an L2 target than an L1 target even before Thunderbird's extra caveat-3 wrinkle).
  - **L1_vs_LLC** (survived-class 0.9 ticks, invalidated-class 4.0 ticks from `LLC_to_DRAM`, boundary 1.90): target median 1.0 ticks (80.5% survived-like, 18.5% ambiguous, 1.0% invalidated-like), control median 1.0 ticks (91.5% survived-like, 8% ambiguous, 0.5% invalidated-like). Paired check: 13.0%. **Verdict: EXCLUSIVE / NON-INCLUSIVE** (80.5% just clears the 80% firm-call threshold) — **this is the opposite directional lean from Sunbird's own L1_vs_LLC result** (Sunbird: 75% invalidated-like, leaning inclusive; Thunderbird: 80.5% survived-like, leaning non-inclusive). Not necessarily a contradiction — these are two different CPU vendors/microarchitectures (Haswell-EP x86 vs. Neoverse N1 ARM) and real LLC inclusion policy is an implementation choice that can legitimately differ by design, not a universal architectural law — but it does mean this project's two ARM/x86 data points for the skip-level pairing disagree, and Thunderbird's own weaker avoidance guarantee (caveat 3) means this result should be held with real, not just formal, uncertainty.
  - Not yet done, any pairing: multiple different target addresses/sets (same gap Sunbird's writeup flags); a huge-pages TLB mitigation for caveat 2; and, specific to this machine, no attempt yet to quantify caveat 3's ~1-in-4 incidental-collision estimate empirically (e.g. by re-running with a target sized to fit exactly one page's worth of index, if a suitable `CAPACITY_RESULTS.md`-independent footprint were chosen for a dedicated diagnostic).

**Best-guess synthesis:** L1 vs L2 is confidently non-inclusive (matches Sunbird's own L1_vs_L2 finding, and is the pairing least exposed to every caveat above). The two LLC-involving pairings each lean in a specific direction (L2_vs_LLC leans inclusive at 76.5%, though formally UNCERTAIN; L1_vs_LLC leans non-inclusive at 80.5%) but, taken together, do NOT tell as clean or as internally consistent a story as Sunbird's own three-pairing result did — an LLC that is simultaneously non-inclusive of L1 directly (L1_vs_LLC) but leans toward invalidating an L2-resident line (L2_vs_LLC) is an unusual combination for a real hierarchy (typically inclusion, if present, holds more uniformly of everything below the inclusive level, not selectively by which level a line is currently resident in) — this is more likely explained by this machine's caveat-3 weaker avoidance guarantee and caveat-4 coarse timer resolution both degrading precision at exactly the two pairings that would otherwise seem to disagree, rather than as evidence of a genuinely selective inclusion policy. Treat Thunderbird's overall read as: **L1 vs L2 non-inclusive (confident); L2 vs LLC and L1 vs LLC both genuinely unresolved on this machine's data**, not a settled hierarchy-wide inclusion/exclusion story the way Sunbird's synthesis could reasonably claim.

### pmu/ (Phase II — started 2026-09-13, after tagging `phase1-timing-only` at commit `7be6dac`)
Phase I frozen/tagged before anything below was run, per `README.md`'s Phase
Discipline. See `CLAUDE.md`'s "Phase II" subsection and
`data_processed/thunderbird/PHASE2_VALIDATION_TABLE.md` for the full
methodology/results write-up and literature citations — this section is the
raw-data/reproduction-detail record. **Uses the same reusable pipeline as
Sunbird** (`scripts/run_pmu_verification.sh` + `scripts/summarize_pmu.py`) —
an earlier pass used a different, ad hoc script; that pass is kept as
supplementary evidence (see below and the validation table's own
supplementary section) rather than discarded, but this run is the canonical
one.

- Source file(s): `scripts/run_pmu_verification.sh`, `scripts/summarize_pmu.py`
  (no `cache_bench` source changes — reuses the existing `--experiment
  hit_latency` binary, wrapped in `perf stat`).
- Machine-specific PMU check done before running (this CPU's raw event list
  differs from Sunbird's x86 PMU, not just its scheduling behavior): a
  standalone `perf stat -e LLC-loads,LLC-load-misses` check came back
  `<not supported>` (not just `<not counted>`) — this `armv8_pmuv3_0` PMU has
  no LLC-scoped event, generic or raw, that perf's `LLC-loads` alias maps to.
  `cache-references`/`cache-misses` and `L1-dcache-loads`/`L1-dcache-load-misses`
  and `cycles`/`instructions` all schedule and count fine. The script's
  existing 4-separate-group design (built for Sunbird's counter-scheduling
  limitation) tolerates this gracefully — `summarize_pmu.py` records the
  `<not supported>` LLC group via its `notes` column exactly as it does a
  `<not counted>` one.
- Run command: `./scripts/run_pmu_verification.sh thunderbird 3
  L1:65536,L2:1048576,LLC:31457280` (core 3 — same core as every other
  Thunderbird experiment; idle-checked via `/proc/stat` idle-time deltas
  across a 2s window immediately before running: 98.5% idle).
  base_seed=12345 (repeats use base_seed+index), samples=1,000,000/run,
  batch_size=1000, warmup_passes=3, dependent load mode, random pattern,
  timestamp `20260913T203354Z`.
- Raw output: `data_raw/thunderbird/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz` (perf
  stat's own `-x,` CSV output, one file per group×run_tag) and
  `*_bench_*.csv.gz` (cache_bench's own CSV from the same invocation).
  Transcript: `data_raw/thunderbird/pmu/run_pmu_verification_20260913T203354Z.log`.
- Processed: `data_processed/thunderbird/pmu/{L1,L2,LLC}/pmu_summary_20260913T203354Z.csv`
  (one row per run_tag + a median-of-3 row).
- System-reported cache info (also Phase II, same run):
  `data_raw/thunderbird/pmu/system_reported_cache_info.txt` — `lscpu --caches`,
  full `lscpu`, and per-instance `/sys/devices/system/cpu/cpu3/cache/index*/`
  fields (only `index0`/`index1`/`index2` = L1D/L1I/L2 exist on this core —
  no L3/SLC entry appears anywhere in the OS-reported cache topology, a real
  finding in itself, see the validation table's LLC row).
- Literature references: Ampere Altra Datasheet Rev A1 v1.30 (2022-07-28)
  §2.3–2.5 p. 9; Arm Neoverse N1 Core TRM r3p1 (100616_0301_01_en)
  §A2.1.2/A6.4/A7.1 — full citations and the per-level Agreement analysis are
  in `data_processed/thunderbird/PHASE2_VALIDATION_TABLE.md`.
- Headline results (full detail and caveats in the validation table): L1D
  matches exactly across Phase I timing, system-report, and literature
  (size/ways/sets/line all agree); L2's associativity disagreement (Phase I's
  confound-suspected 12-way vs. system-reported AND literature's converging
  8-way) is resolved the same way Sunbird's was — in favor of system-report;
  LLC is this machine's weakest row (no system-reported entry exists at all
  for the SLC, unlike Sunbird's L3, so only literature — one source, not
  cross-checked — can speak to it), but Phase II literature does newly
  confirm the SLC is shared across all 80 cores rather than private-per-core,
  sharpening what Phase I could only guess at.
- **Supplementary (earlier ad hoc pass, kept not discarded):**
  `data_raw/thunderbird/pmu/run_pmu_sweep.sh` — a from-scratch raw-event sweep
  across 23 working-set sizes (4 KiB–512 MiB) using raw `armv8_pmuv3_0`
  `l{1,2,3}d_cache[_refill]` events, predating the switch to the shared
  pipeline. Raw: `data_raw/thunderbird/pmu/pmu_sweep_raw.csv.gz`; processed:
  `data_processed/thunderbird/pmu/pmu_sweep_summary.csv`; plot:
  `data_processed/thunderbird/pmu/plots/pmu_miss_rate_sweep.{png,pdf}`; also
  `data_raw/thunderbird/pmu/perf_list_20260913.txt` (full `armv8_pmuv3_0` raw
  event list). This sweep independently corroborates the L1D boundary at an
  exact 64 KiB knee and the "no flat L2 shelf" finding, and its own
  capacity-independent L3 miss-rate signal is additional evidence for the
  "SLC is invisible to this core's PMU/OS reporting" finding above — see the
  validation table's supplementary section for the full writeup.

### eight_counters/ (Problem 8.4, item 1 — 2026-09-14)
The 3 standardized cross-machine microbenchmarks required by problem 8.4 —
(i) L1-resident dependent accesses, (ii) LLC-sized randomized accesses, (iii)
a working set larger than LLC — second machine after Sunbird to run this
pipeline. Same benchmark construction and 8-counter set as Sunbird's own
`eight_counters/` section (see that machine's README and `CLAUDE.md`'s 8.4
bullet for the full rationale) — reused here unmodified except for this
machine's own hand-confirmed L1/LLC footprint values.

- Source file(s): `scripts/run_standardized_benchmarks.sh`,
  `scripts/summarize_eight_counters.py` (copied over via `scp`, same as the
  earlier Phase II PMU scripts — this machine's git remote has no cached
  GitHub credentials, a pre-existing condition already noted in `pmu/`
  above/`CLAUDE.md`; this machine's local checkout also has its own
  in-progress uncommitted `software_hit_rate` work, left untouched).
- **8 counters** (assignment-literal set, same as Sunbird):
  `cache-references`, `cache-misses`, `L1-dcache-loads`,
  `L1-dcache-load-misses`, `L1-dcache-stores`, `LLC-loads`,
  `LLC-load-misses`, `dTLB-load-misses`. Machine-specific check done before
  running: `perf list` has NO `L1-dcache-stores` entry at all on this
  `armv8_pmuv3_0` PMU (unlike Sunbird's x86 PMU), and `LLC-loads`/
  `LLC-load-misses` are already documented as `<not supported>` here (see
  `pmu/` above). A standalone test (`perf stat -x, -e
  duration_time,L1-dcache-stores,dTLB-load-misses -- /bin/true`) confirmed
  graceful degradation, not a hard failure: `L1-dcache-stores` comes back
  `<not supported>` (exit code 0), `dTLB-load-misses` counts normally.
  `summarize_eight_counters.py`'s existing non-numeric-value handling
  (shared with `summarize_pmu.py`, catches any unparseable value string, not
  just the literal `<not counted>`) records this correctly with no script
  changes needed.
- Idle-core check before running: `/proc/stat` idle-tick deltas sampled
  across 3 windows ~2s apart for cores 0-3 — cores 0 and 2 showed flat,
  non-incrementing idle counters (100% busy; `ps` showed another student's
  `incl_pmu` process on core 0 and a different student's `cache_bench_arm`
  on core 2); core 3 (same core as every other Thunderbird experiment)
  confirmed idle and used again here.
- Run command: `./scripts/run_standardized_benchmarks.sh thunderbird 3
  L1_resident:65536,LLC_random:31457280,beyond_LLC:536870912` (core 3;
  footprints are this machine's own hand-confirmed `FINAL_CACHE_TABLE.md`
  L1/LLC values plus the project's universal 536,870,912 B / 512 MiB
  DRAM-scale constant for `beyond_LLC`, the same value already used for this
  machine's own DRAM row elsewhere). base_seed=12345 (repeats use
  base_seed+index), samples=1,000,000/run, batch_size=1000, warmup_passes=3,
  dependent load mode, random pattern, timestamp `20260914T043110Z`.
- Raw output: `data_raw/thunderbird/eight_counters/{L1_resident,LLC_random,
  beyond_LLC}/*_perfstat_*.csv.gz` and `*_bench_*.csv.gz` (gzipped by hand
  post-run). Transcript: `data_raw/thunderbird/eight_counters/
  run_standardized_benchmarks_20260914T043110Z.log`.
- Processed: `data_processed/thunderbird/eight_counters/{L1_resident,
  LLC_random,beyond_LLC}/eight_counters_summary_20260914T043110Z.csv`.
- **Headline numbers (median row, all 3 benchmarks):**
  - `L1_resident` (65,536 B): ≈0.085 ticks/access, `cache_miss_rate`≈0.20%,
    `l1_miss_rate`≈0.19%, `dtlb_load_misses`≈1530-1624 (small) — sane and
    consistent with an entirely L1-resident working set.
  - `LLC_random` (31,457,280 B): ≈2.158-2.161 ticks/access (tight, <0.15%
    spread across all 3 seeds), `dtlb_load_misses`≈1.14M-1.77M (3 orders of
    magnitude above `L1_resident`, as expected). **Flagged, not smoothed
    over: this is noticeably higher than this machine's own
    previously-documented ≈0.907-tick LLC hit latency**
    (`FINAL_CACHE_TABLE.md`) — most likely explained by the same two other
    students' processes (`incl_pmu` on core 0, `cache_bench_arm` on core 2)
    confirmed active for this entire run, contending for the
    chip-shared LLC/memory bandwidth even though core 3 itself stayed idle
    (the same "idle core doesn't insulate from chip-shared contention"
    finding already documented for Ookay's PMU run and Sunbird's own
    `beyond_LLC` result above) — not re-run this session.
  - `beyond_LLC` (536,870,912 B): ≈2.44-2.446 ticks/access, close to (only
    ~4-5% above) this machine's own previously-documented ≈2.336-tick DRAM
    hit latency — within the same contention-noise range as every other
    multi-run experiment on this project's shared machines.
    `dtlb_load_misses`≈255.6M-256.0M, ~150x above `LLC_random`, consistent.
  - **Net effect of the above**: the LLC-to-DRAM tick gap is much more
    compressed in this run (≈2.16 to ≈2.44, only ~1.13x) than this
    machine's own previously-documented values (≈0.907 to ≈2.336, ~2.6x) —
    consistent with `LLC_random` specifically being inflated toward
    DRAM-like latency by contention, rather than `beyond_LLC` being
    suppressed.
  - Confirms an already-documented ARM PMU quirk in this new counter set
    too: `cache_miss_rate` and `l1_miss_rate` are nearly identical at every
    footprint (0.20%≈0.19% at L1_resident; 5.46%≈5.46% at LLC_random;
    5.33%≈5.34% at beyond_LLC) — this machine's generic
    `cache-references`/`cache-misses` alias tracks L1-scope traffic, not a
    true any-cache-vs-DRAM signal, exactly as already found in this
    machine's Phase II PMU section above and its `software_hit_rate/`
    validation work.
  - `dtlb_load_misses` is the one counter that behaves as expected
    throughout: monotonic, multi-order-of-magnitude increase with
    footprint, unaffected by the generic-counter limitation above.
- **2 of 8 machines done (Sunbird, Thunderbird).** Remaining 6 (Skylark,
  Artemisia, Charnwood, Crux, Ookay, Upgrade) need the same command with
  their own `FINAL_CACHE_TABLE.md` L1/LLC values before problem 8.4 items
  2-4 (normalization, per-benchmark ranked S-curves, and the Intel/AMD/Arm
  and older/newer generation comparison) can be attempted.

## Reservation Log (if applicable)
- Reserved core/package: core 3 (of `Cpus_allowed_list: 0-4` granted to this session)
- Time window: 2026-09-08 ~20:14 UTC - ~23:14 UTC
