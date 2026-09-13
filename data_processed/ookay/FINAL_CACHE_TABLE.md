# Final Inferred Cache Table — Ookay (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see the sibling directories next to this file,
and `data_raw/ookay/README.md`, for the raw/processed data, plots, and full
narrative behind each field) — no new runs beyond `inclusion_policy/` itself.
Ticks are this machine's own TSC-scale counter (not directly comparable across
machines — see `CAPACITY_RESULTS.md`'s units caveat), and format/reasoning
style follows `data_processed/sunbird/FINAL_CACHE_TABLE.md`.

**Every field below leads with a concrete best-guess value, never a bare
"unresolved."** Where direct measurement was blocked by a confound (this
happened for L2/LLC associativity here too — see the associativity/ section of
`data_raw/ookay/README.md` for the raw staircase data, and the reasoning below
for how the confound was handled), the number given is this team's best
reasoned estimate from the available evidence, following PROJECT 1.pdf's own
instruction to "report an effective bound... rather than guessing" — not a
guess pulled from nowhere, and not a refusal to answer.

**Full raw numbers, per-pairing detail, and the associativity confound
evidence live in `data_raw/ookay/README.md`** (its `associativity/` section
for the associativity reasoning below, its `inclusion_policy/` section's
"Best-guess synthesis" for the inclusion/exclusion reasoning) — this file is
the consolidated best-guess table, not a replacement for that evidence.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (same, see overhead caveat) | Sharing scope | Inclusion/exclusion (vs. level below) |
|---|---|---|---|---|---|---|---|---|
| L1D | 32,768 B (32 KiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given) | 64 B — confirmed (clean, offset-independent elbow, `line_size/` section) | **8-way — confirmed** (single clean knee, 8/8/8 across base + 2 reproducibility repeats, both patterns) | 64 | ≈7.49 ticks | L1→L2 ≈96 ticks (inflated by an estimated ~58.5-tick fixed single-shot overhead — see latency/ caveat; true incremental cost likely well below this) | Private per core (best guess — architecturally universal for L1D; not directly tested this phase) | **Best guess: NON-INCLUSIVE / exclusive-like w.r.t. L2** (100% of target trials AND 100% of control trials read as survived-like, statistically indistinguishable from each other — the cleanest, most confident result of the three pairings) |
| L2 | 262,144 B (256 KiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given) | 64 B — weak/consistent evidence only (`line_size/` step-4 data flat across 40–88 B, not distinctively minimized at 64 B; not contradicted either) | **Best guess: 8-way** (see reasoning below) | 512 | ≈18.53 ticks | L2→LLC ≈723 ticks (same overhead caveat, plus an unresolved additional inflation — see latency/ section) | Private per core (best guess) | **Best guess: weak lean toward INVALIDATED / inclusive-like w.r.t. LLC** (target 30.5% invalidated-like vs. control's 2.5%, a ~12x relative lean — but 69.5% of target trials still read survived-like, and this is the lowest-confidence pairing of the three: an L2 target's index structurally doesn't fit in one page, so the eviction walk can land on target's own set by ordinary chance; Sunbird's own L2_vs_LLC leaned the *opposite* direction under the same caveat, so treat this cell as a directional guess, not a settled reading) |
| LLC | 8,388,608 B (8 MiB) per `CAPACITY_RESULTS.md` | 64 B — unresolved/inconclusive (`line_size/` family-of-curves data showed no stride-dependent separation at all) | **Best guess: 8-way** (effective point estimate; see reasoning below) | 16,384 | ≈74.78 ticks | LLC→DRAM ≈693 ticks (same overhead caveat; notably NOT clearly larger than L2→LLC's 723, see latency/ section's evict-bytes-margin hypothesis) | Shared across cores/socket (best guess — architecturally typical for an LLC; not directly tested) | **Best guess: leans INVALIDATED / inclusive-like w.r.t. L1** (skip-level test: paired check shows target read slower than its own control in 99.5% of trials — the single cleanest directional signal on this machine, even though the absolute-ticks classifier calls the median itself ambiguous, landing just inside the ±15% fence around its threshold) |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈284.45 ticks | — | — | — |

## Associativity reasoning (L2 = 8-way, LLC = 8-way, both best-guess)

Direct measurement of L2 and LLC associativity is confounded on this machine,
the same way it is on 5 of the other 7 team machines (see `CLAUDE.md`'s
"Running tally" paragraph): a small, fixed-size structure below the real
cache level (most likely DTLB-related) saturates before the level under test
does, so a raw detector reading can't be taken at face value. Ookay's own
data shows this unusually cleanly:

- **Both L2 (262,144 B) and LLC (8,388,608 B) produce numerically
  indistinguishable staircases** — the same two latency tiers (~7.2 ticks at
  num_ways 2–4, a first jump to ~15 at num_ways 5–8) at the **same** two
  num_ways breakpoints, despite a 32x difference in candidate byte capacity.
  `detect_associativity.py` reports the first step ("4-way") for both levels,
  never reaching the second, sharper jump at num_ways=9 — which lands at
  exactly L1's own independently-confirmed 8-way limit (using the same
  "reported associativity = first-thrashing-way − 1" convention the detector
  itself uses elsewhere).
