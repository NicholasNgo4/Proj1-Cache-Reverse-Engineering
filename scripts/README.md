# scripts/

Processing and plotting scripts. Keep one row per script in the table below, updated
as scripts are added.

| Script | Input (raw/processed data) | Output (plot/table) | Notes |
|---|---|---|---|
| `run_capacity_sweep.sh <machine> [core] [args...]` | none (builds + runs `cache_bench --experiment capacity`) | `data_raw/<machine>/capacity/capacity_<timestamp>.csv` | Pins with `taskset`; use `srun --cpu-bind=cores` directly on Hazel instead. |
| `summarize_raw.py <raw.csv> -o <out.csv>` | `data_raw/<machine>/<experiment>/*.csv` | `data_processed/<machine>/<experiment>/summary.csv` | Generic: groups raw per-batch rows by every column except the trailing (trial-index, value) pair and computes n/mean/median/stddev/min/q1/q3/p5/p95/max/n_outliers. |
| `detect_cache_hierarchy.py <summary.csv>` | `data_processed/<machine>/capacity/summary.csv` | printed level table + capacity-boundary hypotheses | Timing-only knee detection on the median-latency-vs-size curve; a starting hypothesis to confirm against box plots, not the final report number. |
