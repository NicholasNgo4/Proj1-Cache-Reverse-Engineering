# hpc_slurm/

## Access-check jobs (one per generation)

`hw1_<constraint>.sh` (e.g. `hw1_haswell.sh`, `hw1_genoa.sh`) -- one per attempted Hazel
CPU generation (Table 4). Identifies the allocated node via the Phase Discipline
whitelist, builds `cache_bench` in an isolated per-job directory
(`hazel_build/$SLURM_JOB_ID/`, NOT the shared checkout directly -- see below), and runs
a tiny (`--samples 1000`) `--experiment capacity` smoke test under
`srun --cpu-bind=cores`. Safe to run before the prediction freeze (non-cache access
check, per Phase Discipline). All 9 Table 4 generations have one of these; run and
recorded 2026-09-14.

## Full-suite jobs (one per generation per experiment type)

`hw1_<constraint>_<experiment>.sh` (e.g. `hw1_haswell_capacity.sh`) -- the real
1,000,000-sample Phase-I suite, gated behind a runtime `predictions-frozen`-ancestry
check. Split by experiment type (capacity / line_size / associativity / hit+miss
latency / inclusion_policy) rather than one job per generation, for two reasons: (1)
`compute_partners`'s only QOS available to this account is `short`, capped at 2h wall
time (`sacctmgr show qos`) -- a combined single job risks exceeding that, per this
project's own lab-machine experience that a full capacity pipeline alone can take
"roughly an hour"; (2) every later experiment needs that generation's own
hand-confirmed capacity boundaries as input (same discipline already used on every lab
machine -- see each `data_raw/<machine>/README.md`), so a human/Claude review step
between capacity finishing and line_size/associativity/latency/inclusion_policy
starting is unavoidable regardless of job structure. Each script wraps the
corresponding `scripts/run_*_full.sh` (or `scripts/run_line_size.sh`) pipeline with
`HAZEL_MODE=1`, which that script now supports natively (see below) -- do not
reimplement the sweep logic in the job script itself.

## `HAZEL_MODE=1` in `scripts/run_*_full.sh` / `run_line_size.sh` / `run_software_hit_rate_sweep.sh`

These scripts (shared with the lab machines) now accept `HAZEL_MODE=1` as an
environment variable: when set, they build `cache_bench` into an isolated
`hazel_build/$SLURM_JOB_ID/` copy instead of the shared checkout, and pin with
`srun --cpu-bind=cores` instead of `taskset -c "$CORE"`. **Do not remove this
isolation** -- confirmed necessary the hard way: a same-batch submission of 8 sister
access-check jobs that all ran `make clean && make` directly in this one shared GPFS
checkout (unlike the lab machines, which each have their own separate, non-shared
`/home`) produced a missing-`.o` link failure on one job and could not be trusted not
to have silently corrupted another's "successful" build. `HAZEL_MODE=0` (the default)
is unchanged lab-machine behavior. The `<machine>` argument these scripts take should
be `hazel_<constraint>` (matching the existing `data_raw/hazel_<constraint>/`
directories); the `<core>` argument is only used for `taskset` in lab mode -- under
Hazel mode, pass whatever `numactl -s`'s `physcpubind` reports (informational only,
since `--cpu-bind=cores` does the real pinning).

## Python plotting/analysis tools on Hazel

`source hpc_slurm/hazel_python_env.sh` before calling any `scripts/*.py` tool
(`summarize_raw.py`, `detect_*.py`, `plot_*.py`) on Hazel. Hazel's default `python3`
(3.9.25) has numpy/scipy but not matplotlib, and a normal `pip install --user` fails
outright (home directory quota exceeded) -- matplotlib+numpy were instead installed
once into GPFS project storage; see that script's own header comment before re-running
the install.

## Recording results

Record for every run (in the corresponding `data_raw/hazel_<generation>/README.md`):
Slurm job ID, requested constraint, hostname, exact CPU model, date/time, logical
CPU/core binding, socket/package, NUMA node, compiler+flags, benchmark Git commit, and
raw output filename.

Remember: do NOT run the cache-experiment suite on Hazel until the lab-only prediction
is frozen (see `../PREDICTION_FREEZE.md`). Access-checking and trivial non-cache test
jobs are allowed before the freeze. (As of 2026-09-14 the freeze is complete --
`predictions-frozen` tag at commit `b4bf2a3` -- so full-suite jobs are now permitted;
the split-by-experiment-type structure above is a wall-time/dependency constraint, not
a remaining Phase Discipline block.)
