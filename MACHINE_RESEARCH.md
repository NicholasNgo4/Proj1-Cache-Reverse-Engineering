# Machine & Microarchitecture Research (Table 1 / Section 8.1)

**Reminder:** This research is for taxonomy/historical ordering only. Do NOT consult
cache specifications, Agner Fog, or vendor cache tables while filling this in — ISA,
vendor, microarchitecture codename, and introduction year are fair game; cache size/
ways/latency are not, until Phase I is frozen.

**Year convention chosen (state once, use everywhere):**
`<INTRODUCTION YEAR OF PROCESSOR GENERATION / MICROARCHITECTURE — pick one, not the
year the machine was purchased>`

## Table 1 — ECE/Ajorpaz Lab Machines

| Host | CPU model (from slides) | ISA / Architecture | Vendor | Microarchitecture / codename | Introduction year | Process node (if documented) | Source(s) |
|---|---|---|---|---|---|---|---|
| Sunbird | 2× Xeon E5-2680 v3 |x86-64 |Intel | Hasewell|2014 |22 nm | |
| Thunderbird | Ampere Q80-30 |AArch64 |Ampere |ARM Neoverse N1 |2020 |7 nm | |
| Skylark | 2× AMD EPYC 7532 |x86-64 |AMD |Zen 2 |2019 |7 nm | |
| Artemisia | 2× Xeon Gold 5420+ |x86-64 |Intel |Saphire Rapids |2023 |10 nm, Intel 7 | |
| Charnwood | Core i7-6700 |x86-64 |Intel |Sky Lake |2015 |14 nm | |
| Crux | Core i7-9700 |x86-64 |Intel |Coffee Lake |2019 |14 nm | |
| Ookay | Core i7-7700 |x86-64 |Intel |Kaby Lake |2017 |14 nm | |
| Upgrade | Core i7-8700 |x86-64 |Intel |Coffee Lake |2017 |14 nm | |

*Sort the final table (in the report) oldest → newest by introduction year before
plotting.*

## Table 4 — Hazel Slurm Constraints (research-only until Phase III)

| Slurm constraint | CPU family/model (NC State-listed) | Generation | Introduction year | Available in current `sinfo`? | Notes |
|---|---|---|---|---|---|
| haswell | Intel Xeon E5 v3 | Intel Haswell | | | |
| broadwell | Intel Xeon E5 v4 | Intel Broadwell | | | |
| skylake | Intel Xeon Scalable Processor | Intel Skylake-SP | | | |
| cascadelake | Intel Xeon 2nd Gen SP | Intel Cascade Lake | | | |
| icelake_6326 | Intel Xeon Gold 6326 | Intel Ice Lake-SP | | | |
| icelake_8358 | Intel Xeon Platinum 8358 | Intel Ice Lake-SP | | | |
| sapphirerapids | Intel Xeon 4th Gen | Intel Sapphire Rapids | | | |
| genoa | AMD EPYC 4th Gen | AMD Zen 4 / Genoa | | | |
| turin | AMD EPYC 5th Gen | AMD Zen 5 / Turin | | | |

Check live availability with `sinfo` / `si` immediately before each run — record the
exact CPU model returned by the allocated node, not just the constraint name.

## Two Pre-Registered Hypotheses (Section 8.1, item 2 — write BEFORE seeing any cache spec)

1. **Hypothesis A:** `<state a falsifiable hypothesis about how a cache quantity changes over time>`
2. **Hypothesis B:** `<state a second, different hypothesis>`
