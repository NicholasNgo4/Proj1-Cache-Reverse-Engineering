# Final Inferred Cache Table — Skylark (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see the sibling directories next to this file
for the raw/processed data and plots behind each field) — no new runs beyond
`inclusion_policy/` itself. Ticks are this machine's own TSC-scale counter (not
directly comparable across machines — see `CAPACITY_RESULTS.md`'s units caveat).
Same format as `data_processed/sunbird/FINAL_CACHE_TABLE.md`, so the two can be
read side by side.

**Every field below leads with a concrete best-guess value, never a bare
"unresolved."** Where direct measurement was blocked by a confound (L2/LLC
associativity, same universal small-way-count wall documented across 5 of the
other 7 team machines in `CLAUDE.md`), the number given is this team's best
reasoned estimate from the available evidence, following PROJECT 1.pdf's own
instruction to "report an effective bound... rather than guessing." Each such
cell says plainly how confident it is and why.

**Full raw numbers, per-pairing detail, and caveats live in
`data_raw/skylark/README.md`** (the `associativity/` section for the
associativity reasoning below, the `inclusion_policy/` section's "Best-guess
synthesis" for the inclusion/exclusion reasoning) — this file is the
consolidated best-guess table, not a replacement for that evidence.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (same, see overhead caveat) | Sharing scope | Inclusion/exclusion (vs level below) |
|---|---|---|---|---|---|---|---|---|
| L1D | 32,768 B (32 KiB) — confirmed (flat-then-ramp signature; matches Sunbird/Upgrade/Charnwood/Crux/Ookay) | 64 B — confirmed, 2 independent methods (Method A family-of-curves + Method B ramp-saturation, both agree) | **8-way — confirmed** (single sharp knee at num_ways=9, identical across base + 2 repeats, both patterns) | 64 | ≈6.24 ticks | L1→L2 ≈96.0 ticks (inflated by an estimated ~65.8 tick fixed single-shot overhead — see latency/ caveat; overhead-corrected estimate ≈24 ticks) | Private per core (best guess — architecturally universal for L1D; not directly tested this phase) | **Best guess: WEAK LEAN NON-INCLUSIVE w.r.t. L2** (68.0% survived-like vs. 0.5% invalidated-like, but classifier itself calls this pairing UNCERTAIN — target/control medians came back nearly identical, a much weaker signal than Sunbird's clean 90%-survived result; same qualitative direction, lower confidence) |
| L2 | 524,288 B (512 KiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given — this machine's own capacity sweep only resolved a broad ~4-16.8 MiB candidate shelf, not a clean 512 KiB edge) | 64 B — best available estimate (no counter-evidence; this footprint's own line_size sweep found no elbow at all, a null result, not a competing answer) | **Best guess: 8-way** (see reasoning below) | 1,024 | ≈16.15 ticks | L2→LLC ≈120.0 ticks (same overhead caveat; overhead-corrected estimate ≈38 ticks) | Private per core (best guess) | **Best guess: NON-INCLUSIVE w.r.t. LLC** (99.5% survived-like, 0% invalidated-like — but read with the LEAST confidence of the three pairings: L2's index almost certainly doesn't fit in one page (same caveat as Sunbird's own weakest pairing), and `CAPACITY_RESULTS.md`'s 8 MiB LLC value is itself likely an underestimate of this machine's real LLC capacity, see below) |
| LLC | 8,388,608 B (8 MiB) per `CAPACITY_RESULTS.md`, but **flagged as a likely UNDERESTIMATE** — this machine's own capacity data shows the real LLC→DRAM knee starting closer to ~16.8-21.8 MiB, with 8 MiB sitting inside an earlier, unresolved candidate shelf rather than at a confirmed edge | 128 B — confirmed at the deep, genuine LLC→DRAM transition boundary (18,295,680 B; both methods agree) — notably 2x this machine's own L1 line size, a real and still-unexplained per-level disagreement (see line_size/ section) | **Best guess: 8-way** (effective estimate; see reasoning below) | 8,192 (using the 128 B line size above; a clean integer) | ≈27.22 ticks | LLC→DRAM ≈360.0 ticks (same overhead caveat; overhead-corrected estimate ≈267 ticks) | Shared across cores/socket (best guess — architecturally typical for an LLC; not directly tested) | **Best guess: NON-INCLUSIVE w.r.t. L1 (skip-level)** (100% survived-like, 0% invalidated-like — the cleanest of the three pairings numerically, though carrying the LLC-capacity-underestimate caveat above. Notably DIFFERENT from Sunbird's own skip-level result, which leaned inclusive; plausibly consistent with AMD Zen 2's publicly documented non-inclusive L3 design — noted only as a post-hoc plausibility check, not consulted while forming this reading, same discipline as Sunbird's own aside) |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈274.87 ticks | — | — | — |

## Associativity reasoning (L2 = 8-way, LLC = 8-way, both best-guess)

Direct measurement of L2 and LLC associativity is confounded on this machine,
same as 5 of the other 7 team machines (see `CLAUDE.md`'s running tally):

- **Auto-detected numbers are not directly citable.** L2 (524,288 B stride)
  auto-detected "9-way" from a multi-step staircase (jump at num_ways=9,
  partial drop, second jump at 13, a third rise ~37) — the detector locked
  onto the *first* jump, which lands at exactly num_ways=9, i.e. the same
  value as L1's own confirmed knee. Since 524,288 B is an exact 16x multiple
  of L1's own 32,768 B stride, every probed node here also aliases into the
  same L1 set as every other node — this measurement is very plausibly just
  re-detecting L1's own 8-way limit (knee at num_ways=9 → associativity 8),
  not L2's real associativity. LLC (8,388,608 B) auto-detected "8-way" from
  a similarly multi-step staircase (small step at 8, another at 12, dominant
  transition actually ~25-34), and this one ISN'T even internally
  reproducible: base=8, rep1=8, rep2=7, with `run_associativity_full.sh`'s
  own built-in check printing an explicit disagreement warning. Neither
  number should be cited as-is (see `associativity/` section above,
  "NOT TRUSTWORTHY" call on both).
- **L2 → 8-way, best guess.** The auto-detected "9" is best read as an
  L1-aliasing artifact landing on L1's own num_ways=9 knee (→ 8-way), not
  independent evidence for a different L2 value. Absent a clean independent
  signal, the standard reasoning this team has used elsewhere applies:
  mid-level caches essentially never have LOWER associativity than L1 in
  real designs, so 8-way (matching L1) is the best-supported single number.
  The S=C/(A×B) cross-check below supports this pick over any alternative.
- **LLC → 8-way, best guess.** The base run's own auto-detected number (8)
  agrees with 1 of 2 repeats (8, 8, 7 — majority/mode is 8), and per the
  S=C/(A×B) cross-check below, 8-way is the only associativity in the
  small-integer range that produces a perfectly clean derived-set count
  (8,192) at this machine's confirmed 128 B LLC-region line size — 9-way at
  the same line size gives a non-integer 7,281.4, which is a mild but real
  point against it. Per PROJECT 1.pdf's explicit allowance to "report an
  effective bound and explain the limitation" when the confound prevents a
  clean measurement, 8-way is presented as an effective point estimate: the
  true value could be masked upward or downward by the same small-structure
  confound documented across the team's other machines, but 8-way is both
  what the (admittedly disagreeing) raw data most often reports and the
  only nearby integer that keeps the derived-set arithmetic clean.
- **Internal-consistency cross-check (PROJECT 1.pdf explicitly asks for
  S=C/(A×B) as a cross-check):** using 8-way uniformly for L1/L2/LLC and
  the line sizes confirmed nearest each level (64 B for L1/L2, 128 B for
  LLC), the derived set counts are 64 / 1,024 / 8,192. L1→L2's set count
  scales by exactly 16x, matching the L1→L2 capacity ratio
  (524,288/32,768 = 16) exactly — clean and internally consistent. LLC's
  8,192 sets is also a clean integer (not a coincidence of a rounded
  capacity value the way Sunbird's ~30 MiB estimate was — 8,388,608 B is
  this machine's exact `CAPACITY_RESULTS.md` value, if likely an
  underestimate of the *true* boundary per the caveat in the main table
  above). Trying 9-way at LLC instead breaks this cleanliness
  (7,281.4 sets, non-integer) — additional, if modest, support for 8-way
  over 9-way here specifically (unlike Sunbird, where 9-way was the
  cleaner-reproduced number and 8-way the cleaner-integer one — the two
  machines land on different sides of that particular tradeoff, worth
  noting rather than resolving further under Phase I timing-only
  discipline).

## Overall best-guess read of the hierarchy

Skylark's cache hierarchy is best read as **32 KiB / 8-way L1D (64 B line),
512 KiB / 8-way L2 (best guess, 64 B line, best available), and an 8 MiB+
(likely understated) / 8-way LLC (best guess, 128 B line, confirmed)** — this
machine is the one clear counter-example on the team to "line size is uniform
across levels" (64 B at L1, 128 B at the deep LLC-region transition, both
independently confirmed by two methods each), a genuine and still-unexplained
hardware finding rather than a methodology gap. All three inclusion_policy
pairings lean the same direction — non-inclusive/exclusive-like — unlike
Sunbird's mixed result (non-inclusive L2, leaning-inclusive skip-level LLC).
The L1-vs-L2 pairing's lean is weak and the classifier itself calls it
UNCERTAIN; the two LLC-involving pairings read as more numerically clean but
carry an important caveat that `CAPACITY_RESULTS.md`'s 8 MiB LLC value likely
undershoots this machine's real LLC capacity (own capacity data points closer
to ~16.8-21.8 MiB), which could mean the eviction footprint used for those two
pairings understates true LLC-scale pressure. Put together, the best-supported
single story is a cache hierarchy where **no level is inclusive of the level
below it** — plausible on its own merits, and directionally consistent with
AMD Zen 2's publicly documented non-inclusive L3 design (a post-hoc
plausibility check only, not part of the Phase-I timing evidence above, same
discipline as Sunbird's own aside) — but this team's best-supported inference
from the data collected, not a certainty, and specifically weaker at the L1-L2
hop than at either LLC-involving hop.