- **Because L2's and LLC's curves are indistinguishable from each other in
  this data, there is no basis here to assign them different point
  estimates** — unlike Sunbird's table, which had an independent corroborating
  source (Upgrade's derived-stride-scan technique) that separated L2 from LLC
  and justified different numbers (8 vs. 9) for the two levels. That
  additional technique was not run on Ookay this session. Absent it, the most
  defensible move is to give both levels the **same** best guess rather than
  inventing an artificial split: the second knee at num_ways=9 recurring
  identically at both strides, combined with (1) L1's own confirmed 8-way
  value, (2) the general heuristic that mid-level and last-level caches are
  essentially never *less* associative than L1 in real designs, and (3) the
  cross-machine convergence already documented on Sunbird/Upgrade/Charnwood
  around this same num_ways≈9-10 wall — together make **8-way** the
  best-supported single number for both L2 and LLC on this machine.
- **Internal-consistency cross-check (S=C/(A×B)), but weaker evidence here
  than on Sunbird:** using 8-way uniformly, derived sets come out to
  64 / 512 / 16,384 — clean integers throughout, and L1→L2's set count scales
  by exactly 8x (matching the 262,144/32,768 = 8x capacity ratio) while
  L2→LLC's scales by exactly 32x (matching 8,388,608/262,144 = 32x). **This
  check is less discriminating here than it was for Sunbird**, though:
  Sunbird's ~30 MiB LLC value was itself a rounded, non-power-of-two estimate,
  so getting a clean integer set count was informative evidence for a
  specific associativity guess. Ookay's `CAPACITY_RESULTS.md` LLC value
  (8,388,608 B) is *already* an exact power of two, and 64 B is also a power
  of two — so C/(A×B) comes out to a clean integer for essentially any
  power-of-two associativity guess (4, 8, 16, 32, ...), not just 8. The clean
  integers above are consistent with 8-way, but do not on their own rule out
  4-way or 16-way the way Sunbird's non-integer-vs-integer contrast could.
  The real basis for the 8-way guess is the structural argument above
  (matching L1, matching the cross-machine wall), not this cross-check.

## Overall best-guess read of the hierarchy

Ookay's cache hierarchy is best read as **32 KiB / 8-way L1D, 256 KiB / 8-way
L2 (best guess), and an 8 MiB / 8-way LLC (best guess)**, with a confirmed 64 B
line size at L1 and a 64 B line size carried through to L2/LLC on weak,
uncontradicted (not positively confirmed) evidence. L1 is non-inclusive of L2
with high confidence — in fact the cleanest such result seen on any machine so
far (100%/100% survived-like, vs. Sunbird's 90%/92%). The two LLC-involving
pairings both lean toward INVALIDATED/inclusive-like rather than sitting
neutral: the skip-level L1 vs. LLC test leans inclusive with the strongest
directional signal on this machine (99.5% paired check), while L2 vs. LLC
leans the same direction more weakly (a ~12x tilt among resolved trials, but
still 69.5% survived-like overall) and carries the lowest confidence of the
three, both because of the structural page-index caveat and because Sunbird's
own L2_vs_LLC pairing leaned the opposite way. Put together, the
best-supported single story — independently arrived at on a second machine,
via the same method — is the same one Sunbird's table proposed: an LLC that
behaves inclusively toward what's resident above it (both L1 directly and,
more weakly and less certainly, L2), while L2 itself behaves as a
non-inclusive mid-level cache. This is this team's best-supported inference
from the data collected, not a certainty; the L2/LLC associativity values
above are the most defensible point estimates available given a real,
well-documented measurement confound, not directly observed facts.
