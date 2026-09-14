# hazel_haswell — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c207n02` (allocated by Slurm for `--constraint=haswell`, job 833461)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) CPU E5-2650 v3 @ 2.30GHz` --
  matches NC State's documented `haswell` constraint mapping (Intel Xeon E5 v3), and is the
  same family as Sunbird's own lab machine (Xeon E5-2680 v3), a different SKU in the same
  v3 generation.
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Haswell-EP
  (server), per the public Xeon E5-2650 v3 product naming -- not read from any cache-topology
  command.
- Introduction year (per the team's stated year convention): 2014 (Haswell-EP launch, same
  generation year the team already uses for Sunbird's own Xeon E5-2680 v3)
- Process node (if reliably documented): 22 nm (Haswell family, same as Sunbird's row in
  `CHRONOLOGICAL_MASTER_TABLE.md` -- not independently verified on this specific SKU this pass)
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64` (`uname -a`)
- Page size: 4096 bytes (standard x86-64; also the alignment `main_code/common/main.c`'s
  `ASSOC_CACHE_BYTES_ALIGN` already assumes)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 10 (`physcpubind: 10`, socket 1, NUMA
  node 1) via `--cpu-bind=cores`. Sibling-thread idleness not independently checked this pass
  (no full-suite timing run yet to require it) -- see the pending Environment note below.

## Environment
- Compiler + version: `gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-11)` (system gcc on the
  allocated compute node, confirmed via the job's own `gcc --version` -- not just the login
  node's)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): RDTSC-family (x86-64), same
  `main_code/x86_64/timer_x86.h` used on every x86 lab machine -- not yet independently
  sanity-checked on this specific node (pending the full-suite pass).
- Affinity/binding command used: `srun --cpu-bind=cores` (NOT `taskset` -- that is the lab
  machines' pinning method only; see `scripts/run_capacity_sweep.sh`'s header comment).
  Resulting binding per the job's own `numactl -s` output: `physcpubind: 10`, `cpubind: 1`,
  `nodebind: 1`, `membind: 0 1`.
- NUMA/locality method: `numactl -s` (available on the compute node) plus
  `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase Discipline whitelist) -- logical CPU 10 is
  physical core 10, socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `b4bf2a3851988965442b06cedf6d272da94b7248`
  (the `predictions-frozen` tag itself -- this job's own gate check confirmed HEAD was tagged
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833461, submitted 2026-09-14T14:25:38 UTC, started 14:25:53, completed 14:25:56 (elapsed 3s,
exit code 0). Full stdout/stderr: `hw1_haswell_833461.log` / `hw1_haswell_833461.err.log` (committed
alongside this README; renamed from Slurm's default `%x_%j.out`/`.err` naming because this
repo's `.gitignore` blanket-ignores `*.out` -- `hpc_slurm/hw1_haswell.sh`'s `#SBATCH --output`/
`--error` directives now write directly into `data_raw/hazel_haswell/` with a `.log` suffix). The job built `cache_bench` cleanly and ran one tiny (`--samples 1000`,
4096-65536 B) `--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the
binary runs correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite
required for the actual capacity/line_size/associativity/latency/inclusion_policy experiments,
which have not run on this machine yet (see `hpc_slurm/hw1_haswell.sh`'s own header for the
Phase-Discipline gate that will permit that next).

## Per-Experiment Reproduction

### capacity/
**Note on node identity:** Hazel is dynamic (per assignment instructions) -- this run landed
on a DIFFERENT physical node (`c207n01`) than the earlier access-check pilot (`c207n02`),
though both report the identical CPU model (`Intel(R) Xeon(R) CPU E5-2650 v3 @ 2.30GHz`) and
socket/NUMA layout (see the pilot's job log for a full `lscpu -e` dump; not repeated here for
brevity, but confirmed matching for `c207n01` in this run's own log,
`hw1_haswell_capacity_833680.log`).

- Slurm job ID: 833680, hostname `c207n01`, logical CPU 10 (`physcpubind: 10` via `numactl -s`),
  socket 1, NUMA node 1 (`lscpu -e=CPU,CORE,SOCKET,NODE`). Submitted/started 2026-09-14
  ~18:44 UTC, completed 20:03 UTC, elapsed 1h19m29s, exit code 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/833680/`, cleaned up on
  job exit -- see `hpc_slurm/hw1_haswell_capacity.sh` / `HAZEL_MODE=1` in
  `run_capacity_full.sh`)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_haswell 10`
  (coarse_max defaulted to 67,108,864 B / 64 MiB; internally invokes
  `srun --cpu-bind=cores "$BENCH" --experiment capacity --pattern {random,sequential}
  --samples 1000000 --batch-size 1000 --min-bytes ... --max-bytes ... --points-per-octave
  {8 coarse, 48 dense} --warmup-passes 3 --seed 12345` per stage)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the SAME
  seed as the base run (unlike associativity's per-repeat-varied-seed convention -- this
  script was not updated to vary seeds per repeat; noting as a known limitation carried over
  unchanged from the lab-machine version of this script, not something introduced for Hazel)
- Raw output filename(s): `data_raw/hazel_haswell/capacity/capacity_{coarse,coarse_ext,
  dense0..dense3,dense3_rep1,dense3_rep2,denseTail}_{random,sequential}_20260914T184407Z.csv.gz`
  (gzipped by the pipeline itself); full run transcript:
  `data_raw/hazel_haswell/capacity/run_capacity_full_20260914T184407Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_haswell/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (auto boundary detection, default thresholds) ->
  4 candidate boundaries (see Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_haswell/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run, no repeats discarded.
  A handful of individual (footprint, pattern) points show wide overlapping-summary spread
  (e.g. 19.3 MiB random: medians [43.6, 46.1, 87.3, 43.5], 79% spread) where dense-sweep
  windows from adjacent boundaries overlap on a shared log-spaced grid point -- `plot_capacity.py`
  auto-averages these and widens the box/whisker to the union rather than silently picking one
  (same behavior already documented for the lab machines); not excluded, just flagged.

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline):**
- **L1D: well-confirmed at 32,768 B (32 KiB).** The coarse-sweep median is flat at ~8.3
  ticks/access from the smallest tested size (1,024 B) through exactly 32,768 B (median 8.47,
  still within noise of the plateau), then visibly departs starting at the very next point,
  35,728 B (median 8.93, climbing steadily from there) -- a genuine, timing-derived edge at
  the expected power-of-two boundary, not borrowed from any published spec. The auto-detector
  (`detect_cache_hierarchy.py`, default thresholds) did NOT flag this edge on its own --
  the transition is a smooth ramp rather than an abrupt step, the same class of miss already
  documented for Thunderbird/other lab machines with soft transitions -- this L1 read comes
  from manually inspecting `coarse_random_summary.csv`, not the pipeline's own boundary list.
