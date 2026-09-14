# Prediction Freeze Log

This file is the audit trail proving the lab-only prediction was frozen **before** any
cache experiment ran on Hazel. Complete it, commit it, and tag the commit
(e.g. `predictions-frozen`) before submitting the first Hazel `sbatch` job that runs the
cache-reverse-engineering suite.

## Freeze Record

| Field | Value |
|---|---|
| Freeze date/time | 2026-09-14 18:23 UTC |
| Git commit hash at freeze | (filled in the follow-up commit that tags `predictions-frozen` — see git log) |
| Git tag | `predictions-frozen` |
| Timestamp of first Hazel cache-experiment job (must be AFTER freeze) | (not yet run — this pass only runs a non-cache access/build check, which Phase Discipline permits pre-freeze) |
| Slurm job ID of that first Hazel cache run | (not yet run) |

## Frozen Lab-Only Prediction Table

Fit using **only** Sunbird, Thunderbird, Skylark, Artemisia, Charnwood, Crux, Ookay,
Upgrade observations. Do not touch after freezing. Source: `CHRONOLOGICAL_MASTER_TABLE.md`
/ `data_processed/master/chronological_master_table.csv` (all 8 machines' Phase I timing
numbers) and `report.tex`'s Section 9 items 1–8 (the doubling model and the
constant/class-dependent findings). Target generation for every row below: **haswell**
(NC State's "Intel Xeon E5 v3" constraint) — chosen as this pass's pilot because it is the
oldest, most-available Hazel generation and the team already has a same-family analog
(Sunbird, a Haswell-EP Xeon E5-2680 v3, 2014).

| Quantity | Model/fit used | Predicted value(s) for target Hazel generation(s) | Uncertainty range | Target Hazel generation |
|---|---|---|---|---|
| L1D capacity | Chen–Ngo Cache Invariance Law (item 1: constant on 6/8 machines) | 32,768 B (32 KiB) | 32 KiB–49 KiB (Thunderbird 64 KiB and Artemisia 48 KiB are the only deviations, both non-Haswell) | haswell |
| L1D associativity | Chen–Ngo Cache Invariance Law | 8-way | 4–12 way (Thunderbird 4-way, Artemisia 12-way are the outliers; every x86 Xeon/Core machine agrees at 8) | haswell |
| L1D hit latency | No chronological trend (item 8) — Sunbird same-era/same-family analog | ~10.4 ticks / ~4.1 ns | 6.2–10.4 ticks across the 8-machine spread; ns/access is the more transferable unit since Hazel's TSC frequency is unknown a priori | haswell |
| L1 miss penalty | No chronological trend — Sunbird analog | ~124 ticks / ~49.6 ns | 67–188 ticks across the 8-machine spread (all carry an uncorrected fixed single-shot-overhead caveat, see `latency/` sections) | haswell |
| L2 capacity/core | Chen–Ngo Cache Capacity Doubling Law, C(t) = 256 KiB · 2^((t−2014)/3) | 256 KiB | evaluated exactly at the model's own 2014 fit endpoint (Sunbird), so this is a same-era identity prediction, not a forward extrapolation — no extra uncertainty band beyond the underlying step-function caveat (item 2/5) | haswell |
| L2 associativity | No chronological trend — Sunbird analog (Phase-II-confirmed 8-way) | 8-way | 4–8 way — flagged explicitly: 5 of 8 lab machines' Phase-I "8-way" guess turned out wrong (real value 4) once Phase II checked it, so this prediction carries a real, documented risk of being off by 2× | haswell |
| L2 hit latency | No chronological trend — Sunbird analog | ~26.8 ticks / ~10.7 ns | 14.3–28.1 ticks across the 8-machine spread | haswell |
| L2 miss penalty | No chronological trend — Sunbird analog | ~284 ticks / ~113.6 ns | 120–723 ticks across the 8-machine spread (wide — this quantity showed the least cross-machine consistency of any latency figure) | haswell |
| LLC capacity (sharing domain) | Class-dependent, not chronological (item 4) — Sunbird analog (2-socket server part, same class NC State's `haswell` constraint targets) | ~31,457,280 B (~30 MiB), 1-socket sharing domain | 8–52 MiB — LLC size is dominated by server-vs-desktop class and specific SKU, not generation; Hazel's actual E5 v3 SKU is unknown until the job reports it | haswell |
| LLC associativity (effective) | No chronological trend — Sunbird analog (Phase-II-confirmed 20-way, NOT Phase I's confound-blocked 9-way) | 20-way | 15–20 way — flagged: this is the field where Phase I's timing-only method was wrong most often (7 of 8 machines); we predict the Phase-II-corrected value, not the Phase-I-style guess, since Phase II ground truth is now available for Sunbird | haswell |
| LLC hit latency | No chronological trend — Sunbird analog | ~58.4 ticks / ~23.4 ns | 27.2–108 ticks across the 8-machine spread; ns/access is the transferable unit | haswell |
| LLC→memory miss penalty | No chronological trend — Sunbird analog | ~622 ticks / ~248.8 ns | 360–852 ticks across the 8-machine spread | haswell |
| Line size | Chen–Ngo Cache Invariance Law (item 1: 64 B on 8/8 machines, zero exceptions) | 64 B | none — the single most consistent measurement in the whole dataset | haswell |
| Inclusion/exclusion behavior | No chronological trend — Sunbird analog | L1 vs L2: NON-INCLUSIVE (confident). L2 vs LLC: UNCERTAIN. L1 vs LLC (skip-level): UNCERTAIN, leans INCLUSIVE | L2-vs-LLC and skip-level results split roughly evenly across the 8 lab machines (see `CHRONOLOGICAL_MASTER_TABLE.md`'s inclusion table) — only the L1-vs-L2 call is made with real confidence | haswell |

## Team Cache Laws — Frozen Predictions

| Law name | Quantitative rule (equation/doubling-time/slope) | Predicted value for held-out Hazel generation | Uncertainty |
|---|---|---|---|
| `Chen–Ngo Cache Capacity Doubling Law` | L2 capacity/core: C(t) = 256 KiB · 2^((t−2014)/3) (τ=3 years, fit from Sunbird 2014 → Artemisia 2023 endpoints only; report.tex item 5/6) | 256 KiB at haswell's ~2014 era (same-era identity prediction, not extrapolated) | Growth is a step function (5 flat years then 3 rapid doublings), not smooth — the model is an end-to-end summary between two points, not a validated per-year curve (item 5) |
| `Chen–Ngo Cache Invariance Law` | L1D capacity, L1D associativity, and line size are architecturally fixed points that do not scale with generation: 64 B line size held on 8/8 machines across 2014–2023 and 3 vendors/ISAs; L1D capacity/associativity held on 6/8 (item 1) | 32,768 B / 8-way / 64 B at L1D for haswell | Thunderbird (ARM) and Artemisia (Sapphire Rapids) are the only two deviations, both non-Haswell/non-x86-desktop-class machines — the law is expected to hold cleanly for an x86 Xeon target like haswell |

## Held-Out Evaluation (fill in AFTER Hazel measurements, never edit the rows above)

| Quantity | Frozen prediction | Hazel measured value | Absolute/relative error | Supported / weakened / falsified | Discussion |
|---|---|---|---|---|---|
| | | | | | |

**Rule:** Hazel points are never used to refit the dashed prediction line. If a
prediction fails, explain why in the discussion column — do not delete or alter the
frozen row.
