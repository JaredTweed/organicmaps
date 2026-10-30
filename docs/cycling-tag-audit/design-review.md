# Cycling stack design review

## Protected original

Do not push `JaredTweed:master`, the head of upstream PR #12692. Its recorded
head before this work is `955cd49403ed025c24beec09f5551e8d274a38ff`.
Changes belong only on the split preparation branches and research branch.

The 2026-10-30 [primary-road constraint discussion](vng-model-constraints.md)
is not a maintainer approval. The user chose to preserve #12692's appearance,
keep side-offset line rendering in a separate proposal/prototype, and subsequently authorized
updates to the split drafts. Candidate changes remain local until their
validation is complete; author permission does not imply vng's agreement.

## Decisions for this revision

- Keep selector, generator, stored phase data and renderer as distinct review
  units. The format PR must read its output without needing the renderer PR.
- Keep the five existing drafts rather than renumbering before maintainer review.
  Official parts 2-4 are cumulative against master, not isolated GitHub diffs.
  Review commit ranges; rebase each onto master after its predecessors land.
- Keep the style PR explicitly a non-merge preview. Identical style assets do
  not prove identical output: classifier mapping, feature retention and geometry
  all participate in rendering.
- Preserve centerline categories, colors, widths, casings, arrows and phase
  behavior. No side-aware rendering or type-retention reprioritization here.
- Keep conflicting-tag order and collision-free grouping fixes outside the
  baseline. Both can alter generated output on edge cases even when one map
  happens to match. See [behavioral-followups.md](behavioral-followups.md).
- Extract `motor_vehicle=permissive` into an independent prerequisite, with
  specific access/override tests and no cycling classifier dependency. Merge
  that exact commit into the types branch; do not duplicate or silently drop
  its behavior. Routing reviewers must accept its semantics before merge.
- Put lane/shared-lane classifier checkers in the types PR. Include generated
  classifier assets in the first commit that consumes the new types, not in a
  delayed regeneration commit after several runtime changes.
- Preserve version-1 `metalines`; place phase offsets in a separate optional
  section. Validate complete feature/direction correspondence before applying
  any offsets. Stale or damaged optional data must not discard legacy labels.

## Concrete defects addressed

- Accepting v2 without reading its interleaved floats desynchronizes the
  metalines stream. Explicit v1/v2/v3 decoding and multi-chain fixtures guard
  version widths, feature IDs, reversal and truncated-offset handling.
- Fixed unnamed-chain integers can collide with named-road hashes. An ordered
  `(kind, name, ref)` tuple is prepared as a separate follow-up, not part of
  the equivalence baseline. It changes collector files and potentially chain
  output; a separate regeneration and appearance review is required.

## Required evidence before merge

- Match generated features by OSM identity and segment geometry, not just
  aggregate type counts. Measure whether retaining cycling displaces access,
  direction or surface attributes. Equal combination counts can conceal swaps.
- Record exact app commit, generator commit, map hash and app/map classifier
  mappings for every visual fixture. A mapping mismatch already caused missing
  cycling treatments in an earlier preview.
- Compare fixed coordinates and zooms for track, lane, shared lane and mixed
  sides; include light/dark, clipped tiles, reversed chains, intersections and
  each supported graphics backend. Record diffs rather than inferring equality
  from style-source hashes.
- Exercise generated bicycle routes for forward/reverse access, contraflow,
  positive-side versus whole-road-negative tags, permissive motor access and
  pedestrian/sidewalk cases. Classification unit tests alone are insufficient.
- The chosen additive format emits a version-1 main section and separate phase
  data, avoiding the previous whole-section v3 rejection. The exact legacy
  signed-feature layout is retained; this is not a blanket historical-app or
  classifier compatibility claim. The duplicate section costs about 1.1% on
  this extract. Historical-client smoke coverage remains separate.

These are merge gates, not claims that the stack is perfect or approved.

The style preview still targets the older `ab/cycling-style` foundation.
Current master contains unrelated intervening rendering/classification work.
An old-base preview cannot certify the eventual merged-master result: rebase,
regenerate and repeat the matched-data/camera audit on the actual integration.
Do not revert unrelated upstream changes merely to force an old screenshot
match. Any unavoidable base difference must be documented and resolved
explicitly before claiming the final integration equivalent.

## Checks for the concrete fixes

The counts below describe the earlier candidate that included the two now
separate behavioral fixes. New-baseline results must identify their actual
source heads rather than inherit those exact-head claims.

- Built `generator_tests` and `drape_frontend_tests` with Debug assertions,
  one compiler job, reduced local unity batching, and a hard 1800 MiB cgroup
  memory cap with additional swap disabled. Some library debug symbols were
  disabled locally to reduce compiler memory; no tracked build flags changed.
- All 10 `Metalines` generator tests pass, including grouping namespaces and
  the actual collector serialization/merge round trip.
- All 5 `MetalineData` tests pass on the exact style candidate, including
  multi-chain v1/v2/v3 fixtures, reverse flags, unknown versions, truncated or
  trailing optional payloads and atomic rejection of stale feature/direction/count data.
- The complete `OsmType` group passes. This is classification evidence, not
  generated-route correctness evidence.
- Built the exact style candidate `f8f603fc7e`; all 16 clipping tests, both
  dash-phase tests and all 5 reader tests pass. Its complete `OsmType` group
  includes the new independent motor-access regression.
- Research/launcher tests cover a misconfigured `master` publication ref and
  reject it before any fetch, push or PR mutation.
- Exact baseline/candidate Android native builds succeed. Every one of 82,785
  generated features and 2,010 directed chains/offsets matches in a detailed
  audit, with no ambiguous identities. The entire tracked style/data tree
  matches. [visual-validation.md](visual-validation.md) separates this evidence
  from the still-required fixed-camera screenshot comparison.

## Resource limits

Run heavy tasks sequentially with one compiler job. On this machine, swap was
already full during the audit. Use a cgroup hard memory limit and no additional
swap use; never increase parallelism or the limit to force a build through.
If a unity translation unit exceeds the cap, reduce its batching or run narrower
targets instead of risking the desktop.