- **L2: NOT cleanly resolved this pass.** Past the L1 edge, latency climbs smoothly and
  continuously from ~9 ticks (35 KiB) up through ~42-46 ticks by roughly 500 KiB-1 MiB, then
  stays in that same noisy ~40-46 tick band all the way out to ~20 MiB -- there is no second,
  visually distinct knee separating an L2 shelf from an LLC shelf within that whole range at
  this sweep's resolution. The auto-detector's first flagged boundary, 285,864 B (~279 KiB),
  sits partway up the ramp (median ~28.9, i.e. still climbing, not yet at the ~43-46 tick
  plateau) -- it is NOT read as a genuine L2 capacity edge, just a threshold trigger partway
  through the ramp (the boxplot's own "279.164 KiB (near)" column shows ~19 ticks with 4% repeat
  spread, well below the eventual plateau, corroborating this read). No L2 candidate byte value
  is reported from this run; a dedicated dense sweep bracketing a narrower 128 KiB-2 MiB window
  would be needed to look for a real L2 knee, mirroring the follow-up several lab machines
  needed for their own unresolved L2/LLC regions.
- **LLC-to-DRAM transition: begins between ~21.8 MiB and ~23.7 MiB, does not fully plateau
  within the tested range (up to 268,435,456 B / 256 MiB).** Coarse-sweep medians:
  21,757,352 B -> 44.8 ticks (still near the plateau), 23,726,560 B -> 48.1 (clearly departing),
  25,874,000 B -> 62.5, 28,215,800 B -> 71.2, climbing steadily and continuously through
  67,108,864 B -> 156.7, and per `capacity_curve.png` continuing to climb (not flattening) all
  the way to ~200 ticks by 256 MiB+. The auto-detector's three boundaries in this region
  (23,726,560 / 28,215,800 / 39,903,168 B) are read as fragments of ONE continuous, accelerating
  climb, not three distinct cache levels -- the same "one continuous transition triggering
  multiple spurious boundary detections" pattern already documented on Crux/Ookay/Sunbird in
  this project (see `CLAUDE.md`'s capacity section). Best-guess LLC capacity edge: ~22-24 MiB
  (where the climb first clearly departs the ~40-46 tick plateau) -- provisional, not a clean
  knee. **The tail-extension + repeats + denseTail-past-deepest stages (up to 256 MiB) never
  found a DRAM plateau** -- unlike most of the 8 lab machines, which all eventually flattened
  somewhere in the 256 MiB-2 GiB range after a manual follow-up extension; this run's pipeline
  extension (4x coarse_max, RAM-safety-clamped) topped out at 268,435,456 B still climbing. A
  further manual extension past 256 MiB (mirroring every lab machine's own capacity/ follow-up)
  would be needed to find the true DRAM floor, not attempted this pass.
- **Held-out comparison against the frozen prediction** (see `PREDICTION_FREEZE.md`): the
  frozen L1D prediction (32,768 B / 8-way, Chen-Ngo Invariance Law) matches this run's
  timing-derived L1D capacity exactly. LLC capacity's frozen prediction (~30 MiB, Sunbird
  same-era analog) is in the same order of magnitude as this run's ~22-24 MiB best-guess edge,
  though not an exact match -- plausibly explained by this being a different, smaller-core-count
  SKU (E5-2650 v3, 10 cores) than Sunbird's own E5-2680 v3 (12 cores), a real, timing-observable
  difference within the same documented generation, consistent with the project's own repeated
  finding elsewhere that LLC capacity varies by specific SKU even within one generation. Full
  held-out evaluation table entry deferred to `PREDICTION_FREEZE.md` once associativity, line
  size, and latency data exist too.

### line_size/
- Source file(s): 
- Build command: 
- Run command + arguments: 
- Sample count: 
- Notes on alignment/candidate strides tested: 

### associativity/
- Slurm job ID: 834509, hostname `c207n02`, logical CPU 10, elapsed 33s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh hazel_haswell 10
  32768,262144,25165824` (explicit `cache_bytes_csv`, no `ASSOC_ALLOW_AUTO`; base_seed=12345,
  repeats at seed+1/seed+2, max_ways=40, 1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate (32,768 / 262,144 / 25,165,824 B), forcing every probed node into the same cache
  set (see `associativity.h`'s docstring) -- standard method used on every lab machine.
- Notes / results:
  - **L1 = 8-way, fully reproducible (base + both repeats agree exactly)** -- flat ~7.7-19.2
    ticks through num_ways=8, sharp knee at 9 (see
    `data_processed/hazel_haswell/associativity/L1/plots/associativity_curve.png`). Matches
    the frozen prediction exactly, and matches every x86 lab machine's own confirmed L1=8-way.
  - **L2 = UNRESOLVED, flagged by the pipeline itself**: base run detected 3, both repeats
    detected 4 (`WARNING: repeat(s) disagree with the base estimate`). Given L2's own capacity
    (262,144 B) was itself a reasoned guess rather than a confirmed boundary this pass, this
    disagreement is not surprising -- do not cite an L2 associativity number for this machine.
  - **L3_LLC = 9, fully reproducible (base + both repeats agree exactly)** -- this is the SAME
    "~9-10-way wall" confound signature already documented extensively across Sunbird/Upgrade/
    Thunderbird/Charnwood/etc. in `CLAUDE.md` (a shared small-fixed-structure artifact, most
    likely DTLB-scale, not real LLC associativity) -- do not cite 9-way as this machine's real
    LLC associativity either. A useful cross-validation point regardless: the exact same
    confound reproduces on Hazel hardware, not just the team's own lab machines.

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
