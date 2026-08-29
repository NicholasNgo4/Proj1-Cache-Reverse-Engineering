# hpc_slurm/

One Slurm job script per attempted Hazel CPU generation (see Table 4). Name scripts
`hw1_<constraint>.sh`, e.g. `hw1_haswell.sh`, `hw1_genoa.sh`.

Record for every run (in the corresponding `data_raw/hazel_<generation>/README.md`):
Slurm job ID, requested constraint, hostname, exact CPU model, date/time, logical
CPU/core binding, socket/package, NUMA node, compiler+flags, benchmark Git commit, and
raw output filename.

Remember: do NOT run the cache-experiment suite on Hazel until the lab-only prediction
is frozen (see `../PREDICTION_FREEZE.md`). Access-checking and trivial non-cache test
jobs are allowed before the freeze.
