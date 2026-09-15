# hazel_icelake_8358 — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `c059n02` (allocated by Slurm for `--constraint=icelake_8358`, job 833555)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `Intel(R) Xeon(R) Platinum 8358 CPU @ 2.60GHz` -- matches NC State's documented
  `icelake_8358` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): Intel Ice Lake-SP (3rd Gen Xeon Scalable)
- Introduction year (per the team's stated year convention): 2021
- Process node (if reliably documented): 10 nm (Intel 10nm SuperFin)
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 56 (socket 1, NUMA
  node 1) via `--cpu-bind=cores`. Sibling-thread idleness not independently checked this
  pass (no full-suite timing run yet to require it).

## Environment
- Compiler + version: `gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-11)` (confirmed via the
  job's own `gcc --version` on the allocated compute node, not just the login node)
- Compiler flags: `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
- Timer method used (RDTSC/RDTSCP+LFENCE, CNTVCT_EL0, etc.): RDTSC-family (x86-64), same
  `main_code/x86_64/timer_x86.h` used on every x86 lab machine -- not yet independently
  sanity-checked on this specific node (pending the full-suite pass).
- Affinity/binding command used: `srun --cpu-bind=cores` (NOT `taskset` -- that is the lab
  machines' pinning method only; see `scripts/run_capacity_sweep.sh`'s header comment).
  Resulting binding: `physcpubind: 56`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 56 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833555, elapsed 22s, exit code 0. Full stdout/stderr: `hw1_icelake_8358_833555.log` /
`hw1_icelake_8358_833555.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833555/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_icelake_8358.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_icelake_8358_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837633, logical CPU 63, elapsed 1h14m01s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837633/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_icelake_8358 63`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation)
- Raw output filename(s):
  `data_raw/hazel_icelake_8358/capacity/capacity_{coarse,coarse_ext,dense0..dense5,
  dense5_rep1,dense5_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full
  transcript: `data_raw/hazel_icelake_8358/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_icelake_8358/capacity/*_summary.csv`;
  `scripts/detect_cache_hierarchy.py` (default thresholds) -> 6 candidate boundaries (see
  Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_icelake_8358/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run; see the Findings' noise
  note below (flagged, not excluded/re-run -- this machine likely needs a full re-run when
  quiet, same as Charnwood's own precedent in this project).

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline).
CPU: Intel Xeon Platinum 8358 (Ice Lake-SP). This is the NOISIEST capacity run of any Hazel
generation so far -- unresolved, not just noisy, above ~2.9 MiB. Read this whole section
before citing any number from this machine; only L1 gets even a best-guess-quality read.**
- **Everything past ~2.9 MiB is wildly, sustainedly noisy -- not a single anomaly like
  icelake_6326/sapphirerapids, but continuous chaos across the entire remaining sweep.**
  Consecutive coarse-sweep points swing wildly with no discernible monotonic trend:
  2,965,816 B: 114.91 -> 3,234,248 B: 60.94 (halved) -> 3,526,968 B: 78.08 -> 4,194,304 B:
  67.07 -> 5,931,640 B: 114.67 -> 6,468,496 B: 133.39 -> 7,053,944 B: 72.71 (roughly halved
  again) -- and this pattern of large, directionless swings (typically 30-100%+ between
  adjacent points) continues essentially unbroken all the way through the coarse sweep's own
  ceiling (67,108,864 B) and into the tail extension. This is consistent with heavy, sustained
  multi-tenant contention for most of this run's duration, not a real cache-hierarchy signal
  -- the same "unresolved, not just noisy" category as Charnwood's own capacity finding in
  this project's lab-machine work (see `CLAUDE.md`), just more severe and covering nearly this
  entire run rather than one contaminated region. **This machine likely needs a full capacity
  re-run when quiet** -- not attempted this pass.
- **L1D: best-guess only, not independently confirmed.** The small-footprint region
  (1,216-50,528 B) is itself noisy (oscillating 8.27-9.66 ticks with no clean flat plateau),
  though real climbing doesn't clearly emerge until 55,104-65,536 B. **Best-guess: 32,768 B**
  (matching the frozen prediction and every other x86 machine), consistent with but not
  cleanly confirmed by this run's own noisy small-size data.
- **L2 and LLC: NOT resolved -- the sustained noise above precludes identifying either edge
  from this run's own data.** The auto-detector's 6 candidates (1,246,968 / 3,234,248 /
  5,439,336 / 16,777,216 / 33,554,432 / 51,748,008 B) are scattered across the entire noisy
  region and not read as evidence of any real boundary. **L2 best-guess: 1,310,720 B
  (1.25 MiB)** -- Ice Lake-SP's known standard per-core L2 (same reasoning as icelake_6326's
  own unresolved L2). **LLC best-guess: 50,331,648 B (48 MiB)** -- this SKU's publicly
  documented total L3 cache size (Xeon Platinum 8358: 48 MB), used here purely as a
  placeholder reasoned value since the timing data itself gives no usable signal, unlike
  icelake_6326's own LLC (which WAS independently confirmed by a clean knee).
- **LLC-to-DRAM: roughly consistent with the same ~230-260 tick plateau every other Intel
  Hazel generation reaches, but the noise here precludes calling it cleanly confirmed.** Tail
  extension values (231.54-276.06 across 103-268 MiB) sit in the same range as
  cascadelake's/icelake_6326's own confirmed DRAM plateaus, with no clear net climb across
  the range -- plausibly a real plateau, just too noisy to confirm the way those two machines
  could.
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way) is consistent with this run's best-guess L1D, but -- per the noise
  discussion above -- this machine's own data cannot independently confirm it.
- Raw output filename(s): 
- Processing script -> data_processed path: 
- Excluded runs (if any) and reason: 

### line_size/
- Slurm job ID: 838211, exit 0.
- Source file(s): `main_code/common/line_size.{c,h}`, `scripts/run_line_size.sh`
  (`HAZEL_MODE=1`), `scripts/detect_line_size.py`, `scripts/plot_line_size*.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_icelake_8358 34
  32768,1310720,50331648` (default coarse strides; no `candidate_overrides_csv`, Method A
  step 4 skipped at every level)
- Sample count: 1,000,000 (timed; warm-up excluded), seed=12345
- **Inconclusive -- Method B found no transition at any of the 3 levels.** Consistent with
  this machine's already-documented pervasive capacity-sweep noise. **Best-guess: 64 B**
  (universal x86 default, unconfirmed here).

### associativity/
- Slurm job ID: 838212, logical CPU 34, elapsed 35s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh
  hazel_icelake_8358 34 32768,1310720,50331648` (best-guess/unresolved capacity boundaries,
  see capacity/ section's noise caveat above; base_seed=12345, repeats at seed+1/seed+2,
  max_ways=40, 1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate (standard method).
- **Notes / results: L1=9 (fully reproducible), L2=12 (fully reproducible), L3_LLC=10 base,
  10/9 on repeats (flagged disagreement).** Consistent with this machine's own already-noisy
  capacity data, **L1's own "9" fails the arithmetic-consistency check** (32,768 B / 64 /
  9 = 56.89 sets, not a whole number) -- not a genuine L1 associativity, same symptom as
  icelake_6326's own machine. L2's "12" (sets=1706.67) and both LLC candidates (10:
  sets=78,643.2; 9: sets=87,381.33) are likewise arithmetically invalid. **No level on this
  machine produces a physically self-consistent associativity number** -- the whole run is
  read as confound/noise throughout, consistent with this machine's already-documented
  pervasive capacity-sweep noise (see the capacity/ section's own "likely needs a full
  re-run when quiet" note).

### latency/
**hit_latency (Slurm job 838213, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_hit_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_hit_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_hit_latency_full.sh
  hazel_icelake_8358 34 L1:32768,L2:1310720,LLC:50331648,DRAM:536870912` (base_seed=12345,
  2 repeats, 1,000,000 samples/point, batch_size=1000)
- Dependent-chain batch size N used: 1,000
- Regular vs. randomized control included? Yes -- no `[UNEXPECTED]` flags, independent read
  faster than dependent everywhere -- but see the result note below before trusting this as
  a sign of a clean run.
- **Results (dependent, random, base-run median, ticks/access): L1=27.22, L2=30.98,
  LLC=231.65, DRAM=256.88.** **L1 and L2 are unusually close together (only ~14% apart) --
  every other Hazel/lab machine shows a 2-4x gap between these two levels.** This is further,
  independent evidence (beyond the capacity/associativity sections' own findings) that this
  machine's whole session was affected by pervasive noise/contention, not a genuine L1≈L2
  hardware property -- consistent with this machine's own "likely needs a full re-run when
  quiet" flag. LLC/DRAM are also closer together (~11%) than most other machines. Do not cite
  any of these four numbers as clean, independent per-level latencies.

**miss_latency (Slurm job 838214, elapsed 1h21m02s, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_miss_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_miss_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_miss_latency_full.sh
  hazel_icelake_8358 34 L1_to_L2:32768:1310720,L2_to_LLC:1310720:50331648,
  LLC_to_DRAM:50331648:536870912`
- **Results (base run, random pattern, median ticks/access): L1_to_L2=90.0, L2_to_LLC=558.0,
  LLC_to_DRAM=716.0** -- monotonically increasing despite this machine's own pervasive noise.
  Substantial repeat spread throughout (48.8-79.1%), consistent with the capacity/
  associativity/hit_latency sections' own documented noise on this machine -- not re-run.

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
