# Cycling PR stack readiness

Status: **published as five official drafts** (selector opened 2026-10-28, split
completed 2026-10-29), with independent motor-access draft
[#14054](https://github.com/organicmaps/organicmaps/pull/14054) added 2026-10-30.
PR #12692's code is protected; only review comments have
been added. Do not push its head branch (`JaredTweed:master`).

The five cycling parts retain their numbers, with an independent motor-access
prerequisite outside the numbered stack. After exact-head native validation,
the split heads were updated under explicit remote leases. Pins live in
`rollout.sh`; original PR #12692 remains unchanged.

**2026-10-30 discussion gate:** vng asked to agree the primary-road model on
[#14040](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6523827420).
The user chose to preserve #12692's appearance and keep side-offset line rendering separate.
The [response](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6524260599)
and [constraint notes](vng-model-constraints.md) separate those decisions.
The user subsequently authorized updating the split drafts while preserving
the original code and appearance. That supersedes the earlier author-side
publication hold, not the need for maintainer agreement. The selector's code
remains at `c24dc38dfe`; none of the drafts is marked ready.

**Ownership-only quality revision:** [review notes](code-quality-review.md) and
[source checks](code-quality-review.json) record the shared metaline codec/test
move to `indexer`. No classification, style, shader, geometry or phase behavior
changes are included; the phone side-offset prototype remains separate.
The updated renderer passes [298 native tests](code-quality-renderer-native-results.json)
and the exact style preview passes [295](code-quality-style-native-results.json).
The seven codec tests now run in `indexer_tests`. Earlier exact-head and
pixel-comparison records below retain their original source pins.

| # | Draft PR | Branch | Head |
| - | --- | --- | --- |
| 1 | https://github.com/organicmaps/organicmaps/pull/14040 | `prepare/cycling-selector` | `c24dc38dfe` |
| prerequisite | https://github.com/organicmaps/organicmaps/pull/14054 | `prepare/motor-vehicle-permissive` | `6daf0d8755` |
| 2 | https://github.com/organicmaps/organicmaps/pull/14041 | `prepare/cycling-tag-data` | `33c33e44b0` |
| 3 | https://github.com/organicmaps/organicmaps/pull/14048 | `prepare/cycling-metalines` | `d74a51b3cd` |
| 4 | https://github.com/organicmaps/organicmaps/pull/14042 | `prepare/cycling-dash` | `fdc131de53` |
| 5 | https://github.com/organicmaps/organicmaps/pull/14043 | `prepare/cycling-style` | `34a0624d67` |

Titles are numbered `1/5` through `5/5`, and every body carries the same stack
block with links to all five drafts.

The single publication entry point is [`rollout.sh`](rollout.sh). It is
self-contained: pins, PR titles, and PR bodies live inside it. The `*-pr-body.md`
files next to it are generated copies (`rollout.sh --dump-bodies DIR`) and are
checked against the script by the tests.

## The stack

| # | Branch on `JaredTweed/organicmaps` | Head | PR base | Target | Draft |
| - | --- | --- | --- | --- | --- |
| 1 | `prepare/cycling-selector` | `c24dc38dfe` | `master` | `organicmaps/organicmaps` | yes |
| 2 | `prepare/cycling-tag-data` | `33c33e44b0` | `master` | `organicmaps/organicmaps` | yes, cumulative |
| 3 | `prepare/cycling-metalines` | `d74a51b3cd` | `master` | `organicmaps/organicmaps` | yes, cumulative |
| 4 | `prepare/cycling-dash` | `fdc131de53` | `master` | `organicmaps/organicmaps` | yes, cumulative |
| 5 | `prepare/cycling-style` | `34a0624d67` | `ab/cycling-style` | `organicmaps/organicmaps` | yes |

`prepare/cycling-style-base` is a byte-for-byte mirror of upstream
`ab/cycling-style` at `7af82a316a` and is kept for provenance.

All five PRs are on the official repository. Parts 2-4 target `master` and are
**cumulative** because the fork cannot host stack base branches: 2/5 contains
part 1, 3/5 contains parts 1-2, and 4/5 contains parts 1-3. Part 5 targets the
existing `ab/cycling-style` branch. The earlier fork drafts are obsolete; the
official PRs are the review units.

## What each step contains

1. **Selector.** `ParseSelector` receives the `Classificator`; drawing rules can
   use `extra_tag=<type>=<path>` and `extra_tag!=<type>=<path>`. Nested types
   match by truncation. Invalid selectors are rejected. No generated rule on
   the pinned baseline uses `extra_tag`, so no existing rule is intended to
   change rendering. This is not a general zero-risk guarantee.
2. **Cycling types.** Adds `cyclewaytag|track`, `lane`, and `shared_lane` while
   keeping the road's main `highway` type. Includes access/direction refinements
   matching #12692. The order-invariance fix is a separate follow-up. The
   PR keeps the incremental classification history. Generated classifier assets
   now accompany the first commit that consumes the types. Shared lane checkers
   belong here. The unrelated permissive motor-access fix is an independent,
   exact prerequisite commit rather than a hidden line in a cycling commit.
3. **Metalines offsets.** Retains version-1 `metalines`, adding optional
   version-3-layout `metalines_offsets`, one double offset per feature;
   unnamed painted lanes/shared lanes are added to metalines in separate
   chains. Grouping and collector layout preserve #12692; collision-free
   tagged keys are a separate behavioral follow-up. The reader explicitly
   consumes v2 float offsets and v3 doubles; v1 has no offsets. Optional data is
   validated against every authoritative feature/direction list before any
   offsets are applied. The renderer does not use offsets yet.
4. **Continuous dash phase.** Uses the stored offsets and geometry direction in
   line geometry, clipping, and shaders; the Vulkan pack is regenerated. Only
   patterned cycling infrastructure is phased. No color, width, or style change.
5. **Style preview.** The cycling style from #12692 replayed on parts 1-4. This is
   a visual preview, not a merge candidate; its base is a maintainer branch.

## Earlier published-revision evidence

| Step | Evidence |
| --- | --- |
| 1 | Full `indexer_tests` debug suite on a clean build of the exact branch. The debug run caught two fixture bugs, fixed in `6f9330d5c0`; `c24dc38dfe` only fixes clang-format. |
| 2 | `generator_tests --filter=OsmType` and the full `routing_common_tests` debug suite. The new order-invariance test failed before the fix and passes after it. The branch keeps the seven original incremental commits; its tree is identical to the commit the tests ran on. |
| 3 | Published-revision Debug-assertion build of generator and renderer tests; all 10 `Metalines` tests, all 3 `MetalineData` tests and the complete `OsmType` group pass. New fixtures exercise actual collector round trips and v1/v2/v3 decoding. Earlier full `indexer_tests` evidence is from the prior revision. |
| 4 | Rebuilt `drape_frontend_tests` at `3d77a89925` with Debug assertions under the memory cap. All 16 clipping tests, both dash-phase tests and all 3 reader tests pass. Prior phone spot checks are not a visual-equivalence proof for this revision. |
| 5 | Earlier full `indexer_tests` debug suite on the preview branch. Style assets were kept unchanged; code also includes the split stack's selector, generator and metalines fixes. The appearance checklist below is still open. |

A real-generator comparison on the same road-only Vancouver extract retained
82,785 features in both builds. The MWM grew from 2,383,926 to 2,387,686 bytes
(+3,760, 0.16%). The candidate added 787 `lane`, 963 `shared_lane`, and 108
`track` type occurrences. Aggregate `hwtag`/`psurface` counts were unchanged
except two additional `hwtag|yescar` occurrences, explained by the
`motor_vehicle=permissive` handling. Counts are aggregate, not matched features;
they do not prove per-road routing correctness. Raw data is in
[`actual-generator-results.json`](actual-generator-results.json).

The six-draft kit passes publication preflight against upstream `f1b50dbcb5`:
ancestry, DCO, whitespace, protected refs and upstream source-overlap checks.
Rewritten preparation refs were pushed atomically with exact remote leases;
the rollout script itself never force-pushes. All six drafts are published.

## Candidate evidence

### Appearance-preserving revision

The newer baseline excludes two behavioral fixes that the earlier
candidate bundled with extraction: conflicting `cycleway=no`/side-tag
precedence and collision-free chain keys. Their follow-up branches are
`prepare/cycling-order-followup` (`9e7915de8d`) and
`prepare/cycling-chain-key-followup` (`9990d07b85`). Neither is part of the
ordered equivalence baseline or its publication steps.

New heads are types `33c33e44b0`, optional metalines `30ebe4827d`,
renderer `45b08c9aa7`, and style preview `82b6f69887`. On the style preview,
classification logic and chain grouping match #12692; only the additive
metalines compatibility work differs in the generator. Runtime code/assets
are unchanged from the earlier candidate. Its rebuilt Android native library
is byte-identical to that earlier candidate, with fresh source provenance.

The Pixel is now connected. Original-reference captures across five sites,
three zooms, two themes and OpenGL/Vulkan are complete, with repeated
cold starts. Cameras are normalized only by the original reference, then
shared unchanged with the candidate. The completed 60-view phone comparison
has 11 exact cross-build pairs and no cross-build differences among pairs
stable in both builds. Only 10 original and 11 candidate views repeat exactly;
maximum cross-build difference is 289/1,219,096 pixels. Strict certification
remains false. One system-overlay-contaminated case was recaptured in full,
with the substitution recorded and original evidence preserved. See
[visual-phone-results.json](visual-phone-results.json).
All matched features/chains pass in [visual-equivalence-baseline-data.json](visual-equivalence-baseline-data.json).
The exact revised master and style heads pass 296 and 293 native tests:
[master results](equivalence-master-native-results.json),
[style results](equivalence-style-native-results.json). All 73 research tests pass.
The old evidence below remains historical evidence, not an exact-head test
claim for these newer revisions.

- Independent motor-access branch `6daf0d8755` builds and passes the full
  `OsmType` group. The first usable cycling commit `532f644147` also builds
  and passes that group with its classifier assets present.
- The exact master-based renderer head `29834257a1` passes 299 native tests:
  68 selected generator tests, 23 selected reader/clipping/phase tests, the
  full 181-test indexer suite and the full 27-test routing-common suite.
  Binary/log hashes are in [native-check-results.json](native-check-results.json).
- The exact style candidate `f8f603fc7e` independently builds and passes its
  classification, metalines and reader/clipping/phase groups. Exact original
  and candidate Android and Qt native builds also succeed.
- All 66 research/launcher tests pass, including API-error/ambiguous-PR
  publication refusal, protected-ref guards, semantic feature matching,
  complete source identities, stored type order, camera/map binding and strict
  pixel comparison. A small pixel difference is detected, not tolerated away.
- [visual-validation.md](visual-validation.md) records the detailed matched-map
  and rendered-image results. All 82,785 features have source identities and
  match, with the same 2,010 directed chains/offsets. Full tracked data/style
  trees match. This does not erase the remaining pixel discrepancies.
- Of 60 fixed-camera Qt views, 36 match cross-build exactly; 23 are also stable
  within both builds. One stable pair differs by 17 grayscale road-edge pixels.
  That strict visual-equivalence result remains false. Pixel/Vulkan coverage
  was absent in that earlier report; the new phone run is recorded separately.
  Generated-route tests remain open.

Local review ranges (not claims of isolated public GitHub diffs):

| Unit | Range |
| --- | --- |
| Selector | `303ef27fbc..c24dc38dfe` |
| Independent access | `303ef27fbc..6daf0d8755` |
| Cycling types, after both prerequisites | `407057c693..33c33e44b0` |
| Optional metaline data | `33c33e44b0..30ebe4827d` |
| Renderer | `30ebe4827d..45b08c9aa7` |
| Complete style preview, including dependencies | `7af82a316a..82b6f69887` |

## Known open questions for review

The revision rationale and explicit merge gates are in [design-review.md](design-review.md).

- Side-specific facilities: proposed deferral for this stack, not an approval
  from vng. The centerline summary still needs maintainer acceptance.
- The eight-type limit: aggregate dumps matched on the Vancouver extract. This
  does not establish per-feature or pixel equality. Measure displaced access,
  direction and surface types before changing cycling retention priority.
- `motor_vehicle=permissive`: the cycling style needs it for shared-space ways,
  but it also changes two pedestrian/sidewalk classifications in the test extract.
- The candidate fixes whole-section v3 rejection by retaining a v1 main
  section and separate optional offsets. The emitted legacy layout and resolved
  offsets are audited. This is not a blanket historical-client compatibility
  result; the duplicate data costs about 1.1% on this test map.
- Whether the style preview should merge into `ab/cycling-style` or wait for that branch to reach `master`.

## Review answers (vng)

The response is posted in
[#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

- **Model:** keep the road's main type plus one `cyclewaytag`; classifier types
  now, a richer binary feature section only if side-specific or pedestrian data
  becomes a committed requirement.
- **Visuals:** one conservative centerline category per road. Per-side rendering
  and per-side directions are deferred. Preserving solid/dashed/dotted styling
  is the objective, not a verified pixel-equivalence result.
- **Eight-type cap:** a local retention variant produced the same set of
  `cyclewaytag` combinations on the Vancouver extract (209 type-dump lines).
  Aggregate equality cannot rule out changes on individual roads. The current
  ranking stays pending per-feature measurements; other regions are not measured.
- **Routing:** PR 2/5 refines access/direction flags as well as display types.
  Style consumers, classifier retention and routing can interact. End-to-end
  route-graph tests remain a gate. The independent `motor_vehicle=permissive`
  change is now extracted locally; the final preview retains it, so extraction
  does not silently change shared-space appearance.
- **Pedestrians:** a separate follow-up, not part of this stack.

## Publishing

Do not publish while the primary-road discussion gate is open. These commands
document the eventual workflow; the candidate kit currently rejects the old
remote heads and cannot overwrite them automatically.

```bash
cd docs/cycling-tag-audit
./rollout.sh --check                     # read-only, default
PUBLISH_CYCLING_STACK=YES ./rollout.sh --publish
./rollout.sh --verify
```

`--publish` fails closed if:

- a branch tip differs from its pin, or a fork branch would be overwritten;
- `ab/cycling-style` moved;
- a source file touched by a stack PR changed on `master` since its base;
- an existing PR is not one of our open drafts, or its base/head moved;
- the target is PR #12692.

It pushes only branches that do not exist yet, creates only new draft PRs, and
records them in `~/.local/state/organicmaps-cycling-rollout/state.tsv`. Existing
titles and bodies are left alone unless `UPDATE_PR_TITLES=YES` and/or
`UPDATE_PR_BODIES=YES` is set.

To undo a publish before review starts:

```bash
ROLLBACK_CYCLING_STACK=YES ./rollout.sh --rollback
```

Rollback closes only the drafts recorded in the state file, only if they are
still open drafts, and never deletes branches.

## Remaining gates before any PR leaves draft

- Device screenshots for step 5 at several zoom levels in light and dark themes,
  on the same roads used for #12692.
- End-to-end bicycle route tests on generated graphs for step 2, not just unit
  suites.
- A decision on the `motor_vehicle=permissive` side effect.
- Maintainer-approved upstream CI on the reviewed heads; local tests do not
  substitute for GitHub workflow approval or maintainer review.

## Promotion path after review

All five are already official drafts. Parts 2-4 are cumulative because their
clean bases are fork-only. As each step is accepted:

1. Merge part 1.
2. Rebase `prepare/cycling-tag-data` onto the new `master`. Its 2/5 diff then
   contains only the cycling types; check that no new classifier IDs were
   appended and retest.
3. Rebase `prepare/cycling-metalines` onto the accepted types head. Its 3/5 diff
   then contains only the format change; review the metalines compatibility
   decision separately.
4. Rebase `prepare/cycling-dash` onto the accepted metalines head. Its 4/5 diff
   then contains only the renderer phase.
5. Rebase the style work onto `ab/cycling-style` (or `master` once that lands),
   regenerate the rules, and verify the visual checklist before merging. Do not
   merge the preview as-is.

After each rebase the cumulative official diff shrinks to that part's own
changes. `rollout.sh --check` fails if `master` changes a file a stack PR edits,
so an upstream ID append or a renderer change blocks publication until the
branch is rebased and retested.

## Notes

- Classifier IDs are assigned relative to each branch's base. On current
  `master` the cycling types are `1660-1662`; on the older `ab/cycling-style`
  base they are `1658-1660`. This is why the style preview cannot be squashed
  blindly into the stack: after the types land, the style branch must be rebased
  and its generated rules regenerated once.
- A first phone preview mixed a map generated on `master` (IDs `1660-1662`) with
  the preview app's rules (IDs `1658-1660`). The rules then matched the wrong
  types, so Cambie Street lost its lane dashes and only a few shared/track
  segments rendered. Regenerating the map from the preview branch fixed it:
  track is solid, lane is dashed, shared_lane is dotted. Never test the preview
  with a map generated from a different branch's classifier.
- A separate, unmodified local branch `feature/bicycle-routing-improvements`
  also adds bicycle types (`hwtag|bicycle_access`, `cyclewaytag|*`,
  `hwtag|bicycle_ramp`) on an August base. It was not touched. If revived, its
  IDs will collide with the current stack and must be renumbered.
- The earlier experimental `prepare/cycling-kothic` branch in the Kothic fork is
  not part of this stack; the style preview uses the Kothic revision already
  pinned by `ab/cycling-style`.
