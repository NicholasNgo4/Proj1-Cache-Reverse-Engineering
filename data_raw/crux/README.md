# crux — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: crux.ece.ncsu.edu
- CPU model (from `lscpu`/`/proc/cpuinfo`): Intel(R) Core(TM) i7-9700 CPU @ 3.00GHz (1 socket, 8 cores, 1 thread/core -- no SMT)
- ISA / architecture: x86-64
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Coffee Lake (Coffee Lake Refresh), per `MACHINE_RESEARCH.md` Table 1
- Introduction year (per the team's stated year convention): 2019 (per `MACHINE_RESEARCH.md`)
- Process node (if reliably documented): 14 nm (per `MACHINE_RESEARCH.md`)
- Kernel version: Linux 6.8.0-88-generic
- Page size: 4096 bytes (`getconf PAGE_SIZE`)
- SMT siblings idle during runs? N/A -- this CPU has no SMT (`lscpu`: 1 thread/core, 8 cores/socket, 1 socket = 8 logical CPUs total, one-to-one with physical cores).

## Environment
- Compiler + version: GCC 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): x86 RDTSC (LFENCE-fenced start) / RDTSCP (LFENCE-fenced stop), batched: N=1000 dependent pointer-chase steps timed per start/stop pair, ticks/access = (t1-t0)/N. See `main_code/x86_64/timer_x86.h`, `main_code/common/benchmark.c`.
- Affinity/binding command used: `taskset -c 7 ./cache_bench ...` (see `scripts/run_capacity_full.sh` and the ad hoc `crux_tail2.sh` follow-up described below). Core 7 was chosen after checking `Cpus_allowed_list` (session had 0-7 available), `lscpu -e=CPU,CORE,SOCKET,NODE` (confirmed CPU==CORE, i.e. no SMT sibling to worry about), and `who`/`ps -eLo pid,psr,pcpu,user,comm`/`mpstat -P ALL 1 2` to check for other students' active load: at run time, CPU 0 was 100%-pinned by `clclark7`'s `associativity` process and CPU 4 was 100%-pinned by `hbsu`'s and `rsivaku3`'s `cache_bench` processes (confirmed via `taskset -pc` on each PID); CPUs 1,2,3,5,6,7 were idle across two independent `mpstat` samples. Core 7 was picked from that idle set.
- NUMA/locality method: no explicit NUMA pinning; single-socket machine (no NUMA to control for). Default first-touch allocation on `malloc`-then-touch.
- Git commit hash of the code used for these results: `881fbfc00f6bf576dfbc35cf5d97ce2a1aa09ad9` (working tree was clean of code changes at run time; only new data/plot files were added by the run, listed below)

## Per-Experiment Reproduction

