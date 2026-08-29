# Prediction Freeze Log

This file is the audit trail proving the lab-only prediction was frozen **before** any
cache experiment ran on Hazel. Complete it, commit it, and tag the commit
(e.g. `predictions-frozen`) before submitting the first Hazel `sbatch` job that runs the
cache-reverse-engineering suite.

## Freeze Record

| Field | Value |
|---|---|
| Freeze date/time | |
| Git commit hash at freeze | |
| Git tag | `predictions-frozen` |
| Timestamp of first Hazel cache-experiment job (must be AFTER freeze) | |
| Slurm job ID of that first Hazel cache run | |

## Frozen Lab-Only Prediction Table

Fit using **only** Sunbird, Thunderbird, Skylark, Artemisia, Charnwood, Crux, Ookay,
Upgrade observations. Do not touch after freezing.

| Quantity | Model/fit used | Predicted value(s) for target Hazel generation(s) | Uncertainty range | Target Hazel generation |
|---|---|---|---|---|
| L1D capacity | | | | |
| L1D associativity | | | | |
| L1D hit latency | | | | |
| L1 miss penalty | | | | |
| L2 capacity/core | | | | |
| L2 associativity | | | | |
| L2 hit latency | | | | |
| L2 miss penalty | | | | |
| LLC capacity (sharing domain) | | | | |
| LLC associativity (effective) | | | | |
| LLC hit latency | | | | |
| LLC→memory miss penalty | | | | |
| Line size | | | | |
| Inclusion/exclusion behavior | | | | |

## Team Cache Laws — Frozen Predictions

| Law name | Quantitative rule (equation/doubling-time/slope) | Predicted value for held-out Hazel generation | Uncertainty |
|---|---|---|---|
| `<LastName1>–<LastName2> Cache ___ Law` | | | |
| `<LastName1>–<LastName2> Cache ___ Law` | | | |

## Held-Out Evaluation (fill in AFTER Hazel measurements, never edit the rows above)

| Quantity | Frozen prediction | Hazel measured value | Absolute/relative error | Supported / weakened / falsified | Discussion |
|---|---|---|---|---|---|
| | | | | | |

**Rule:** Hazel points are never used to refit the dashed prediction line. If a
prediction fails, explain why in the discussion column — do not delete or alter the
frozen row.
