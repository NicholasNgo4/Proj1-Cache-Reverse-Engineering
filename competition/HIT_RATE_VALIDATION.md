# Competition 2 — Software-Only Cache Hit-Rate Validation

Estimator source: `main_code/software_hit_rate/` — final frozen parameters must be
committed before official competition scoring. The estimator may use timers and
ordinary unprivileged instructions only; it may NOT read PMU counters, privileged
registers, cache-topology answers, or spec tables at estimation time.

## Frozen Estimator Reference

| Field | Value |
|---|---|
| Estimator source file(s) | |
| Frozen parameters (threshold/model coefficients) | |
| Git commit hash (competition-ready) | |
| Freeze date/time | |

## Calibration Summary

- Cache-resident calibration workload: 
- Non-resident calibration workload: 
- Classification rule / probabilistic model: 
- Confidence/uncertainty reporting method: 

## Validation Table (team's own verification machines, PMU accessible)

| Machine | Workload | Software-estimated hit rate Ĥ (%) | PMU-derived hit rate H (%) | \|Ĥ − H\| (pp) | Notes |
|---|---|---|---|---|---|
| | | | | | |

Mean absolute percentage-point deviation (team's own verification set): `___`

**Note:** Official competition scoring may use held-out machine/workload combinations
the team did not calibrate on, to measure generalization rather than memorization.
