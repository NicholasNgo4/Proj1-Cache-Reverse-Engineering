#!/bin/bash
#SBATCH --job-name=hw1_cache
#SBATCH --output=hw1_%x_%j.out
#SBATCH --error=hw1_%x_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --constraint=REPLACE_ME   # e.g. haswell, broadwell, skylake, cascadelake,
                                   # icelake_6326, icelake_8358, sapphirerapids, genoa, turin

set -euo pipefail
hostname
uname -a
grep -m1 -E 'model name|Hardware|Processor' /proc/cpuinfo

# Run only after the lab-only prediction has been frozen (see PREDICTION_FREEZE.md).
srun --cpu-bind=cores ./cache_bench <your arguments>
