# Final Inferred Cache Table — Artemisia (Phase I best guess, 2026-09-13)

Per PROJECT 1.pdf's required final table (`{level, size, line size, associativity,
derived sets, hit latency, miss/next-level latency, sharing scope, inclusion/
exclusion behavior}`). Built entirely from this machine's already-collected
results across every experiment type (`capacity/`, `line_size/`, `associativity/`,
`latency/`, `inclusion_policy/` — see `data_raw/artemisia/README.md`'s
sibling sections for the raw/processed data, plots, and full reasoning behind
each field) — no new runs beyond the inclusion_policy pass this same session.
Ticks are this machine's own TSC-scale counter (not directly comparable across
machines — see `CAPACITY_RESULTS.md`'s units caveat).

**Every field below leads with a concrete best-guess value, never a bare
"unresolved."** L2/LLC associativity is confounded here exactly as it was on
5 of the other 7 team machines (see the associativity/ section for the full
investigation and the reasoning below); the numbers given are this team's best
reasoned estimates from the available evidence, following PROJECT 1.pdf's own
instruction to "report an effective bound... rather than guessing." Each such
cell states its confidence plainly so the reasoning can be checked or revised.

**Full raw numbers, per-pairing detail, and the confound investigation itself
live in `data_raw/artemisia/README.md`** (the `associativity/` section for the
associativity reasoning below, the `inclusion_policy/` section's "Best-guess
synthesis" for the inclusion/exclusion reasoning) — this file is the
consolidated best-guess table, not a replacement for that evidence.

| Level | Size | Line size | Associativity | Derived sets (S=C/(A×B)) | Hit latency (dependent, random, median) | Miss/next-level latency (same, see overhead caveat) | Sharing scope | Inclusion/exclusion |
|---|---|---|---|---|---|---|---|---|
| L1D | 49,152 B (48 KiB) per `CAPACITY_RESULTS.md` (this machine's own capacity data has no clean plateau below ~48 KiB — see capacity/'s Anomaly 1 — but agrees the continuous ramp above starts here) | 64 B — confirmed, two methods (family-of-curves + single-curve), 3 independent reproductions, step-4 offset-invariance-confirmed | **Best guess: 12-way** (clean, reproducible transition to a low-spread ~16.2 ticks/access shelf at exactly num_ways=13 in all 3 runs; NOT machine-confirmed the way Sunbird/Upgrade/Charnwood's L1=8-way was, both because of this machine's known per-invocation P-state noise at small buffer sizes and an unexplained second jump past this knee — see associativity/ section) | 64 | ≈9.87 ticks | L1→L2 ≈188 ticks (inflated by an estimated ~60 tick fixed single-shot overhead — see latency/ caveat; true incremental cost likely well below this) | Private per core (best guess — architecturally universal for L1D; not directly tested this phase) | **UNCERTAIN w.r.t. L2** (target landed 77.5% ambiguous rather than cleanly classified, likely muddied by this pairing's oversized eviction footprint — see inclusion_policy/ caveat 4; a 100% paired-slower result hints at *some* sensitivity to L2-scale eviction, but not a clean verdict) |
| L2 | 2,097,152 B (2 MiB) per `CAPACITY_RESULTS.md` — **flagged NOT a confirmed boundary by this machine's own capacity data** (a waypoint inside one continuous ~48 KiB–90 MiB ramp, not a discrete plateau); used anyway per project-wide direction, but every field on this row inherits that extra uncertainty on top of the usual associativity confound | 64 B — best-supported candidate (visual family-of-curves signal + step-4 auto-pick agree), but the offset-invariance check that confirmed L1 came back genuinely mixed here (only ~half the tested offsets stayed saturated past the candidate stride) — see line_size/ section | **Best guess: 16-way** (see reasoning below) | 2,048 | ≈28.05 ticks | L2→LLC ≈381 ticks (same overhead caveat) | Private per core (best guess) | **Leans INCLUSIVE w.r.t. LLC** (100% invalidated-like, 0% ambiguous — a much cleaner split than Sunbird's own L2_vs_LLC result — but read with the caveat that an L2-sized target has no structural guarantee of avoiding its own set during the eviction walk, so this could in part reflect ordinary incidental eviction rather than a specific policy) |
| LLC | ~30 MiB (31,457,280 B representative) per `CAPACITY_RESULTS.md` — this machine's own data confirms only that ~90 MiB is a genuine plateau *onset*, not that 31,457,280 B specifically is a clean edge (see capacity/ section); used per project-wide direction | 64 B — the only line size measured anywhere on this machine; 11 independent attempts specifically at this ~30 MiB candidate found no line-size-detectable signal at all (see line_size/ section's extensive null-result investigation) — carried over as the best available default, not a machine-specific measurement at this level | **Best guess: 16-way** (effective point estimate; see reasoning below — 8-way remains an equally plausible, similarly clean alternative) | 30,720 | ≈94.38 ticks | LLC→DRAM ≈582 ticks (same overhead caveat, a smaller fraction of this larger number) | Shared across cores/socket (best guess — architecturally typical for an LLC; not directly tested) | **INCLUSIVE w.r.t. L1** (skip-level test: 100% invalidated-like, 0% ambiguous — the cleanest, most confident result of all three pairings on this machine, and the more structurally trustworthy of the two LLC-involving pairings since L1's own index fits within one page here too) |
| DRAM (reference floor, not a cache level) | — | — | — | — | ≈305.58 ticks | — | — | — |

## Associativity reasoning (L1 = 12-way best guess, L2 = LLC = 16-way best guess)

Direct measurement of L2 and LLC associativity is confounded on this machine,
the same "universal small-structure wall" already documented on 5 of the
other 7 team machines (see `data_raw/artemisia/README.md`'s associativity/
section): the L2 candidate (2,097,152 B) and LLC candidate (31,457,280 B) —
a 15x byte-capacity range — produced **numerically indistinguishable curves**
at every probed width from num_ways=2 through 40, which is the clean,
Phase-I-safe proof that this method cannot separate the two levels' real
associativity here, independent of which candidate byte value is used.

- **Where the confound's own wall sits on this machine is itself informative,
  and different from every other team machine so far.** The shared L2/LLC
  curve shows a soft, noisy first knee around num_ways≈5-6 (base/rep
  disagreement: L2 base=6/rep1=5/rep2=6, LLC base=rep1=rep2=6), then a clean
  flat plateau through num_ways=7-12, then a second, much sharper jump
  starting at **num_ways=13 — the exact same num_ways where this machine's
  own L1 stride (49,152 B) independently transitions**, in every run of
  both. On Sunbird/Upgrade/Charnwood, the confound's hard wall (~9-10) sat
  at a *different* number than those machines' own confirmed L1 knee (8),
  which was itself part of the evidence that the confound was a shared,
  separate structure. Here the confound's hard wall lands on the *same*
  number as L1's own knee, which is more consistent with the L2/LLC curves'
  second jump being **L1's own real signal bleeding through again** (every
  node in this method still lives on its own page, so an L1-scale
  page-indexed structure saturating at the same point regardless of the
  candidate stride is exactly what would happen if L1's real associativity,
  not some smaller unrelated structure, is what's capping these large-stride
  attempts) rather than evidence of a distinctly different confound size.
  Either way, this second jump carries no separating information about L2 or
  LLC's own associativity — it just says "not less than L1's own value."
- **L2 → 16-way.** No independent stride-scan or falsification test (the
  techniques that gave Sunbird's and Upgrade's L2 estimates more direct
  support) has been run on this machine. Absent that, the estimate rests on
  two structural arguments instead: (1) mid-level caches essentially never
  have lower associativity than L1 in real designs, so L1's own (weakly
  supported) 12-way is a floor, not a point estimate; (2) 2,097,152 B is
  itself an exact power of two, so any real associativity dividing it evenly
  into a whole number of sets must also be a power of two — 12 does not
  divide 2,097,152 evenly (S=C/(A×B) gives a non-integer 2,730.67 at 12-way),
  which is itself a small piece of evidence against 12 specifically being
  the real L2 associativity, even setting the confound aside. The smallest
  power of two at or above the L1 floor is 16, which the S=C/(A×B) check
  cleanly confirms (2,048 sets, exact). **This is a structural best guess,
  not a directly observed number** — flagged LOW confidence, doubly so given
  this machine's own capacity data doesn't even confirm 2,097,152 B is a
  real L2 boundary in the first place (see the table row's own caveat).
- **LLC → 16-way**, reported as a point estimate with no data separating it
  from the equally clean 8-way alternative. Unlike L2's capacity, ~30 MiB
  (31,457,280 B) is not a pure power of two, so — unlike L2 — the
  S=C/(A×B) integer-cleanliness check does not usefully discriminate here:
  many divisors of the byte value (8, 12, 15, 16, 20, 24, 30, ... — its
  underlying factorization is 2^21 × 3 × 5) all produce a clean integer set
  count (8-way → 61,440 sets; 12-way → 40,960; 16-way → 30,720; all exact),
  so "clean sets" is much weaker evidence at this level than it was for L2.
  16-way is presented as the point estimate mainly for internal consistency
  with the L2 guess above (nothing in this machine's data argues LLC should
  be smaller than L2, and matching them keeps the hierarchy's story simple),
  but 8-way — which happens to be the exact number Sunbird's own LLC
  reasoning also produced an alternative for, at this identical byte
  value — remains an equally plausible reading. Confidence: LOW, an
  effective point estimate rather than a resolved number, per PROJECT 1.pdf's
  explicit allowance to report a defensible number and state the limitation
  rather than leaving the cell blank.
- **Internal-consistency cross-check (PROJECT 1.pdf's S=C/(A×B)):** using
  12/16/16-way for L1/L2/LLC, derived sets are 64 / 2,048 / 30,720 — all
  clean integers, and L1→L2's set count scales by exactly 32x, matching the
  L1→L2 capacity ratio (2,097,152/49,152 ≈ 42.67, NOT a clean multiple —
  this mismatch, unlike Sunbird's exact 8x L1→L2 scaling, is itself a direct
  symptom of L2's candidate capacity not being a genuine boundary on this
  machine, not a sign the associativity guesses are wrong). LLC's own set
  count (30,720) is a clean integer at 16-way, but as noted above this
  candidate's factorization makes several other associativity guesses look
  equally clean, so this check is corroborating-but-weak evidence for LLC
  specifically, stronger evidence for L2 (where only powers of two work at
  all), and not usable as independent evidence for L1 (whose own capacity
  and associativity were both used to derive the 64-set anchor in the first
  place).

## Overall best-guess read of the hierarchy

Artemisia's cache hierarchy is best read as **48 KiB / 12-way (best guess)
L1D, a 2 MiB-candidate / 16-way (best guess) L2 whose very capacity is
itself unconfirmed by this machine's own data, and a ~30 MiB / 16-way (best
guess, 8-way an equally plausible alternative) LLC**, all sharing the same
64 B line size (confirmed at L1, best-supported but not offset-invariance-
clean at L2, unmeasured at LLC). The inclusion/exclusion picture is the
strongest, cleanest part of this machine's Phase I dataset: **both
LLC-involving pairings came back a decisive 100% invalidated-like on target
with 0% ambiguous** — cleaner splits than Sunbird produced for the
equivalent pairings — supporting a confident read that this machine's LLC is
**inclusive of both L1's and L2's resident lines**, consistent with an
inclusive, cross-core snoop-filter-style LLC design. The one piece left
genuinely open is **L1's own relationship to L2**: the `L1_vs_L2` inclusion
test came back mostly ambiguous rather than a clean call, most likely
because it inherited this machine's oversized, unconfirmed L2 capacity
candidate as its eviction-footprint scale (8x the DTLB pressure Sunbird's
equivalent, confirmed-capacity pairing carried) — this is the one field on
this table that would most benefit from being redone with a corrected L2
eviction footprint if a genuine L2 capacity boundary is ever established for
this machine. As with Sunbird, the associativity values above are the most
defensible point estimates available given a real, well-documented
measurement confound, not directly observed facts — and here, uniquely,
even the L2 row's underlying capacity value carries an extra layer of
this-machine-specific uncertainty on top of that.
