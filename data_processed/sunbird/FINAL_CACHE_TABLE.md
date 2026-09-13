# Final Inferred Cache Table — Sunbird (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see the sibling directories next to this file
for the raw/processed data and plots behind each field) — no new runs. Ticks are
this machine's own TSC-scale counter (not directly comparable across machines —
see `CAPACITY_RESULTS.md`'s units caveat). Where a field is unresolved, that's
stated rather than guessed, per the assignment's "report uncertainty or a
behavioral bound... rather than guessing" instruction.

**Full reasoning, per-pairing raw numbers, and every caveat behind this table
live in `data_raw/sunbird/README.md`** (the `inclusion_policy/` section's
"Best-guess synthesis" subsection, plus the `capacity/`, `line_size/`,
`associativity/`, and `latency/` sections above it) — this file is the
consolidated table itself, not a replacement for that reasoning.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (same, see overhead caveat) | Sharing scope | Inclusion/exclusion (vs. level below) |
|---|---|---|---|---|---|---|---|---|
| L1D | 32,768 B (32 KiB) — confirmed | 64 B — confirmed, 2 independent methods | 8-way — confirmed (clean knee, 0% repeat spread) | 64 | ≈10.35 ticks | L1→L2 ≈124 ticks (inflated by an estimated ~64-85 tick fixed single-shot overhead — see latency/ caveat; true incremental cost likely well below this) | Private per core — **assumed, not tested this phase** | **NOT INCLUSIVE** of/by L2 (90% of trials survived L2-scale eviction) — exclusive or non-inclusive; this method can't distinguish those two further |
| L2 | 262,144 B (256 KiB) per `CAPACITY_RESULTS.md` — **this machine's own capacity data flags it as possibly just a point on a continuous ramp, not a confirmed plateau** | 64 B — same clean split as the other two levels, but anchored to an unconfirmed boundary so read with the same caveat | **UNRESOLVED** — every candidate byte value tested breaks at the same num_ways≈9-10 regardless of capacity (confound, not a real associativity signal; see associativity/ section) | Cannot compute (A unresolved) | ≈26.83 ticks | L2→LLC ≈284 ticks (same overhead caveat) | Private per core — **assumed** | **UNCERTAIN** vs. LLC (85% of trials ambiguous) — and per the caveat-3 sharpening above, structurally unreliable for an L2 target regardless of repeat count |
| LLC | ~30 MiB (31,457,280 B representative) per `CAPACITY_RESULTS.md` | 64 B — the cleanest fit of the three levels | **UNRESOLVED** — same confound as L2 | Cannot compute | ≈58.42 ticks | LLC→DRAM ≈622 ticks (same overhead caveat, smaller fraction of this larger number) | Shared across cores/socket — **assumed, not tested** | Skip-level test (L1 vs LLC): **UNCERTAIN**, leaning **INCLUSIVE-like** (75% invalidated, just under the 80% firm-call threshold) |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈207.10 ticks | — | — | — |

**Overall best-guess read of the hierarchy:** L1D is a confirmed 32 KiB/8-way/
64 B private cache, non-inclusive with respect to L2. L2's own size,
associativity, and inclusion behavior remain unresolved on this machine — line
size only, at 64 B, carries over cleanly. The LLC's line size is the
best-supported of the three (64 B, cleanest elbow), while its capacity is a
~30 MiB estimate and its associativity is unresolved; its skip-level relationship
to L1 leans inclusive without clearing the confidence bar. The single most
plausible unifying story (see `data_raw/sunbird/README.md`'s inclusion_policy/
synthesis): a non-inclusive L2 paired with an LLC that behaves inclusively
toward L1 (and by extension likely L2) — consistent with, though not proven by,
every pairing tested. Associativity above L1, and L2's own capacity, are this
table's biggest open gaps; both are documented dead ends under the current
method (see `data_raw/sunbird/README.md`'s associativity/ section) rather than
unattempted.
