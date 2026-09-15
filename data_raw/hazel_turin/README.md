# hazel_turin — Reproduction Manifest

> Fill in every field before freezing results. This README must let a grader go from
> this folder to the exact command that generated the data without guessing.

## Machine Identification
- Hostname: `n0405` (allocated by Slurm for `--constraint=turin`, job 833558)
- CPU model (from `lscpu`/`/proc/cpuinfo`): `AMD EPYC 9655 96-Core Processor` -- matches NC State's documented
  `turin` constraint mapping (see PREDICTION_FREEZE.md/assignment Table 4).
- ISA / architecture: x86-64 (`uname -a`: `x86_64 x86_64 x86_64 GNU/Linux`)
- Vendor / microarchitecture / codename (researched, NOT from cache tables): AMD Zen 5 (EPYC 9005 'Turin')
- Introduction year (per the team's stated year convention): 2024
- Process node (if reliably documented): TSMC 3/4 nm (chiplet-dependent)
- Kernel version: `5.14.0-611.5.1.el9_7.x86_64`
- Page size: 4096 bytes (standard x86-64)
- SMT siblings idle during runs? This access-check job requested 1 CPU
  (`--cpus-per-task=1`); Slurm bound it to logical CPU 128 (socket 1, NUMA
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
  Resulting binding: `physcpubind: 128`, socket 1, NUMA node 1
  (via `numactl -s`).
- NUMA/locality method: `numactl -s` plus `lscpu -e=CPU,CORE,SOCKET,NODE` (both on the Phase
  Discipline whitelist) -- logical CPU 128 is socket 1, NUMA node 1 on this node.
- Git commit hash of the code used for these results: `cb7e0c8c82c0269507e665db04563dee78fda9a6` (the `predictions-frozen`
  tag's own commit is an ancestor of this HEAD -- confirmed by this job's own gate check
  before running anything past the smoke test)

**Job record (this pass -- access/build check only, not the full suite):** Slurm job ID
833558, elapsed 2s, exit code 0. Full stdout/stderr: `hw1_turin_833558.log` /
`hw1_turin_833558.err.log` (committed alongside this README; `.log` suffix used instead of
Slurm's default `.out` because this repo's `.gitignore` blanket-ignores `*.out`). The job built
`cache_bench` cleanly (in an isolated per-job directory, `hazel_build/833558/`, to avoid
races with sibling generations' jobs building concurrently in this same shared GPFS checkout --
see `hpc_slurm/hw1_turin.sh`'s header) and ran one tiny (`--samples 1000`, 4096-65536 B)
`--experiment capacity` smoke test under `srun --cpu-bind=cores` to confirm the binary runs
correctly bound to a real core on Hazel -- this is NOT the 1,000,000-sample suite required for
the actual capacity/line_size/associativity/latency/inclusion_policy experiments, which are run
by a separate `hw1_turin_<experiment>.sh` job script per experiment type (see
`hpc_slurm/README.md`).

## Per-Experiment Reproduction

### capacity/
- Slurm job ID: 837636, hostname `n0405` (confirmed the correct Turin node, not one of the
  `gpu35-39` nodes that also carry the `turin` feature flag -- see `CLAUDE.md`'s Hazel status
  note), logical CPU 160, elapsed 1h33m39s, exit 0.
- Source file(s): `main_code/common/{main.c,benchmark.c,pointer_chase.c,random.c,capacity.c}`,
  `scripts/run_capacity_full.sh` (`HAZEL_MODE=1`), `scripts/summarize_raw.py`,
  `scripts/detect_cache_hierarchy.py`, `scripts/plot_capacity.py`
- Build command: `make -s` (isolated per-job copy under `hazel_build/837636/`, cleaned up on
  job exit)
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_capacity_full.sh hazel_turin 160`
  (coarse_max defaulted to 67,108,864 B / 64 MiB, then a 4x tail extension to 256 MiB)
- Sample count: 1,000,000 (timed; warm-up excluded) -- every stage
- Random seed(s): base 12345; reproducibility repeats on the deepest boundary use the same
  seed (this script's own known limitation)
- Raw output filename(s):
  `data_raw/hazel_turin/capacity/capacity_{coarse,coarse_ext,dense0..dense3,dense3_rep1,
  dense3_rep2,denseTail}_{random,sequential}_20260915T010343Z.csv.gz`; full transcript:
  `data_raw/hazel_turin/capacity/run_capacity_full_20260915T010343Z.log`
- Processing script -> data_processed path: `scripts/summarize_raw.py` ->
  `data_processed/hazel_turin/capacity/*_summary.csv`; `scripts/detect_cache_hierarchy.py`
  (default thresholds) -> 4 candidate boundaries (see Findings); `scripts/plot_capacity.py` ->
  `data_processed/hazel_turin/capacity/plots/capacity_{curve,boxplots}.{png,pdf}`
- Excluded runs (if any) and reason: none -- single complete run.

**Findings (timing-only; no vendor/cache-topology lookup used, per Phase I discipline).
CPU: AMD EPYC 9655 (Turin, Zen 5) -- a second AMD generation, one Zen family newer than
hazel_genoa's own Zen 4.**
- **L1D: flat baseline extends notably past 32,768 B, similar in shape to
  hazel_sapphirerapids' own L1D deviation -- best-guess 49,152 B (48 KiB), not the usual
  32,768 B.** The ~3.22-3.30 tick baseline (extremely fast/low-overhead relative to every
  other machine, consistent with a newer, higher-clocked core) persists cleanly through
  46,336 B -- well past every other x86/Zen4 machine's own confirmed 32,768 B edge, where
  this same baseline would already be climbing. A real, unambiguous climb only begins at
  50,528 B (3.61, +11%) and is clearly established by 55,104 B (4.34, +34%). Not independently
  verified against a public Zen 5 architecture spec this pass (unlike this project's usual
  practice of citing a known generation-typical value for provisional picks) -- flagged
  purely as a timing-observed deviation, the same *direction* and *shape* of finding as
  sapphirerapids' own L1D result, worth a dedicated line_size/associativity follow-up to
  pin down further.
- **L2: NOT resolved -- one continuous climb from the L1 edge through ~1.9 MiB, no distinct
  shelf.** Climbs steadily from 50,528 B (3.61) through 1,923,096 B (29.69). **L2 best-guess:
  1,048,576 B (1 MiB)** -- same generation-typical value used for hazel_genoa's own
  unresolved L2 (Zen 4/Zen 5 EPYC server parts are both publicly documented at 1 MiB private
  per-core L2, no known change between these two generations).
- **LLC: a real shelf (2-24 MiB), then a noisy transition zone, then a real sustained
  climb.** The curve settles into a relatively flat shelf from ~2 MiB through 23,726,560 B
  (26.57-39.34 ticks, some drift but no sharp jumps). The immediate region above that
  (25,874,000-36,591,368 B) is genuinely noisy -- alternating spikes and dips rather than a
  clean single knee (25,874,000 B: 54.25, 28,215,800 B: 39.18 -- back down to shelf level --
  30,769,544 B: 63.60, 33,554,432 B: 39.65 -- down again -- 36,591,368 B: 73.00) -- consistent
  with genuine transition-boundary measurement noise (a pattern already documented elsewhere
  in this project right at real edges) rather than sustained external contention (which
  usually shows as a one-directional shift over several consecutive points, not this
  alternating pattern). A real, sustained, unambiguous climb is clearly established from
  39,903,168 B onward (98.55, then 123.01, 144.35, 166.93 -- no more reversals). **LLC
  best-guess: 33,554,432 B (32 MiB)** -- one of the auto-detector's own 4 candidates, and an
  exact match to hazel_genoa's own confirmed LLC edge (both are 96-core, 8-cores-per-CCD EPYC
  parts with the same publicly documented 32 MB per-CCD L3) -- read with somewhat lower
  confidence than genoa's own cleaner result, given the surrounding noise, but the same
  value, same reasoning, same CCD architecture.
- **LLC-to-DRAM: cleanly confirmed plateau within the default tail extension -- the
  cleanest DRAM floor of any Hazel generation so far.** 87,029,424 B: 335.43 through
  268,435,440 B: 352.30 -- only ~5% drift across the entire 3x tail range, tighter than
  every other machine's own tail-extension result this session (haswell/skylake/
  sapphirerapids/genoa all failed to plateau at all within 256 MiB; icelake_6326/cascadelake
  plateaued with more like 15% drift).
- **Held-out comparison against the frozen prediction:** the frozen L1D prediction
  (32,768 B / 8-way) does NOT match this run -- see the L1D finding above, the second Hazel
  generation (after sapphirerapids) where the timing data itself points to a larger L1D.

### line_size/
- Slurm job ID: 838244, exit 0.
- Source file(s): `main_code/common/line_size.{c,h}`, `scripts/run_line_size.sh`
  (`HAZEL_MODE=1`), `scripts/detect_line_size.py`, `scripts/plot_line_size*.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_line_size.sh hazel_turin 144
  49152,1048576,33554432` (default coarse strides; no `candidate_overrides_csv`, Method A
  step 4 skipped at every level)
- Sample count: 1,000,000 (timed; warm-up excluded), seed=12345
- **Only LLC produced a citable estimate: 64 B.** L1 (49,152 B) and L2 (1,048,576 B) both
  found no transition -- consistent with the same "no signal near the best-guess L1 edge"
  pattern already seen on sapphirerapids' own line_size run. Same misleading-but-technically-
  true "every level/method that produced an estimate AGREES on 64B" pipeline message as
  hazel_haswell/hazel_icelake_6326's own runs (only one level actually produced a value).
  **Best-guess: 64 B** -- matches genoa's own Zen 4 result exactly (Zen 5 didn't change line
  size either), and this is the only real data point on this machine.

### associativity/
- Slurm job ID: 838245, logical CPU 144, elapsed 16s, exit 0.
- Source file(s): `main_code/common/associativity.{c,h}`,
  `scripts/run_associativity_full.sh` (`HAZEL_MODE=1`), `scripts/detect_associativity.py`,
  `scripts/plot_associativity.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_associativity_full.sh hazel_turin 144
  49152,1048576,33554432` (base_seed=12345, repeats at seed+1/seed+2, max_ways=40,
  1,000,000 samples/point)
- Conflict-set construction method: node-to-node stride fixed at each level's own capacity
  candidate (standard method).
- **Notes / results: L1=13, L2=13, L3_LLC=13 base, 12/13 on repeats (flagged disagreement)
  -- the clearest single-machine confound signature of any Hazel generation so far.** All
  three levels report the SAME digit (13) despite spanning a 683x byte-capacity range
  (49,152 B to 33,554,432 B), and **that digit fails the arithmetic-consistency check at
  every level**: L1 (768 lines/13 = 59.08 sets), L2 (16,384 lines/13 = 1,260.31 sets), and
  LLC (524,288 lines/13 = 40,329.85 sets) are all non-integer -- not one of these three
  levels can physically have 13-way associativity at its own tested capacity. Unlike
  sapphirerapids' own L1 result (which reported a distinct value from L2/LLC AND passed the
  arithmetic check, both signs of a genuine measurement), this machine's L1 result gives
  neither -- despite this being the SAME capacity/ section that flagged L1D as likely
  49,152 B (48 KiB, not 32,768 B) from independent timing evidence. Read as: the 48 KiB L1D
  best-guess itself is not undermined by this (it came from the capacity curve's own shape,
  not this experiment), but this machine's associativity run cannot independently confirm
  ANY level's real associativity -- the cross-machine DTLB-scale confound documented in
  `CLAUDE.md` is the more likely explanation throughout.

### latency/
**hit_latency (Slurm job 838246, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_hit_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_hit_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_hit_latency_full.sh hazel_turin 144
  L1:49152,L2:1048576,LLC:33554432,DRAM:536870912` (base_seed=12345, 2 repeats, 1,000,000
  samples/point, batch_size=1000)
- Dependent-chain batch size N used: 1,000
- Regular vs. randomized control included? Yes -- no `[UNEXPECTED]` flags, independent read
  faster than dependent everywhere.
- **Results (dependent, random, base-run median, ticks/access): L1=3.33, L2=18.46,
  LLC=41.95, DRAM=347.59** -- a clean, monotonic 4-tier ladder. The DRAM/L1 ratio (~104x) is
  the largest of any Hazel machine so far, consistent with this being the fastest/lowest-
  latency core measured this session (L1≈3.3 ticks) -- the same "faster core sees more ticks
  for the same physical DRAM latency" effect already noted for genoa, just more pronounced
  given Zen 5's even lower baseline.

**miss_latency (Slurm job 838247, elapsed 1h38m43s, exit 0):**
- Source file(s): `main_code/common/latency.{c,h}`, `scripts/run_miss_latency_full.sh`
  (`HAZEL_MODE=1`), `scripts/plot_miss_latency.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_miss_latency_full.sh hazel_turin 144
  L1_to_L2:49152:1048576,L2_to_LLC:1048576:33554432,LLC_to_DRAM:33554432:536870912`
- **Results (base run, random pattern, median ticks/access): L1_to_L2=130.0, L2_to_LLC=442.0,
  LLC_to_DRAM=780.0** -- cleanly increasing. Only one (transition, pattern) cell flagged
  >20% spread (L1_to_L2 random, 21.4%), the least noisy miss_latency result of any Hazel
  generation so far -- consistent with this machine already having the cleanest DRAM-plateau
  result in the capacity section.

### inclusion_policy/
**(Slurm job 838248, elapsed 1m59s, exit 0. All three pairings came back UNCERTAIN -- same
total-non-answer category as hazel_broadwell's and hazel_genoa's own results; see genoa's
own bullet for the cross-machine "both AMD generations" observation.)**
- Source file(s): `main_code/common/inclusion_policy.{c,h}`,
  `scripts/run_inclusion_policy_full.sh` (`HAZEL_MODE=1`),
  `scripts/classify_inclusion_policy.py`, `scripts/plot_inclusion_policy.py`
- Run command + arguments: `HAZEL_MODE=1 ./scripts/run_inclusion_policy_full.sh hazel_turin
  144 L1_vs_L2:49152:1048576:L1_to_L2,L2_vs_LLC:1048576:33554432:L2_to_LLC,
  L1_vs_LLC:49152:33554432:LLC_to_DRAM` (`ASSUMED_LINE_SIZE_BYTES` default 64).
- **Results:**
  - **L1_vs_L2**: target 0.0% survived-like / 32.0% invalidated-like / 136 ambiguous, control
    2.5% survived-like / 0.5% invalidated-like / 194 ambiguous -- both channels mostly
    ambiguous. **Verdict: UNCERTAIN (mixed result)**.
  - **L2_vs_LLC**: confound warning fired -- **control read 21.5% invalidated-like**, despite
    never being touched. **Verdict: UNCERTAIN (confound suspected)**.
  - **L1_vs_LLC (skip-level)**: confound warning fired, more severely -- **control read
    46.0% invalidated-like**, and target itself read a stark 100.0% invalidated-like (0
    survived, 0 ambiguous). **Verdict: UNCERTAIN (confound suspected)** despite the target's
    own extreme reading, because the control contamination means that reading cannot be
    trusted as reflecting the target's real behavior.
  - **Best-guess overall reading: none -- no directional claim is supportable from this
    machine's data**, same as hazel_broadwell's and hazel_genoa's own results.
- Full transcript: see `data_raw/hazel_turin/inclusion_policy/run_inclusion_policy_full_*.log`

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
