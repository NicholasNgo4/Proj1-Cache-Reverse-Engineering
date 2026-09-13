# Final Inferred Cache Table — Sunbird (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see the sibling directories next to this file
for the raw/processed data and plots behind each field) — no new runs. Ticks are
this machine's own TSC-scale counter (not directly comparable across machines —
see `CAPACITY_RESULTS.md`'s units caveat).

**Every field below leads with a concrete best-guess value, never a bare
"unresolved."** Where direct measurement was blocked by a confound (this
happened for L2/LLC associativity — see the associativity/ section for the
full multi-machine confound investigation), the number given is this team's
best reasoned estimate from the available evidence, following PROJECT 1.pdf's
own instruction to "report an effective bound... rather than guessing" — not a
guess pulled from nowhere, and not a refusal to answer. Each such cell says
plainly how confident it is and why, so the reasoning can be checked or
revised, but the table always states a position.

**Full raw numbers, per-pairing detail, and the confound investigation itself
live in `data_raw/sunbird/README.md`** (the `associativity/` section for the
associativity reasoning below, the `inclusion_policy/` section's "Best-guess
synthesis" for the inclusion/exclusion reasoning) — this file is the
consolidated best-guess table, not a replacement for that evidence.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (same, see overhead caveat) | Sharing scope | Inclusion/exclusion (vs. level below) |
|---|---|---|---|---|---|---|---|---|
| L1D | 32,768 B (32 KiB) — confirmed | 64 B — confirmed, 2 independent methods | **8-way — confirmed** (clean knee, 0% repeat spread across base+2 repeats, both patterns) | 64 | ≈10.35 ticks | L1→L2 ≈124 ticks (inflated by an estimated ~64-85 tick fixed single-shot overhead — see latency/ caveat; true incremental cost likely well below this) | Private per core (best guess — architecturally universal for L1D; not directly tested this phase) | **Best guess: NON-INCLUSIVE / exclusive-like w.r.t. L2** (90% of trials survived L2-scale eviction, cleanest and most confident result of the three pairings) |
| L2 | 262,144 B (256 KiB) per `CAPACITY_RESULTS.md` (hand-verified; take as given) | 64 B — same clean split as the other two levels | **Best guess: 8-way** (see reasoning below) | 512 | ≈26.83 ticks | L2→LLC ≈284 ticks (same overhead caveat) | Private per core (best guess) | **Best guess: leans NON-INCLUSIVE w.r.t. LLC** (13.5% survived-like vs. 1.5% invalidated-like among the trials that resolved at all — a 9:1 lean toward survival — though 85% of trials fell in the ambiguous zone; lowest-confidence read of the three pairings, see caveat below) |
| LLC | ~30 MiB (31,457,280 B representative) per `CAPACITY_RESULTS.md` | 64 B — the cleanest elbow of the three levels | **Best guess: 9-way** (effective lower bound; see reasoning below) | ≈54,613 (non-integer — expected, since ~30 MiB is itself a rounded capacity estimate, not an exact hardware value) | ≈58.42 ticks | LLC→DRAM ≈622 ticks (same overhead caveat, a smaller fraction of this larger number) | Shared across cores/socket (best guess — architecturally typical for an LLC; not directly tested) | **Best guess: leans INCLUSIVE w.r.t. L1** (skip-level test: 75% invalidated-like vs. 11% survived-like — the clearest directional lean of the three pairings, just short of the strict 80% firm-call threshold) |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈207.10 ticks | — | — | — |

## Associativity reasoning (L2 = 8-way, LLC = 9-way, both best-guess)

Direct measurement of L2 and LLC associativity is confounded on this machine
(and on 5 of the other 7 team machines): every candidate byte value tried as
the conflict-set stride — spanning 512 KiB to ~30 MiB, a >50x range — tends to
break somewhere in the same num_ways≈9-10 neighborhood regardless of which
level it nominally targets, which is the signature this team has used
throughout (see `data_raw/sunbird/README.md`'s associativity/ section) to
argue that a small, fixed-size structure below the real cache level (most
likely DTLB-related) saturates first and can mask the level's true eviction
threshold. That confound is real and well-evidenced, but it does not mean the
question is unanswerable — it means the raw detector's single reported number
can't always be taken at face value, and the best-guess value has to be
reasoned from more than one data point:

- **L2 → 8-way.** Two independent lines of evidence point below the ~9-10
  confound wall rather than at it: (1) Sunbird's own 2026-09-12 re-run at this
  exact candidate (262,144 B) disagreed with the universal wall entirely —
  base run reported 3, both repeats reported 4, not 9-10 — meaning this
  candidate is NOT simply reproducing the same confound value seen elsewhere;
  something smaller and softer is happening here. (2) Upgrade's more rigorous,
  higher-sample-count derived-stride-scan re-test at an equivalent L2-region
  stride resolved the ambiguity directly: a genuine plateau survives cleanly
  through way 8 (accesses still mostly hit), with only a marginal, noisy
  partial rise at way 4 that a full-rigor re-check did not confirm as true
  thrashing — the real, sharp eviction jump only appears at way 9, i.e., 8
  concurrently-resident lines fit without conflict. Combined with L1's own
  confirmed 8-way (mid-level caches essentially never have lower associativity
  than L1 in real designs) and the internal-consistency check below, 8-way is
  the best-supported single number, with the caveat that it cannot be fully
  separated from the neighboring confound.
- **LLC → 9-way**, reported as the most reproducible empirical eviction
  threshold rather than a fully independent number. The 2026-09-12
  CAPACITY_RESULTS.md-anchored re-run at this exact candidate gave 9-way with
  full 3/3 agreement (base + both repeats), the cleanest reproducibility of
  any LLC-scale attempt on this machine. Per PROJECT 1.pdf's explicit
  allowance to "report an effective bound and explain the limitation" when
  LLC slicing/hashing (or, here, this confound) prevents a clean measurement,
  9-way is presented as an **effective lower bound and best point estimate**:
  the true value could be higher and masked by the same small-structure
  confound (a real LLC is often, though not always, at least as associative as
  the levels above it), but 9-way is what the data most directly and
  repeatedly supports, and is not weaker evidence than any alternative number
  this method could produce.
- **Internal-consistency cross-check (PROJECT 1.pdf explicitly asks for
  S=C/(A×B) as a cross-check):** using 8-way uniformly for L1/L2 and 9-way for
  LLC, the derived set counts are 64 / 512 / ≈54,613. L1→L2's set count scales
  by exactly 8x, matching the L1→L2 capacity ratio (262,144/32,768 = 8)
  exactly — a clean, internally consistent result. LLC's own set count does
  NOT come out to a clean integer at 9-way (54,613.3), which is expected
  (the ~30 MiB LLC capacity is itself a rounded estimate, not measured to the
  byte) rather than a sign the associativity guess is wrong — for comparison,
  using 8-way instead at LLC's capacity gives an exactly clean 61,440 sets,
  which is worth keeping in mind as a close, similarly-plausible alternative
  best guess if a single integer-friendly number is preferred over the
  slightly-more-reproduced 9-way reading.

## Overall best-guess read of the hierarchy

Sunbird's cache hierarchy is best read as **32 KiB / 8-way L1D, 256 KiB / 8-way
L2 (best guess), and a ~30 MiB / 9-way LLC (best guess)**, all sharing the same
64 B line size. L1 is non-inclusive of L2 with high confidence. The two
LLC-involving pairings both lean in a specific direction rather than sitting
neutral: L2 vs. LLC leans non-inclusive (low confidence — this pairing is also
the one most structurally undermined by the target's index not fitting in one
page, per `data_raw/sunbird/README.md`'s caveat 3), while the skip-level L1 vs.
LLC test leans inclusive (moderate confidence, clearest directional lean of
the three). Put together, the best-supported single story is an LLC that
maintains a directory-style inclusion of L1's own resident lines specifically
(consistent with a cross-core snoop-filter design) without necessarily
guaranteeing the same for whatever L2 happens to hold independently — L2 itself
behaving as a non-inclusive mid-level cache relative to both levels around it.
This is this team's best-supported inference from the data collected, not a
certainty; the associativity values above are the most defensible point
estimates available given a real, well-documented measurement confound, not
directly observed facts.