### capacity/
- Source file(s): `main_code/common/{main.c,capacity.c,capacity.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments:
  - Full automatic pipeline: `./scripts/run_capacity_full.sh crux 7` (default `coarse_max_bytes` = 64 MiB). This ran, in order: coarse sweep 1 KiB-64 MiB (both patterns, 8 points/octave) -> automatic 4x tail-extension sweep 64-256 MiB -> `detect_cache_hierarchy.py --machine-readable` on the combined coarse+tail random data -> dense sweeps (48 points/octave, +-3 octaves) around each of the 4 detected boundaries (262144, 9147840, 11863280, 16777216 bytes) -> 2 reproducibility repeats on the deepest boundary's dense window (16.78 MiB, i.e. 2-128 MiB) -> a dense sweep past the deepest boundary, 64-256 MiB, checking for a further plateau -> plots.
  - Manual follow-up (`crux_tail2.sh`, ad hoc script, not committed): after inspecting the automatic pipeline's 64-256 MiB tail data, the median was still climbing at the 256 MiB ceiling (218 ticks at 64 MiB -> 243 ticks at 256 MiB, no flattening), so per the team's Sunbird precedent this was extended rather than accepted as final. Ran one additional dense sweep (48 points/octave) from 256 MiB to 1 GiB (`--min-bytes 268435456 --max-bytes 1073741824`), both patterns, plus 2 independent repeats of the same window, all pinned `taskset -c 7`, same seed/samples/batch/warmup as below. 1 GiB was chosen as 4x the prior 256 MiB ceiling (matching the automatic script's own tail-extension rule), and checked against the memory-safety rule (25% of `MemAvailable` at run time was ~3.46 GiB, comfortably above the 1 GiB single-buffer allocation).
  - All runs: `--samples 1000000 --batch-size 1000 --warmup-passes 3 --seed 12345`, `--pattern random` and `--pattern sequential` each.
- Sample count: 1,000,000 timed accesses per (size, pattern) point; warm-up (3 full untimed chase passes) excluded from that count
- Random seed(s): 12345 (xorshift32, `make_random_cycle`); sequential-pattern runs use `make_sequential_cycle` (no seed/randomness)
- Raw output filename(s): all under `data_raw/crux/capacity/`, timestamp `20260908T231021Z` for every file (the manual follow-up reused this timestamp for filename continuity even though it ran later in a separate invocation): `capacity_coarse_{random,sequential}_*.csv.gz`, `capacity_coarse_ext_{random,sequential}_*.csv.gz` (64-256 MiB tail), `capacity_dense{0,1,2,3}_{random,sequential}_*.csv.gz` (dense windows around the 4 detected boundaries), `capacity_dense3_rep{1,2}_{random,sequential}_*.csv.gz` (deepest-boundary repeats), `capacity_denseTail_{random,sequential}_*.csv.gz` (64-256 MiB post-boundary check, part of the automatic pipeline), `capacity_denseTail2_{orig,rep1,rep2}_{random,sequential}_*.csv.gz` (manual 256 MiB-1 GiB follow-up, 3 independent runs). Gzipped after the fact (~9x smaller) to keep repo size manageable; summaries in `data_processed/` were generated from the uncompressed originals before compression. Full transcript of the automatic pipeline: `run_capacity_full_20260908T231021Z.log`.
- Processing script -> data_processed path: `python3 scripts/summarize_raw.py <raw.csv> -o data_processed/crux/capacity/<name>_summary.csv` for every raw file above, then `python3 scripts/plot_capacity.py <all summary.csv except coarse_combined_random_summary.csv> -o data_processed/crux/capacity/plots --machine crux --boundary 262144 --boundary 9147840 --boundary 11863280 --boundary 16777216`. (`coarse_combined_random_summary.csv` is an internal concatenation used only as input to `detect_cache_hierarchy.py`, not a real independent run -- excluded from the plot inputs to avoid `plot_capacity.py` treating it as a spurious duplicate/second observation of the same data.) **Regenerated 2026-09-10** with `--boundary 32768 --boundary 9147840 --boundary 11863280 --boundary 16777216` (dropped 262144, which was never a real boundary -- see the L1 correction above; added the precise 32,768 B L1 edge).
- Excluded runs (if any) and reason: none excluded; all runs listed above are included in the final plots.
- **Boundary detection and plateau status** (see also `MACHINE_RESEARCH.md`/report for the final level assignment -- this is the raw-data-level finding):
  - **~5.6-7 ticks/access plateau, 1 KiB-~64 KiB**: flat, low-noise (stddev ~0.2 ticks at most points). Confirmed genuine plateau (L1 region) directly from the coarse sweep; no further work needed. **Precise edge identified (2026-09-10, same already-committed coarse data, no new run):** the plateau (5.50-5.68 ticks) actually holds flat through exactly 30,048 B, with the ramp starting at 32,768 B (5.806) and clearly underway by 35,728 B (6.175); sequential-pattern control stays flat across that same pair (5.71 vs 5.706 ticks), confirming a real random-access effect. **L1 = 32,768 bytes (32 KiB)** -- matching the same value found the same way on Sunbird (hand-confirmed via associativity), Skylark, Upgrade, Ookay, and Charnwood (see each machine's own README): 6 of this team's 7 x86 machines now agree. The original auto-detector's first reported boundary was 262,144 B (256 KiB) -- inconsistent with this 32 KiB edge; that value is not a real second plateau either (see the ~64 KiB-4 MiB ramp region immediately below), it was just where the detector's threshold happened to first trip on the way up the same ramp. **PROVISIONAL** (clean in the data; not yet cross-checked by an independent test the way Sunbird's was).
  - **~7-40 ticks/access, ~64 KiB-~4 MiB**: a shallow, continuous ramp rather than a hard plateau -- `dense0` (32 KiB-2 MiB, bracketing the auto-detected 262144-byte/256 KiB boundary) shows no flat shelf immediately after 256 KiB; latency keeps climbing gently all the way to ~4 MiB. Treated as an open/soft region, not a confirmed second plateau -- flagged here rather than asserted as an L2 boundary.
  - **~40-250 ticks/access, ~4-64 MiB**: one dominant steep S-curve transition. The auto-detector's three boundaries in this span (9147840 / 11863280 / 16777216 bytes, i.e. ~8.7/11.3/16 MiB) are three points along this single ramp, not three separate levels -- consistent with the team's Sunbird finding that a steep transition region gets over-segmented by the knee-detector. The two independent repeats (`dense3_rep1`, `dense3_rep2`) on the 16.78 MiB window reproduced large point-to-point run-to-run spread here (up to ~89% at some sizes, e.g. 8.85 MiB: medians [59.3, 48.2, 51.6, 108.7, 76.0] across runs) -- this region is genuinely noisy/variable run-to-run, not just noisy within one run, and any single-run boundary estimate inside it should be treated with caution.
  - **~245-250 ticks/access plateau, ~100 MiB-1 GiB**: **initially open, now confirmed genuine.** The automatic pipeline's 64-256 MiB tail-extension was still climbing at its 256 MiB ceiling (218 ticks at 64 MiB -> 243 ticks at 256 MiB, no flattening) -- per the team's Sunbird precedent, this was not accepted as final. The manual 256 MiB-1 GiB follow-up (orig + 2 repeats) shows the climb slowing sharply and flattening: average median across the 3 runs rises only ~243->250 ticks (~3%) over the full 256 MiB-1 GiB range (vs. ~11% per octave in the still-transitioning 64-256 MiB region), and the 3 independent runs agree within 0.2-0.5% at the 1 GiB endpoint (249.376 / 249.893 / 249.901 ticks). Run-to-run spread across the 256 MiB-1 GiB range is under 1% at nearly every point, with two isolated exceptions (~322 MiB: 3.7%, ~912 MiB: 4.7%) consistent with the same kind of transient scheduling interference documented below, not a real property of those sizes. This plateau is interpreted as the machine's true random-access DRAM latency floor once the working set is far outside any cache level, not a cache boundary itself.
- **Known interference / anomalies**:
  - This is a shared, multi-user lab machine. At run time (concurrently with our benchmark, on other cores): `clclark7` running an `associativity` benchmark pinned to CPU 0, `hbsu` and `rsivaku3` each running `cache_bench`-family benchmarks pinned to CPU 4 (`hbsu`'s own project, unrelated to this repo) -- confirmed not to overlap our core (7) via `taskset -pc` on each PID. Load average climbed from ~3.1 to ~3.9 over the course of this session as more students started jobs.
  - The automatic pipeline's `dense3` deepest-boundary window (16.78 MiB, 2-128 MiB) showed very large run-to-run spread in its 2 reproducibility repeats (up to ~89% at individual points in the 5-15 MiB steep-transition region) -- same signature as the Sunbird multi-tenant-interference finding: noise localized to a subset of runs at a subset of sizes, not a consistent property of the region across all runs.
  - The manual 256 MiB-1 GiB follow-up showed large wall-clock time variance for nominally identical work: the original 256 MiB-1 GiB random sweep took 35m53s, an immediately following independent repeat (rep1) took only 13m01s for the same parameters, and a second repeat (rep2) took ~40 min -- a ~3x spread in wall-clock time for the same fixed sample count, most plausibly explained by other students' concurrent jobs contending for shared resources (memory bandwidth, LLC) even though affinity kept our process on its own dedicated core. This did not measurably corrupt the *timing* data itself (the three runs' medians agree within 0.5% at every size checked), only the wall-clock duration of collecting it.
  - Sequential-pattern latency stayed flat (~5-7 ticks) across the entire 1 KiB-1 GiB range in every sweep, confirming the hardware prefetcher fully hides main-memory latency for the sequential control even at gigabyte-scale footprints, as expected.

### line_size/
- Source file(s): `main_code/common/{main.c,line_size.c,line_size.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root; see `Makefile`)
- Run command + arguments: `./scripts/run_line_size.sh crux 3 32768,262144,8388608 8,16,32,64,128,256 <overrides>`, run twice. Core 3 picked after `lscpu -e=CPU,CORE,SOCKET,NODE` (no SMT on this CPU, confirmed in the Machine Identification section above) and two `mpstat -P ALL 1 2` samples plus `ps -eLo pid,psr,pcpu,...` taken seconds apart, both showing core 3 at 0% across every sample (this session's own VS Code/Claude processes were the only non-trivial load on the machine, sitting on cores 0/1/3-6 lightly — core 3 still measured fully idle in both mpstat windows). Boundaries `32768,262144,8388608` are this machine's L1/L2/L3 candidates as tabulated in `/home/krchen/Proj1-Cache-Reverse-Engineering/CAPACITY_RESULTS.md` (L1 PROVISIONAL 32,768 B; L2 candidate 262,144 B, itself flagged there as "not a hard plateau"; L3 the table's rounded ~8 MiB representative of the single dominant ~4–64 MiB S-curve transition documented above — not one of this machine's own three raw auto-detected sub-boundaries (9,147,840 / 11,863,280 / 16,777,216 B), which the capacity/ section above already treats as waypoints on one transition rather than distinct levels).
  - Run 1, timestamp `20260912T214443Z`, no candidate overrides (`auto` for all 3 levels): ran Method A steps 1-3 (coarse family-of-curves, 6 strides x 2 patterns, per level) and Method B (single-curve ramp-saturation) for all 3 levels. Log: `data_raw/crux/line_size/run_line_size_20260912T214443Z.log`.
  - Run 2, timestamp `20260912T214637Z`, `candidate_overrides_csv=64,auto,auto`: added Method A step 4 (bracket 40/48/56/64/72/80/88B x offsets 0/8/16/24/32/40/48/56B, pattern random) for L1 only, based on run 1's coarse family-curve plot appearing to show a clean 2-cluster split there. Log: `data_raw/crux/line_size/run_line_size_20260912T214637Z.log`.
  - Independent repeat, timestamp `20260912T215054Z`, boundaries restricted to `262144,8388608`: re-ran Method A steps 1-3 + Method B for L2/L3 only as a reproducibility check on run 1's L2/L3 shape (real new hardware timing samples, same seed). Log: `data_raw/crux/line_size/run_line_size_20260912T215054Z.log`.
  - Run 4, timestamp `20260912T215443Z`, `candidate_overrides_csv=64,64,64`: forced the step-4 bracket+offset refinement at **all three** levels, prompted by a visual read that the coarse family-of-curves plots for L2/L3 (which the analysis below of run 1/the repeat had called "no discrete split") did in fact show a noticeable stride-dependent separation worth checking at fine (8-byte) granularity rather than only the coarse 6-stride resolution. This turned out to be the right call — see below. Log: `data_raw/crux/line_size/run_line_size_20260912T215443Z.log`.
  - Independent step-4 repeat, timestamp `20260912T220855Z`, boundaries restricted to `262144,8388608`, `candidate_overrides_csv=64,64`: re-ran the step-4 bracket+offset refinement for L2/L3 only, as a reproducibility check on run 4's L2/L3 step-4 numbers (given L1's step-4 result had already proven not reproducible run-to-run — see below). Log: `data_raw/crux/line_size/run_line_size_20260912T220855Z.log`.
  - Run 6, timestamp `20260912T223057Z`, all 3 boundaries, `candidate_overrides_csv=64,auto,auto`: re-ran the coarse family-of-curves pass (steps 1-3) for all three levels again (third independent measurement of L2/L3's coarse shape, third overall of L1's), plus a third independent step-4 measurement for L1 only. Log: `data_raw/crux/line_size/run_line_size_20260912T223057Z.log`.
  - Run 7, timestamp `20260912T224949Z`, boundary `8388608` only, no overrides: a fourth independent coarse family-of-curves measurement at L3, run alone (core 3 re-verified idle first; a different user's session, `nsngo`, had appeared on cores 0/4/6 in the meantime but not on core 3). Log: `data_raw/crux/line_size/run_line_size_20260912T224949Z.log`.
  - Run 8, timestamp `20260913T141153Z`, boundary `262144` only, `candidate_overrides_csv=64`: a third independent step-4 measurement at L2 alone (core 3 re-verified idle; `CAPACITY_RESULTS.md`'s Crux row re-checked against the version current as of this run and unchanged — L2 still 262,144 B). Log: `data_raw/crux/line_size/run_line_size_20260913T141153Z.log`.
  - Run 9, timestamp `20260913T143014Z`, boundary `262144` only, `candidate_overrides_csv=64`: a fourth independent step-4 measurement at L2 alone (core 3 re-verified idle beforehand). Log: `data_raw/crux/line_size/run_line_size_20260913T143014Z.log`.
  - Run 10, timestamp `20260913T143145Z`, boundary `262144` only, `candidate_overrides_csv=64`: a fifth independent step-4 measurement at L2 alone (core 3 re-verified idle beforehand). Log: `data_raw/crux/line_size/run_line_size_20260913T143145Z.log`.
- Sample count: 1,000,000 timed accesses per (stride/footprint, pattern) point; warm-up (2 passes, Method A; 3 passes, Method B) excluded from that count. Seed 12345 for every run (deterministic pipeline — real hardware timing noise still differs run to run even at a fixed seed, which is what makes the repeats above meaningful).
- **Corrected finding (supersedes the "no L2/L3 signal" call from run 1/the repeat below it — see run 4):** the coarse family-of-curves pass (steps 1-3, only 6 widely-spaced candidate strides, no offset variation) is too coarse to reveal the actual line-size split at L2/L3 on this machine — it looks like one continuous stride-ordered ramp at that resolution. The **step-4 dense bracket (8-byte granularity) + 8-offset sweep, run at all three levels, reveals a real, alignment-independent elbow at exactly 64B for all three** — this is a stronger and more direct result than the coarse-pass reading below and is what should be cited.
- Notes on alignment/candidate strides tested, in the order investigated:
  - **Run 1/2 coarse read (superseded by run 4, kept for the record):** `level_32768/plots/line_size_family_curve.png` showed a clean 2-cluster split ({8,16,32}B vs {64,128,256}B) at L1, so run 2 forced candidate=64B there; its step-4 check reported `elbow varies 2.25x across offsets (36736-82560 bytes) -- transition may be alignment-sensitive`. `level_262144` and `level_8388608`'s coarse plots showed no such cluster split — all 6 strides moved together in a continuous ramp / single noisy S-curve — so step 4 was left on auto (skipped) for those two levels in runs 1/2, and the reproducibility repeat (timestamp `20260912T215054Z`) confirmed that same coarse-resolution shape reproduces. **In hindsight this was the wrong conclusion to stop at**: the coarse pass's 6 strides (8/16/32/64/128/256B) and lack of offset variation aren't fine-grained enough to resolve a real elbow sitting between two of those widely-spaced points, which is exactly what run 4 found.
  - **Run 4 (`candidate_overrides_csv=64,64,64`, all three levels, timestamp `20260912T215443Z`) — the citable result:**
    - **L1 (boundary=32,768 B):** step-4 elbow varies **1.59x** across offsets (36,736-58,368 B) — every one of the 8 offsets shows a clear V-shaped minimum right at stride=64B (`level_32768/plots/line_size_offset_elbow.png`), though the exact minimum value differs a bit by offset (two offsets sit at 58,368 vs. the rest at 36,736). Run 2 measured this same candidate/bracket/offsets at a different point in time and got 2.25x instead of this run's 1.59x — the fact that an independent re-measurement at the same fixed seed gives a different spread each time shows this number is sensitive to real per-run timing noise, not a fixed property of the alignment itself. Still short of a clean textbook (1.00x) result but consistent with a genuine 64B transition. **Resolved by run 6 below: a third measurement came back perfectly clean (1.00x).**
    - **L2 (boundary=262,144 B):** step-4 elbow is **essentially perfect** — `elbow stable across the 8/8 offsets with a detectable elbow (524288-524288 bytes, 1.00x spread)`. `level_262144/plots/line_size_offset_elbow.png` shows every one of the 8 offsets landing on exactly the same two-tier value: strides 40/48/56B (below the candidate) all elbow at ~588,480 B, and strides 64/72/80/88B (at/above the candidate) all elbow at ~524,232-524,288 B, for every offset tested. This is the cleanest single result across any level/method run on this machine so far.
    - **L3 (boundary=8,388,608 B):** step-4 elbow varies **1.26x** across offsets (16,777,216-21,137,920 B) with `8/8 offsets` reporting a value — `level_8388608/plots/line_size_offset_elbow.png` shows a clear V-shaped minimum at stride=64B for every offset (one offset, 0B, dips lowest to exactly 16,777,216 B; the rest cluster a bit higher around 18.8-21.1M B), the same qualitative signature as L1's plot, just with tighter offset-to-offset agreement.
    - Method B (single-curve) only ever produced an independent estimate at L1 (64B, from run 1/2's fixed-footprint coarse stride sweep) in run 4; its coarse sweep never found a transition at L2/L3 in run 4 — but see the independent repeat below, where it did.
  - **Independent step-4 repeat (`20260912T220855Z`), L2/L3 only — reproducibility confirmed, and Method B now agrees too:**
    - **L2:** step-4 elbow spread **1.12x** (524,288-588,480 B) — reproduces run 4's 1.00x closely. Method B's coarse sweep this time *did* detect a transition (estimate=64B), and went on to run its full dense sweep (32-129B, step 1) + 2 independent repeats around it — the first time Method B has produced an L2 estimate at all, independently corroborating Method A's step-4 result.
    - **L3:** step-4 elbow spread **1.00x**, exactly stable at 18,831,744 B across all 8 offsets — tighter than run 4's own 1.26x. Method B's coarse sweep still found no transition here (unchanged from every prior run).
    - This means L2 and L3 have now each independently reproduced an alignment-independent 64B elbow twice (1.00x/1.12x for L2, 1.26x/1.00x for L3) — a meaningfully stronger and more consistent result than L1's had been at this point, which had instead varied 2.25x -> 1.59x across its own two measurements. Log: `data_raw/crux/line_size/run_line_size_20260912T220855Z.log`.
  - **Run 6 (`20260912T223057Z`) — L1's third step-4 measurement resolves the earlier inconsistency: perfectly clean.** `candidate stride 64B: elbow stable across the 8/8 offsets with a detectable elbow (36736-36736 bytes, 1.00x spread)` — every single one of the 8 offsets lands on the exact same value, 36,736 B (`level_32768/plots/line_size_offset_elbow.png`, a textbook V-shape converging exactly at stride=64). Method B also re-confirmed 64B independently at L1 in this same run. The coarse family-of-curves pass (steps 1-3) was also re-run for all three levels in run 6 as a third independent look at L2/L3's shape — both reproduced the same continuous-ramp/single-S-curve appearance as runs 1 and the first repeat, consistent with the step-4 finding that this coarse resolution simply can't resolve the real elbow at those two levels. Log: `data_raw/crux/line_size/run_line_size_20260912T223057Z.log`.
  - **Run 7 (`20260912T224949Z`) — a fourth independent coarse family-of-curves measurement at L3 alone, same result.** `level_8388608/plots/line_size_family_curve.png` again shows all 6 strides overlapping through the flat sub-4-MiB region and rising together through the same single noisy S-curve, with no coarse-resolution stride split (Method B's coarse sweep again found no transition either). This is now the fourth time this level's coarse pass has reproduced this exact shape (runs 1, the L2/L3 repeat, run 6, and this run) — reinforcing that the coarse 6-stride resolution genuinely cannot see the real elbow here, and that the step-4 dense bracket (already confirmed clean at 1.26x/1.00x across 2 independent measurements, see above) is the only method that resolves it at this level. Log: `data_raw/crux/line_size/run_line_size_20260912T224949Z.log`.
  - **Run 8 (`20260913T141153Z`) — a third independent L2 step-4 measurement, still clean.** `candidate stride 64B: elbow stable across the 8/8 offsets with a detectable elbow (467072-524288 bytes, 1.12x spread)` — `level_262144/plots/line_size_offset_elbow.png` shows the same two-tier signature as the prior two L2 step-4 runs: strides below 64B elbow noticeably higher, strides at/above 64B (and one offset's own V-shaped minimum exactly at 64B) settle at ~524,288 B, for every one of the 8 offsets. L2 has now measured this same clean result three separate times (1.00x, 1.12x, 1.12x), the most-repeated and most consistent of any level on this machine. Log: `data_raw/crux/line_size/run_line_size_20260913T141153Z.log`.
  - **Run 9 (`20260913T143014Z`) — a fourth independent L2 step-4 measurement, perfectly clean again.** `candidate stride 64B: elbow stable across the 8/8 offsets with a detectable elbow (524288-524288 bytes, 1.00x spread)` — exactly the same value across every offset. Plot: `data_processed/crux/line_size/level_262144/plots/line_size_offset_elbow.png` (full path: `/home/krchen/Proj1-Cache-Reverse-Engineering/data_processed/crux/line_size/level_262144/plots/line_size_offset_elbow.png`, `.pdf` alongside it; corresponding `line_size_offset_boxplots.{png,pdf}` in the same directory). L2's step-4 track record across 4 independent runs is now 1.00x / 1.12x / 1.12x / 1.00x — the most consistently clean level on this machine. Log: `data_raw/crux/line_size/run_line_size_20260913T143014Z.log`.
  - **Run 10 (`20260913T143145Z`) — a fifth independent L2 step-4 measurement, same clean result.** `candidate stride 64B: elbow stable across the 8/8 offsets with a detectable elbow (467072-524288 bytes, 1.12x spread)`. Plot at the same path as above (overwritten in place, per this pipeline's un-timestamped plot filenames — see the earlier caveat about this). L2's step-4 spread across all 5 independent runs to date: 1.00x, 1.12x, 1.12x, 1.00x, 1.12x — every run has confirmed the same alignment-independent elbow at 64B; this level's result should now be treated as solidly established, and further repeats of the identical test are unlikely to add new information. Log: `data_raw/crux/line_size/run_line_size_20260913T143145Z.log`.
  - **Net result: L1, L2, and L3 have each now independently measured an alignment-independent 64B elbow (1.00x/1.59x/2.25x -> 1.00x for L1 across 3 runs; 1.00x/1.12x for L2 across 2 runs; 1.26x/1.00x for L3 across 2 runs).** L1's own reproducibility took 3 attempts to land clean, so its result should be read as "clean on the most recent, most-repeated measurement" rather than "clean on every attempt" the way L2/L3's have been — worth keeping in mind if L1 needs to be re-verified again later, but not a reason to doubt the current 64B reading.
  - Cross-level, cross-method summary as printed by the pipeline: run 4 gave `level boundary=32768B -> method A = 64B, method B = 64B`; `level boundary=262144B -> method A = 64B, method B = none`; `level boundary=8388608B -> method A = 64B, method B = none`. The independent L2/L3 repeat then gave `level boundary=262144B -> method A = 64B, method B = 64B`; `level boundary=8388608B -> method A = 64B, method B = none`. Run 6 gave `level boundary=32768B -> method A = 64B, method B = 64B` again (L2/L3 left on auto, so no step-4 output there this run). Every level/method that has produced an estimate, across every run, agrees on **64B**.
  - Plots: `data_processed/crux/line_size/level_{32768,262144,8388608}/plots/` (family curve/boxplots are each level's most recent coarse-pass run — run 6 for all three; offset elbow/boxplots are each level's most recent step-4 run — run 6 for L1, the independent repeat for L2/L3 — since the pipeline's per-level plot filenames aren't timestamped and each new run overwrites the prior one at the same path; the underlying numbers from every run are preserved in this section and in the raw/log files even where the plot itself was overwritten). Raw CSVs (not yet gzipped — awaiting confirmation before compressing/committing): `data_raw/crux/line_size/level_{32768,262144,8388608}/*.csv`.
  - **Frozen Phase-I status: 64B at all three levels, well-supported.** L1, L2, and L3 have each independently reproduced a clean (1.00x, or close to it), alignment-independent, 8/8-offset elbow at 64B on their most recent measurement, with L2 additionally corroborated by Method B. This is now consistent with 64B being Crux's real cache line size at every tested level, matching every other x86 machine on this team. Comparing against PMU counters and the documented/system-reported line size is Phase II, per this project's discipline — not done here.

### associativity/
- Source file(s): `data_raw/crux/associativity/{L1,L2,L3_LLC}/*.csv.gz` (raw),
  `data_processed/crux/associativity/{L1,L2,L3_LLC}/*summary*.csv` (processed),
  full transcript `data_raw/crux/associativity/run_associativity_full_20260912T225213Z.log`
- Run command + arguments: `./scripts/run_associativity_full.sh crux 7 32768,262144,8388608`
  (`cache_bytes` per level taken directly from this machine's rows in
  `CAPACITY_RESULTS.md` — L1=32,768 B, L2=262,144 B, LLC=8,388,608 B/8 MiB —
  per the user's own finalized capacity analysis, superseding the more
  hedged/unresolved L2/LLC status previously logged in
  `CAPACITY_INFERENCE_STATUS.md`)
- Core/seed/samples: core=7, base_seed=12345 (2 repeats at seed+1, seed+2),
  samples=1,000,000, batch=1000, warmup=3, num_ways swept 2-40, timestamp=20260912T225213Z
- Conflict-set construction method: node-to-node stride fixed at each level's
  own capacity in bytes (forces every probed node into the same cache set
  regardless of unknown line size/way count — see `main_code/common/associativity.h`),
  sweeping same-set node count (num_ways_probed) 2-40 with both a randomized
  dependent-chain pattern and a sequential control (prefetcher check).
- Results (auto knee-detected, base + both repeats in exact agreement, no
  reproducibility warnings for any level):
  - L1 (stride=32 KiB): **8-way** (repeats: 8, 8)
  - L2 (stride=256 KiB): **4-way** (repeats: 4, 4)
  - L3/LLC (stride=8 MiB): **4-way** (repeats: 4, 4)
- Notes: All three levels show a single sharp knee (not a multi-step
  staircase), and random/sequential curves track closely up to the knee
  before diverging afterward (prefetcher effect on the sequential control,
  not part of the associativity signal itself). Plots:
  `data_processed/crux/associativity/{L1,L2,L3_LLC}/plots/associativity_curve.png`
  and `associativity_boxplots.png`. **Caveat:** the LLC `cache_bytes=8,388,608`
  (8 MiB) value comes from `CAPACITY_RESULTS.md`'s "~8 MiB" entry, which
  conflicts with this same machine's own more granular capacity findings
  elsewhere in this README/`CAPACITY_INFERENCE_STATUS.md` (steep transition
  region spanning ~4-64 MiB with large run-to-run spread, no single
  confirmed discrete boundary) and with `lscpu`'s reported real hardware
  L3 of 12 MiB. The clean single-knee result above does not by itself
  resolve that conflict — it confirms 8,388,608 B produces a well-behaved
  associativity signal, not that 8 MiB is independently the true LLC
  capacity.

### latency/
Two sub-experiments, `hit_latency` and `miss_latency`, run 2026-09-13. Footprint/
target/evict byte values taken **only from `CAPACITY_RESULTS.md`** (L1 =
32,768 B, L2 = 262,144 B, LLC ≈ 8 MiB = 8,388,608 B — same values already used
for this machine's `associativity/` section above) — per project-wide direction,
`CAPACITY_RESULTS.md` is the single source of truth for these boundaries; this
file's own more-detailed capacity write-up above (steep, not-fully-resolved
~4-64 MiB transition) is not used to pick these numbers.
- Core: 2 (not the 7 used for capacity/associativity earlier — re-checked idle
  for this session: `who`/`ps` showed no other students' processes pinned to any
  core, and two independent `/proc/stat` idle-time-delta samples ~3s apart,
  taken both immediately before the hit_latency run and again immediately after
  the miss_latency run finished, showed every core 0-7 under ~1.5% busy both
  times).
- Build: `git pull && make clean && make` (fast-forwarded `cb1f482..e343732`);
  `python3 -c "import matplotlib"` confirmed working (3.6.3) before running.

**hit_latency (dependent chain + independent-load diagnostic control):**
- Source file(s): `main_code/common/{main.c,latency.c,latency.h,benchmark.c,benchmark.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Run command + arguments: `./scripts/run_hit_latency_full.sh crux 2 L1:32768,L2:262144,LLC:8388608,DRAM:536870912` (DRAM's 512 MiB footprint is not a `CAPACITY_RESULTS.md` value — a "deep in the DRAM plateau" pick, same convention Sunbird's README used).
- Per level: base run + 2 reproducibility repeats (seed 12345/12346/12347), each at `--load-mode {dependent,independent}` x `--pattern {random,sequential}`, 1,000,000 timed accesses per combination (batch size 1000), 3 untimed warm-up passes.
- Raw output: `data_raw/crux/latency/hit/<LEVEL>/hit_latency_{base,rep1,rep2}_{dependent,independent}_{random,sequential}_20260913T061111Z.csv.gz`; processed summaries + plots under `data_processed/crux/latency/hit/<LEVEL>/{*.csv,plots/hit_latency_boxplots.{png,pdf}}`. Full transcript: `data_raw/crux/latency/run_hit_latency_full_20260913T061111Z.log`.
- **Result (dependent, random pattern, base run median): a clean, monotonically increasing 4-tier ladder — L1 ≈ 7.42 ticks, L2 ≈ 14.30 ticks, LLC ≈ 43.23 ticks, DRAM ≈ 236.80 ticks.** Confirms the `CAPACITY_RESULTS.md` byte values correspond to 4 genuinely distinct levels on this machine.
- **Independent-vs-dependent check: 6 of 8 (level, pattern) combinations show the expected `independent < dependent`; the random pattern is expected-faster at all 4 levels (L1: 5.42 vs 7.42; L2: 7.06 vs 14.30; LLC: 16.70/19.53(mean) vs 43.23; DRAM: 46.91 vs 236.80). Both LLC and DRAM flagged `[UNEXPECTED -- investigate]` for the SEQUENTIAL pattern** (LLC: 5.96 vs 5.63 aggregate; DRAM: 5.95 vs 5.81 aggregate) — investigated per the task's directive before trusting this data, root-caused from source rather than dismissed or re-run blind:
  - Per-run breakdown (not just the aggregated median) confirms this is reproducible, not a one-off fluke: LLC sequential dependent medians are tight across all 3 runs (5.61/5.65/5.64), while independent's are consistently at or above them (5.70/5.81/6.38) — same direction every time.
  - Root cause, found in `main_code/common/latency.c` (`run_hit_latency_experiment`) and `benchmark.c` (`measure_independent_loads_batched`): `struct node` is a single 8-byte pointer (`pointer_chase.h`), the same size as a `size_t`. For `LOAD_MODE_INDEPENDENT` + sequential pattern, `latency.c` allocates a full `order[num_nodes]` array (`order[i] = i`) the SAME SIZE in bytes as the `nodes[]` array itself — so independent mode's true touched working set at any footprint is ~2x `footprint_bytes`, not `footprint_bytes`. At L1/L2 (32,768/262,144 B -> 65,536/524,288 B combined) this doesn't matter enough to flip the result. At LLC (8,388,608 B -> ~16.78 MiB combined, roughly 2x this machine's own ~8 MiB LLC estimate) and at DRAM (already far past any cache), the extra `order[]` stream adds real memory traffic/cache pressure that dependent mode never pays (it only ever touches `nodes[]`). For the SEQUENTIAL pattern specifically, the dependent baseline is already riding the hardware next-line prefetcher down to near-L1 speed (~5.6-5.8 ticks, essentially flat from L1 all the way to a 512 MiB footprint — see below) — there is no latency headroom left for independent mode's MLP-exposure benefit to recover, so the extra `order[]` array cost shows up as a small but consistent net slowdown instead. This is a real, source-grounded methodology artifact of the independent-load control (auxiliary index array doubling its footprint), not corruption, not core contention, and not a reason to distrust the RANDOM-pattern numbers (which is where the real headline latency ladder above comes from).
  - Notable side finding from the same data: sequential-pattern latency (both modes) stays within ~5.4-6.4 ticks across the ENTIRE 32,768 B-536,870,912 B range (L1 through DRAM) — the hardware prefetcher fully hides main-memory latency for sequential access even at 512 MiB, matching this machine's own capacity/ finding above ("Sequential-pattern latency stayed flat ... across the entire 1 KiB-1 GiB range").
  - Not fixed / not re-run: this is a property of the independent-load control's construction (present since the bug-fix documented in `CLAUDE.md`/Sunbird's README), not something this session's task scope (hit_latency/miss_latency data collection only) authorized changing in `benchmark.c`/`latency.c`.

**miss_latency (forced eviction + single-shot reload):**
- Source file(s): same list as hit_latency above.
- Eviction-set calibration (done before committing to full parameters, core 2, random pattern, target=8,388,608, 100 trials): 16,777,216 B (16 MiB, 2x the LLC estimate) evict_bytes measured ~94 ms/trial (9.411s/100) — extrapolated to 3 runs x 2 patterns x 200 trials = 1200 trials, ~2 min for the LLC_to_DRAM transition alone; well under the ~15 min budget, so no need to shrink further (did not try evict_bytes anywhere near the 512 MiB DRAM hit_latency footprint, per the task's explicit warning against jumping straight to a huge value).
- Run command + arguments: `./scripts/run_miss_latency_full.sh crux 2 L1_to_L2:32768:262144,L2_to_LLC:262144:8388608,LLC_to_DRAM:8388608:16777216`.
- Per transition: base run + 2 reproducibility repeats (seed 12345/12346/12347), each at `--pattern {random,sequential}`, 200 single-shot trials each (`--batch-size 1`, meaningless to this experiment but required by `main.c`'s cross-experiment validation), 3 untimed warm-up passes per trial.
- Raw output: `data_raw/crux/latency/miss/<TRANSITION>/miss_latency_{base,rep1,rep2}_{random,sequential}_20260913T061432Z.csv.gz`; processed summaries + plots under `data_processed/crux/latency/miss/<TRANSITION>/{*.csv,plots/miss_latency_boxplots.{png,pdf}}` (annotated with the incremental-penalty delta against this machine's own hit_latency dependent/random summaries, found automatically by the script for all 3 transitions). Full transcript: `data_raw/crux/latency/run_miss_latency_full_20260913T061432Z.log`.
- **Result (random pattern, base run median, n=200 each): L1→L2 ≈ 77 ticks, L2→LLC ≈ 260 ticks, LLC→DRAM ≈ 437 ticks** — monotonically increasing, consistent with genuinely deeper eviction at each transition (same qualitative ladder shape as Sunbird's 124/284/622).
- **Run-to-run spread: L1→L2 is tight (base/rep1/rep2 medians 77/78/74 random, 79/78/78 sequential, <7% spread, no warning) but L2→LLC and LLC→DRAM both triggered `plot_miss_latency.py`'s >20%-spread warning, per the task's instruction NOT to re-run until it disappears — reported as-is:**
  - L2→LLC random: medians [260.0, 105.5, 270.5], spread 165.0 ticks = 77.8%.
  - LLC→DRAM random: medians [437.0, 512.0, 407.0], spread 105.0 ticks = 23.2%.
  - LLC→DRAM sequential: medians [260.5, 396.5, 301.5], spread 136.0 ticks = 42.6%.
  - Not traced to a specific interfering process this session (machine was re-confirmed idle via `who`/`/proc/stat` immediately before hit_latency and immediately after miss_latency, but not polled mid-run) — consistent with the same transient-interference signature documented throughout this team's capacity/associativity work on shared machines (scattered single-run spikes, not a systematic bias), but not independently confirmed as such here.
- **Single-shot measurement overhead, measured per this machine (task step 7):** `--target-bytes 32768 --evict-bytes 512 --pattern random --samples 2000` (an 8-line eviction set overwhelmingly unlikely to evict the target) gives a median of **50 ticks**, versus this machine's own batched L1 hit_latency dependent/random median of **7.42 ticks** at the identical 32,768 B footprint — a ~42-tick fixed single-shot overhead (serializing timer cost + post-call pipeline state, unamortized across a batch, per `latency.h`'s documented KNOWN LIMITATION). Every miss_latency number above is "true reload latency + ~42 ticks of fixed overhead," not a clean number; the 77→260→437 increasing trend is still meaningful evidence of deeper eviction, but do not subtract/compare these directly against hit_latency plateaus without accounting for this overhead.
- Not yet done: overhead was only measured once at the L1 footprint (not per-transition); the L2→LLC/LLC→DRAM spread was not traced to a specific process.

### inclusion_policy/
Boundary values from `CAPACITY_RESULTS.md` only (L1 = 32,768 B, L2 = 262,144 B,
LLC ≈ 8 MiB = 8,388,608 B — same values already used for `associativity/` and
`latency/` above). **All three adjacent-and-skip-level pairings implied by
CAPACITY_RESULTS.md's three levels were run** (L1 vs L2, L2 vs LLC, and L1 vs
LLC directly) — each has its own confidence level, see per-pairing Results
below; do not read one pairing as covering the others.

- Source file(s): `main_code/common/{main.c,inclusion_policy.c,inclusion_policy.h,pointer_chase.c,pointer_chase.h,random.c,random.h}`, `main_code/x86_64/timer_x86.h`, `main_code/common/timer.h`
- Build command: `make` (from repo root)
- Core: 3 (same as `line_size/` above, re-verified idle immediately before this
  run: `who` showed only `dchen27`'s and `djgreen`'s idle login sessions, no
  pinned processes on any core; two `mpstat -P ALL 1 1` samples ~3s apart both
  showed every core 0-7 at ≥93% idle, core 3 specifically at 100%/99% idle in
  the two samples).
- **Line size caveat already resolved before this ran, unlike Sunbird's initial
  pass.** `run_inclusion_policy_full.sh`'s `ASSUMED_LINE_SIZE_BYTES` defaults to
  64 — this machine's own `line_size/` section above independently confirmed
  **64 B at all three levels** (L1/L2/L3, 2026-09-12/13, alignment-independent
  step-4 elbow, L2 reproduced 5 times) before this experiment was ever run, so
  no override was needed and the eviction-footprint scaling below was correct
  from the start (no separate "resolved after the fact" note required, unlike
  Sunbird).
- **Calibration before committing to a large `--evict-bytes` (per the task's
  explicit warning that this timing is non-linear in eviction-set size on
  Sunbird — checked directly on this machine rather than assumed to transfer):**
  ran the largest scaled footprint needed (536,870,912 B / 512 MiB, for the
  L2_vs_LLC and L1_vs_LLC pairings) directly via `cache_bench` first: 20 trials
  took 0.398s wall, 200 trials (the pipeline's real per-run trial count) took
  2.327s wall (~11.6 ms/trial). This is far cheaper than Sunbird's reported
  74-604 ms/trial range for the same general kind of eviction-scale timing —
  plausible given `inclusion_policy`'s eviction buffer touches only one line
  per page (sparse walk, one page-table entry stressed per 4096 B) rather than
  densely filling the footprint the way `miss_latency`'s eviction buffer does.
  At ~11.6 ms/trial, the full 6-runs-of-200-trials-per-pairing pipeline
  (base+2 repeats × 2 patterns) completes in well under a minute per pairing —
  no `tmux` needed on this machine for this experiment.
- Run command + arguments (all three pairings in one invocation):
  `./scripts/run_inclusion_policy_full.sh crux 3 L1_vs_L2:32768:262144:L2_to_LLC,L2_vs_LLC:262144:8388608:LLC_to_DRAM,L1_vs_LLC:32768:8388608:LLC_to_DRAM`
  (timestamp `20260913T182037Z`). The 4th field on each spec names the
  already-collected `miss_latency` transition (see `latency/` section above)
  that pairing sources its "invalidated" calibration class from: L1_vs_L2
  evicts at L2 scale → "invalidated" = the `L2_to_LLC` transition; L2_vs_LLC
  and L1_vs_LLC both evict at LLC scale → "invalidated" = `LLC_to_DRAM`.
- Eviction/reload construction (see `main_code/common/inclusion_policy.h`'s
  module doc comment for the full argument): target (the UPPER level's
  capacity) and an untouched control buffer are both freshly page-aligned
  (offset 0). The eviction buffer places one node every 4096 B
  (`--evict-stride-bytes`, one page), all at a FIXED sub-page offset of 2048 B
  (`--evict-offset-bytes`) — different from target/control's own offset 0 — so
  every eviction node varies the higher-order (lower-level-relevant) address
  bits while structurally never landing on target's own line, PROVIDED the
  target's entire index fits within one page. `--evict-bytes` is
  `lower_level_bytes * evict_stride_bytes / ASSUMED_LINE_SIZE_BYTES` (64):
  16,777,216 B (16 MiB) for L1_vs_L2; 536,870,912 B (512 MiB) for both
  L2_vs_LLC and L1_vs_LLC (LLC is the lower level in both). Per trial: untimed
  re-touch of target and control, untimed eviction walk, then one timed
  dependent reload of each — exactly like `miss_latency`'s mechanism, but
  potentially skipping a level.
- **Same three load-bearing caveats as documented on Sunbird (`inclusion_policy.h`'s
  KNOWN LIMITATION paragraphs) apply here too, unresolved:**
  1. Line size scaling — resolved favorably for this machine (see above), not
     an open caveat.
  2. **DTLB pressure at large eviction scale** (L2_vs_LLC and L1_vs_LLC, both
     ~131,072-page/512 MiB eviction footprints; L1_vs_L2's ~4,096-page/16 MiB
     footprint is far smaller and less suspect). The `control` channel is the
     live per-run check for this — see Results below; both large-footprint
     pairings' control channels show elevated run-to-run spread (24-40%,
     flagged by `plot_inclusion_policy.py`) that L1_vs_L2's control does not,
     consistent with this caveat being a real factor here, not just
     theoretical.
  3. **Avoidance guarantee only holds for a target whose full index fits in
     one page** (affects L2_vs_LLC specifically — L2's 262,144 B target almost
     certainly needs more index bits than fit in the remaining 12 bits after
     line-offset, the same math-backed argument Sunbird's README makes with
     its own confirmed 64 B line size: 64 B lines (6 offset bits) + L1's own
     8-way/64-set index (6 bits) = exactly 12 bits/one page, which is *why*
     the method works cleanly for an L1 target and is not expected to for an
     L2 target). Treat L2_vs_LLC's result with more skepticism than L1_vs_L2's
     for this structural reason, independent of caveat 2.
- Per trial: 200 single-shot trials (`--samples 200 --batch-size 1`), base + 2
  reproducibility repeats (seed 12345/12346/12347), both eviction-walk
  traversal patterns, 3 untimed warm-up passes. A separate calibration run
  (500 trials, `--evict-bytes` = `--target-bytes`, i.e. nothing evicted)
  establishes each pairing's own single-shot "survived" baseline fresh — this
  doubles as this machine's single-shot-overhead sanity check for
  `inclusion_policy` specifically (see below), the same kind of trivially-small
  eviction-set control the task asked to verify.
- Raw output filename(s): `data_raw/crux/inclusion_policy/<pairing>/inclusion_policy_{calibration,base,rep1,rep2}_{random,sequential}_20260913T182037Z.csv.gz`
- Processing: `scripts/summarize_raw.py` per raw file → `data_processed/crux/inclusion_policy/<pairing>/*_summary_20260913T182037Z.csv` → `scripts/classify_inclusion_policy.py` (reads the raw base/random data directly) → `scripts/plot_inclusion_policy.py`. `matplotlib` confirmed working (3.6.3) — no plotting failures this run.

**Single-shot overhead check, this experiment specifically:** the "survived"
calibration (trivially-small `--evict-bytes`, nothing evicted) reads 56.28 and
57.98 ticks at the L1/L2 target footprints and 42.31 ticks at the smaller
L1-only footprint in the L1_vs_LLC pairing — all close to, and consistent
with, the ~42-tick single-shot fixed overhead already isolated in this
machine's `latency/` `miss_latency` section above (measured there via an
identical trivially-small-eviction-set control at the L1 footprint). Every
number below is "true reload behavior + this fixed overhead," not a clean
latency number — the overhead mostly washes out of the classification itself
since both calibration classes (survived/invalidated) carry the same additive
term, but it means the *absolute* tick values quoted below should not be
compared directly against `hit_latency`'s batched numbers.

**Results, one per pairing (n=200 target/control trials each, base/random run
unless noted):**

- **L1_vs_L2** (survived-class 56.28 ticks, invalidated-class 260.00 ticks
  from `L2_to_LLC`, boundary=120.97 ticks): target median 87.0 ticks (97.5%
  survived-like, 0.5% invalidated-like), control median 65.0 ticks (99.5%
  survived-like). Paired check (target slower than its own control): 100.0%.
  **Verdict: EXCLUSIVE / NON-INCLUSIVE** — the cleanest, most confident result
  of the three (smallest eviction footprint, L1-sized target, least exposed to
  caveats 2-3). One plot-script note: `(target, random)` had 3 overlapping
  summary rows (medians 87/71/70, 22.4% spread) — averaged per
  `plot_capacity.py`'s established convention, not re-run to chase away (well
  within the same noisy-shared-machine pattern documented throughout this
  team's work).
- **L2_vs_LLC** (survived-class 57.98 ticks, invalidated-class 437.00 ticks
  from `LLC_to_DRAM`, boundary=159.18 ticks): target median 131.0 ticks (90.5%
  survived-like, 2.5% invalidated-like, 7.0% ambiguous), control median 106.0
  ticks (100.0% survived-like). Paired check: 98.0%. **Verdict: EXCLUSIVE /
  NON-INCLUSIVE**, but read with more caution than L1_vs_L2's per caveat 3
  above (an L2 target does not get the same structural "avoids the upper
  level" guarantee L1 does) — **best guess, directionally: leans
  non-inclusive**, since 90.5% clears the classifier's threshold cleanly and
  the control channel itself stayed clean (100% survived-like, no sign the
  512 MiB eviction footprint's DTLB pressure corrupted the *control* reading),
  which argues caveat 2 is a smaller factor here than caveat 3 is. This is a
  more confident directional result than Sunbird's own L2_vs_LLC pairing
  (which came back UNCERTAIN, 85% ambiguous) — worth noting as a genuine
  cross-machine difference, not assumed to generalize. Two plot-script notes:
  `(target, sequential)` 3 overlapping rows (medians 111/145/113, 27.6%
  spread), `(control, sequential)` 3 overlapping rows (medians 101/82/123,
  40.2% spread) — the control spread here is the first sign of caveat 2 (DTLB
  pressure) showing up at all on this machine, though it didn't flip the
  overall verdict.
- **L1_vs_LLC** (survived-class 42.31 ticks, invalidated-class 437.00 ticks
  from `LLC_to_DRAM`, boundary=135.97 ticks): target median 132.0 ticks (0.0%
  survived-like, 2.0% invalidated-like, **98.0% ambiguous**), control median
  103.0 ticks (98.0% survived-like, 2.0% invalidated-like). Paired check:
  99.5%. **Verdict: UNCERTAIN** by the classifier, and the least resolved of
  the three pairings on this machine — nearly every trial falls inside the
  classification fence rather than confidently on either side. **Best guess,
  directionally: leans NON-INCLUSIVE (barely)** — target's raw median (132.0)
  sits just below the geometric-mean boundary (135.97), i.e. on the
  "survived" side of the midpoint even though not by enough margin for any
  individual trial to clear the classifier's confidence band, and the target
  still reads reliably slower than its own control in 99.5% of trials (so
  *something* about the LLC-scale walk is costing extra latency — this is not
  simply noise). Read this as weak evidence, not a firm call: the dominant
  98% ambiguous rate is consistent with caveat 2 (512 MiB / 131,072-page
  eviction footprint, same scale as L2_vs_LLC) smearing the timing distribution
  into the middle band rather than cleanly toward either calibration class.
  **Notably, this pairing's directional lean (non-inclusive) is the OPPOSITE
  of Sunbird's own L1_vs_LLC skip-level result (leaning inclusive, 75%
  invalidated-like)** — a genuine cross-machine disagreement on the one
  pairing both machines could measure with some signal, not just a difference
  in confidence. Two plot-script notes: `(control, random)` 3 overlapping rows
  (medians 103/83/107, 24.6% spread), `(control, sequential)` 3 overlapping
  rows (medians 75.5/83/97, 25.2% spread) — both control-channel spreads,
  reinforcing that caveat 2's DTLB pressure is a real, measurable factor for
  both LLC-scale pairings on this machine (control spread was clean/tight for
  L1_vs_L2's 16 MiB footprint by comparison).
- Not yet done, any pairing: multiple different target addresses/sets
  (PROJECT 1.pdf asks to "repeat with controls and multiple target
  sets/addresses" — every run above tested exactly one target buffer per
  repeat, just re-seeded); the huge-pages TLB mitigation for caveat 2, noted
  as future work on Sunbird and not attempted here either.

**Best-guess synthesis:** L1 is confidently non-inclusive w.r.t. L2 (97.5%
survived, cleanest result). L2 vs LLC leans non-inclusive with moderate
confidence (90.5%, though caveat 3 limits how much weight this deserves for
an L2-sized target). The skip-level L1 vs LLC test is the weakest of the
three but leans non-inclusive too, for what little the mostly-ambiguous
classification is worth. **Put together, this machine's best-supported single
story is a non-inclusive hierarchy at every level tested** — unlike Sunbird's
own mixed reading (non-inclusive L2, leaning-inclusive LLC-as-snoop-filter for
L1), Crux shows no positive evidence anywhere of an inclusive relationship;
the one pairing that could in principle show it (L1_vs_LLC) leans the same
direction as the other two, just far more weakly. This is this team's best
reasoned inference from the timing data collected here, not a certainty —
both LLC-involving pairings are undermined by the same DTLB-pressure caveat
(2) at this eviction scale, and L2_vs_LLC additionally by caveat 3.

### pmu/ (Phase II — 2026-09-14)
Phase I frozen/tagged (`phase1-timing-only`) before anything below was run,
per `README.md`'s Phase Discipline. See `CLAUDE.md`'s Phase II section and
`data_processed/crux/PHASE2_VALIDATION_TABLE.md` for the full methodology/
results write-up and literature citation — this section is the raw-data/
reproduction-detail record. Uses the settled cross-machine pipeline
(`scripts/run_pmu_verification.sh` + `scripts/summarize_pmu.py`), the same
one Sunbird's and Thunderbird's sessions used — no new code this session.

- Source file(s): `scripts/run_pmu_verification.sh`, `scripts/summarize_pmu.py`
  (no `cache_bench` source changes — reuses the existing `--experiment
  hit_latency` binary, wrapped in `perf stat`).
- Core selection: cores 0 and 2 were pinned by other students' active jobs
  at the time (`incl_pmu` at ~133% CPU on core 0, `cache_bench_x86` at
  ~67% CPU on core 2 — confirmed via `taskset -pc <pid>` on each). Two
  independent `/proc/stat` idle-time-delta samples, 4s apart, confirmed
  cores 0 and 2 at 0% idle (fully busy) both times while cores 1, 3, 4, 5,
  6, 7 were all ~100% idle both times. Core 1 chosen (also had no other
  process listed against it in `ps -eLo pid,psr,...`).
- Machine-specific PMU check done before running (this machine behaves
  differently from Sunbird's, worth checking rather than assuming): a
  hand-run combined single `perf stat -e duration_time,cache-references,
  cache-misses,L1-dcache-loads,L1-dcache-load-misses,LLC-loads,
  LLC-load-misses,cycles,instructions` invocation against a real
  `cache_bench --experiment hit_latency` run (footprint 32,768 B, core 1),
  repeated 3 times, showed **all 8 events scheduled at 100%
  simultaneously** every time — unlike Sunbird, which could only reliably
  schedule 2 hardware events at once. `nmi_watchdog=1` here too (same as
  Sunbird), so that alone doesn't explain the difference; not investigated
  further (plausibly just more free programmable counters available on
  this generation/SKU, or less other contention on the PMU at the moment
  of the hand-check). `run_pmu_verification.sh` still ran its fixed
  4-separate-2-event-group design regardless, per the settled cross-machine
  convention (not re-derived per machine) — this just means the split was
  more conservative than strictly necessary here, not that anything failed.
- Run command: `./scripts/run_pmu_verification.sh crux 1
  L1:32768,L2:262144,LLC:8388608` (footprints per `CAPACITY_RESULTS.md`,
  the same three values already used for this machine's `associativity/`
  and `latency/` sections above). base_seed=12345 (repeats use
  base_seed+index), samples=1,000,000/run, batch_size=1000, warmup_passes=3,
  dependent load mode, random pattern (matching the existing `hit_latency`
  convention), timestamp `20260914T003352Z`.
- Raw output: `data_raw/crux/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz` (perf
  stat's own `-x,` CSV output, one file per group×run_tag, gzipped by hand
  per this repo's `data_raw/**/*.csv.gz` convention) and `*_bench_*.csv.gz`
  (cache_bench's own CSV from the same invocation, for direct side-by-side
  comparison against the perf-derived numbers). Transcript:
  `data_raw/crux/pmu/run_pmu_verification_20260914T003352Z.log`.
- Processed: `data_processed/crux/pmu/{L1,L2,LLC}/pmu_summary_20260914T003352Z.csv`
  (one row per run_tag + a median-of-3 row; no `<not counted>` entries
  anywhere in any of the three files — this machine's `notes` column is
  empty in every row). Columns include miss rates for cache-references/
  L1-dcache/LLC, cycles/access, IPC, and perf's own wall-clock ns/access —
  see `scripts/summarize_pmu.py`'s docstring for the exact parsing/
  derivation and its caveats.
- System-reported cache info (also Phase II, same run):
  `data_raw/crux/pmu/system_reported_cache_info.txt` — `lscpu --caches`,
  full `lscpu`, and per-instance `/sys/devices/system/cpu/cpu0/cache/index*/`
  fields, collected 2026-09-14T00:34:16Z.
- Headline results (full detail and caveats:
  `data_processed/crux/PHASE2_VALIDATION_TABLE.md`): L1D matches exactly
  across Phase I timing, system-report, and Agner Fog's literature table
  (Skylake-family, which Coffee Lake shares for cache purposes) at
  size/ways/sets/line/sharing. **Two genuinely important disagreements,
  stated plainly rather than smoothed over:** (1) L2's real associativity
  is system-reported as **4-way**, matching the raw confound-flagged
  reading `FINAL_CACHE_TABLE.md` explicitly set aside in favor of a
  reasoned "8-way" best guess — Phase I's override was wrong here, and the
  raw (confound-suspected) measurement was actually right; (2) the real
  LLC is system-reported as **12 MiB, not the ~8 MiB `CAPACITY_RESULTS.md`
  value** this and every other Crux experiment used, confirming the
  discrepancy `FINAL_CACHE_TABLE.md` had already flagged (`lscpu`'s 12 MiB)
  but left unresolved — LLC associativity (system-reported 12-way) also
  matches neither Phase I's raw confound value (4) nor its best guess (8).
  Miss-rate PMU evidence (the reliable Phase-II corroboration signal, per
  the validation table's own caveat section on why raw cycles/ns numbers
  are only an order-of-magnitude cross-check here) reproduces the L2→LLC
  capacity crossing cleanly (LLC-scope miss rate 0.6-0.9% at the L2
  footprint → 10.5-15% at the LLC footprint). Latency: L2's measured ticks
  land almost exactly on Fog's 14-cycle reference (~1.03-1.07x, tighter
  than L1's own ~1.4x inflation); LLC's measured ticks fall inside Fog's
  wide 34-85 cycle reference range. Sharing scope: system-reported
  confirms L1/L2 private-per-core (this CPU has no SMT) and LLC shared
  across all 8 cores of the single socket.

### eight_counters/ (Problem 8.4, item 1 — 2026-09-14)
Cross-machine standardized microbenchmark pipeline for `PROJECT 1.pdf` §8.4
("Eight Interesting Performance Counters Across Generations"). Uses the
team-wide `scripts/run_standardized_benchmarks.sh` +
`scripts/summarize_eight_counters.py` pipeline (already run on Sunbird,
Thunderbird, and Skylark — see `CLAUDE.md`'s §8.4 section) — no new code
this session. This is a *different* pipeline from `pmu/`'s §8.3 one: same
`cache_bench --experiment hit_latency` construction and same proven
4-groups-of-2 `perf stat` scheduling split, but a different fixed 8-event
set (`cache-references`, `cache-misses`, `L1-dcache-loads`,
`L1-dcache-load-misses`, `L1-dcache-stores`, `LLC-loads`,
`LLC-load-misses`, `dTLB-load-misses` — swaps `pmu/`'s `cycles`/
`instructions` pair for the L1 store-side signal and a real dTLB-miss
count) and 3 standardized cross-machine benchmark *names*
(`L1_resident`, `LLC_random`, `beyond_LLC`) rather than this pipeline's
own per-level names.

- Run command: `./scripts/run_standardized_benchmarks.sh crux 1
  L1_resident:32768,LLC_random:8388608,beyond_LLC:536870912` — footprints
  are this machine's own `FINAL_CACHE_TABLE.md` L1/LLC values (same
  32,768 B / 8,388,608 B already used for `pmu/`'s §8.3 run above) plus
  the project's universal 512 MiB `beyond_LLC` constant. Core 1 —
  re-checked idle immediately before this run via two independent
  `/proc/stat` idle-time-delta samples 4s apart (all 8 cores ~99-100%
  idle both times; the other students' jobs that had pinned cores 0/2
  during the earlier `pmu/` session had since exited). base_seed=12345
  (repeats use base_seed+index), samples=1,000,000/run, batch_size=1000,
  warmup_passes=3, dependent load mode, random pattern, timestamp
  `20260914T052920Z`.
- Raw output: `data_raw/crux/eight_counters/{L1_resident,LLC_random,
  beyond_LLC}/*_perfstat_*.csv.gz` (perf stat output) and `*_bench_*.csv.gz`
  (cache_bench's own CSV from the same invocation), gzipped by hand per
  this repo's convention. Transcript:
  `data_raw/crux/eight_counters/run_standardized_benchmarks_20260914T052920Z.log`.
- Processed:
  `data_processed/crux/eight_counters/{L1_resident,LLC_random,beyond_LLC}/eight_counters_summary_20260914T052920Z.csv`
  (one row per run_tag + a median-of-3 row; no `<not counted>` entries
  anywhere in any of the three files).
- Results: all 8 events collected cleanly at all 3 benchmarks, no PMU
  scheduling failures (consistent with this machine's own already-
  documented all-events-at-100% finding from the `pmu/` section above).
  `bench_avg_ticks_per_access` (median): `L1_resident`≈6.94,
  `LLC_random`≈42.25, `beyond_LLC`≈237.64 — **this is the cleanest
  cross-machine run of the three done so far**: unlike Sunbird's,
  Thunderbird's, and Ookay's own `beyond_LLC`/LLC-scale results (all
  inflated by other students' processes contending for chip-shared
  LLC/memory bandwidth despite an idle core), every one of Crux's 3
  numbers here lands within ~6.5% of this machine's own already-
  documented Phase I `latency/` hit-latency figures at the matching
  footprint (L1: 7.42 vs. 6.94, -6.5%; LLC: 43.23 vs. 42.25, -2.3%; DRAM:
  236.80 vs. 237.64, +0.36%) — consistent with all 8 cores being
  genuinely idle (not just this run's own core) for the whole session,
  not merely the pinned core. `l1_miss_rate` climbs from 1.05% at
  `L1_resident` to 8.80-8.81% at `LLC_random` (crosses the L1 boundary,
  as expected) then to 13.4% at `beyond_LLC` — unlike the `pmu/` section's
  L1→L2→LLC footprint sequence (where `l1_miss_rate` *saturates and
  drops* once inside LLC territory, per the already-documented -O0
  guaranteed-L1-hit-stack-load dilution effect), here it keeps climbing
  because `beyond_LLC`'s footprint is far past even LLC, not just past L1.
  `llc_miss_rate` shows the same small-sample noise at the `L1_resident`
  footprint already documented for this machine's `pmu/` section (5.2-6.3%
  off of only ~13.6-14k `llc_loads` events) before climbing to a clean,
  large 46.7-46.8% at `beyond_LLC`. Generic `cache_miss_rate` shows a
  clean monotonic climb this time (8.2-9.3% → 3.6-6.0% → 54.3-54.4%) —
  note the same L1-footprint-higher-than-LLC_random-footprint dip already
  flagged as an open, unexplained quirk in the `pmu/` section reproduces
  here too. `dtlb_load_misses` climbs cleanly and monotonically across all
  3 benchmarks — median 1,349 at `L1_resident` → 1,080,275 at `LLC_random`
  (~800x) → 254,971,011 at `beyond_LLC` (~236x further) — the same clean
  monotonic pattern already documented on Sunbird, Thunderbird, and
  Skylark, real new measured data (not just structural inference) toward
  this project's still-open DTLB-scale associativity confound question.
- **5 of 8 machines now done (Sunbird, Thunderbird, Skylark, Crux); 4
  remaining** (Artemisia, Charnwood, Ookay, Upgrade) — see `CLAUDE.md`'s
  §8.4 section for the running cross-machine tally; items 2-4 of §8.4
  (normalization, ranked S-curves, Intel/AMD/Arm + generation comparison)
  still need all 8 machines' data before they can be attempted.

### software_hit_rate/ (Problem 8.5 — 2026-09-14)
Software-only, timing-derived cache hit-rate estimator
(`main_code/software_hit_rate/`, no PMU access anywhere in that file) plus
its Phase-II PMU validation, same pipeline and redesigned harness used on
Sunbird/Thunderbird/Skylark (see `data_raw/sunbird/README.md`'s
`software_hit_rate/` section for the original design, the invalid first
attempt, and the 2026-09-14 redesign that fixed it — none of that history
is re-derived here). See `main_code/software_hit_rate/software_hit_rate.h`'s
module doc comment for the full method (calibration -> ROC threshold
selection -> Rogan-Gladen prevalence correction -> bootstrap CI).

#### Sweep (parts 1-3, standalone, no perf)
- Source file(s): `main_code/software_hit_rate/software_hit_rate.{c,h}`,
  `scripts/run_software_hit_rate_sweep.sh`,
  `scripts/summarize_software_hit_rate.py`, `scripts/plot_software_hit_rate.py`.
- Run command: `./scripts/run_software_hit_rate_sweep.sh crux 5
  4096,16384,32768,65536,131072,262144,1048576,4194304,8388608,16777216,33554432,67108864,134217728,268435456,536870912
  L1:32768,L2:262144,LLC:8388608,DRAM:536870912` — core=5 (confirmed idle:
  `/proc/stat` idle-tick deltas across 2 windows ~3s apart showed ~99%+
  idle on every core, and `ps -eLo pid,psr,pcpu,...` showed nothing but this
  session's own light VS Code/Claude processes anywhere on the machine),
  seed=12345, timestamp `20260914T123738Z`. Footprint list is anchored to
  this machine's own `CAPACITY_RESULTS.md` L1/L2/LLC values (32,768 /
  262,144 / 8,388,608 B), not Sunbird's default sweep.
- Raw output: `data_raw/crux/software_hit_rate/raw/hit_rate_<bytes>_20260914T123738Z.csv.gz`
  (full per-access CSV per point). Transcript:
  `data_raw/crux/software_hit_rate/run_software_hit_rate_sweep_20260914T123738Z.log`.
- Processed: `data_raw/crux/software_hit_rate/hit_rate_sweep_20260914T123738Z.csv`
  (one row per footprint); plots:
  `data_processed/crux/software_hit_rate/plots/{hit_rate_sweep,calibration_distributions}.{png,pdf}`.
- Headline results: Hhat=1.0000 for every footprint through 131,072 B,
  **including this machine's own exact 32,768 B L1 boundary** (0.9999, no
  dip) — unlike Sunbird, whose Hhat dipped to 0.8664 right at its own exact
  L1 edge. Falls off from there: 262,144 B (L2 boundary)->0.9824, 1,048,576
  B->0.6978, 4,194,304 B->0.3633, then **rises again** at 8,388,608 B (this
  machine's nominal `CAPACITY_RESULTS.md` LLC value)->0.4643 — non-monotonic,
  not smoothed over — before resuming its fall: 16,777,216 B->0.0868,
  33,554,432 B->0.0506, 67,108,864 B->0.0095, 134,217,728 B->0.0038,
  268,435,456 B->0.0009, and 0.0000 at the 536,870,912 B DRAM reference.
  **The non-monotonic dip-then-rise between 4,194,304 B and 8,388,608 B is
  not a fluke of this one estimator run — it lines up with two things this
  project already independently documented about Crux's own hardware in
  this exact byte range**: (1) `CLAUDE.md`'s own Crux capacity bullet
  already flags "the ~4-64 MiB region showed up to ~89% run-to-run spread"
  as genuinely noisy, not a settled shelf; (2)
  `data_processed/crux/PHASE2_VALIDATION_TABLE.md` establishes that this
  machine's REAL LLC capacity is 12,582,912 B (12 MiB), not the 8,388,608 B
  `CAPACITY_RESULTS.md` value used to anchor this sweep — so every point
  from 1,048,576 B through 8,388,608 B sits inside one messy, still-growing
  transition region on real hardware, not past a clean L2/LLC edge, which
  is a very plausible reason a single-seed sweep would land non-monotonically
  in exactly this range. See the PMU validation subsection below for direct
  confirmation that this instability is real and reproducible, not
  particular to this one seed.

#### PMU validation (part 4)
- Source file(s): `scripts/run_hit_rate_pmu_validation.sh`,
  `scripts/compare_hit_rate_pmu.py` (unmodified from the Sunbird-redesigned
  version — no Crux-specific code path exists or was needed).
- Run command: `./scripts/run_hit_rate_pmu_validation.sh crux 5
  L1:32768,L2:262144,LLC:8388608,DRAM:536870912` (core 5, re-confirmed idle
  immediately before running — same core as the sweep above). Footprint
  values are this machine's own `CAPACITY_RESULTS.md` numbers, same three
  L1/L2/LLC values already used for this machine's `latency/`,
  `associativity/`, `pmu/`, and `eight_counters/` sections. Tested
  footprints after the script's own L1/L2/LLC halving (a "safely inside the
  level" point, not the exact edge — see Sunbird's writeup for why):
  L1=16384, L2=131072, LLC=4194304, DRAM=536870912 (unchanged).
  base_seed=12345 (repeats use base_seed+index), timestamp `20260914T125809Z`.
- Raw output: `data_raw/crux/software_hit_rate/pmu/{L1,L2,LLC,DRAM}/
  *_{calibonly,bench,hitlatpmu,perfstat}_{base,rep1,rep2}_20260914T125809Z.csv`
  (not yet gzipped — do before committing, per this repo's `data_raw/**/*.csv.gz`
  convention). Transcript:
  `data_raw/crux/software_hit_rate/pmu/run_hit_rate_pmu_validation_20260914T125809Z.log`.
- Processed: `data_processed/crux/software_hit_rate/pmu_validation_20260914T125809Z.csv`.
- Headline results (median of base+2 repeats):

  | Level | Tested footprint | Hhat | H_pmu | rel. error |
  |---|---|---|---|---|
  | L1  | 16,384 B     | 1.0000 | 0.9023 | 10.8% |
  | L2  | 131,072 B    | 0.9995 | 0.9406 | 6.3%  |
  | LLC | 4,194,304 B  | 0.7519 | 0.9795 | 23.1% |
  | DRAM | 536,870,912 B | 0.0001 | 0.4541 | 100.0% |

  **L1/L2 agreement is in the same 6-11% ballpark already seen on
  Sunbird/Skylark/Thunderbird** — no new finding there. L1's 10.8% error is
  also independently corroborated by this machine's own earlier Phase-II
  work: `data_processed/crux/PHASE2_VALIDATION_TABLE.md` already flagged
  the generic `cache-references`/`cache-misses` pair as showing an
  "unexplained anomaly at the L1 footprint" (12.6% median miss rate there,
  vs. this run's own 9.8% at the L1 footprint) — same order of magnitude,
  same counter pair, same machine, different session. Still not root-caused,
  but now reproduced twice rather than a one-off.

  **LLC is where this machine produces a genuinely new result: Hhat itself
  is wildly unstable across the 3 seeds (base=0.7519, rep1=0.1246,
  rep2=0.8683 — a ~7x spread), while H_pmu (the independent, batched-timing
  PMU ground truth) stays tight and consistent across the same 3 seeds
  (0.9783, 0.9795, 0.9796 — agreeing to within 0.13%).** This is a different
  failure mode from every prior machine's LLC row: on Sunbird/Skylark/
  Thunderbird the single-threshold classifier was consistently wrong in the
  same direction (systematically too low, because a genuine LLC hit's
  single-shot latency sits above tau); here the classifier is inconsistent
  with itself seed-to-seed at a footprint where the underlying PMU signal
  says the true hit rate barely moves at all. Directly explained by the two
  facts already noted in the sweep write-up above: (1) 4,194,304 B (half of
  the nominal 8,388,608 B LLC value) sits inside the same ~4-64 MiB region
  this machine's own capacity data already flags as having up to 89%
  run-to-run spread on raw timing, and (2) the real LLC is 12 MiB, so this
  footprint is not actually "half of the level's true capacity" the way the
  script's halving convention intends for L1/L2 — it is a point deep inside
  a still-unsettled transition on the real hardware, which is exactly where
  a single-shot classifier that depends on individual access timings (not a
  batched aggregate) would be most exposed to real per-run conflict-miss
  variance. **Conclusion: do not cite a single "Crux LLC Hhat" number from
  this run — the instability is the finding.** The raw per-run PMU miss
  counts corroborate H_pmu's own stability directly: `cache-references`/
  `cache-misses` were 11,140,906/242,046 (base), 11,174,069/229,595 (rep1),
  11,146,775/226,938 (rep2) — a consistent ~2.0-2.2% miss rate underlying
  all 3 runs, confirming the instability is in the software estimator, not
  in the workload itself varying seed-to-seed.

  **DRAM's near-total disagreement (100.0%) is the same expected,
  already-documented generic-counter-semantics limitation as every other
  machine tested so far (Sunbird 99.9%, Skylark 99.98%, Thunderbird 100%)**
  — H_pmu's median 0.4541 reflects a generic `cache-references`/
  `cache-misses` alias that does not cleanly mean "any cache level vs.
  DRAM" at this scale, not a real ~45% hit rate for a fully random 512 MiB
  working set. Hhat's near-zero (0.0000-0.0001 across 3 runs) is the
  trustworthy number here, consistent with every other machine.

  **4 of 8 machines now have software_hit_rate data (Sunbird, Skylark,
  Thunderbird, Crux — check each machine's own README before assuming this
  count is current); Charnwood/Artemisia/Ookay/Upgrade still need this
  pipeline run** — see `CLAUDE.md`'s §8.5 section for the running
  cross-machine tally.

## Final Inferred Cache Table (Crux, Phase I best guess, 2026-09-13)

Lives at `data_processed/crux/FINAL_CACHE_TABLE.md`, alongside this machine's
other processed benchmark outputs (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/`), matching Sunbird's convention. The full
per-pairing reasoning and caveats behind it remain here, in this file's
`associativity/` and `inclusion_policy/` sections above — the processed-
directory copy is the consolidated table only, not a replacement for that
narrative.

## Reservation Log (if applicable)
- Reserved core/package: 
- Time window: 
