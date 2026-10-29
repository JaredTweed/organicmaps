# Cycling PR stack readiness

Status: **published as five official drafts** (selector opened 2026-10-28, split
completed 2026-10-29). PR #12692 was not modified.

| # | Draft PR | Branch | Head |
| - | --- | --- | --- |
| 1 | https://github.com/organicmaps/organicmaps/pull/14040 | `prepare/cycling-selector` | `c24dc38dfe` |
| 2 | https://github.com/organicmaps/organicmaps/pull/14041 | `prepare/cycling-tag-data` | `0a9b94bcef` |
| 3 | https://github.com/organicmaps/organicmaps/pull/14048 | `prepare/cycling-metalines` | `aff18a6bda` |
| 4 | https://github.com/organicmaps/organicmaps/pull/14042 | `prepare/cycling-dash` | `e9e62a1618` |
| 5 | https://github.com/organicmaps/organicmaps/pull/14043 | `prepare/cycling-style` | `22f7af8d9d` |

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
| 2 | `prepare/cycling-tag-data` | `0a9b94bcef` | `master` | `organicmaps/organicmaps` | yes, cumulative |
| 3 | `prepare/cycling-metalines` | `aff18a6bda` | `master` | `organicmaps/organicmaps` | yes, cumulative |
| 4 | `prepare/cycling-dash` | `e9e62a1618` | `master` | `organicmaps/organicmaps` | yes, cumulative |
| 5 | `prepare/cycling-style` | `22f7af8d9d` | `ab/cycling-style` | `organicmaps/organicmaps` | yes |

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
   `master` currently uses `extra_tag`, so activating it cannot change existing
   rendering.
2. **Cycling types.** Adds `cyclewaytag|track`, `lane`, and `shared_lane` while
   keeping the road's main `highway` type. Includes access/direction refinements
   and an order-invariance fix for `cycleway=no` plus a positive side value. The
   PR keeps the seven original incremental commits instead of squashing them.
3. **Metalines offsets.** Metalines section version 1 -> 3, one double offset per
   feature; unnamed painted lanes/shared lanes are added to metalines in separate
   chains. Shared `ftypes` checkers and stable chain keys replace duplicated type
   paths and `std::hash`; the dead version-2 reader is removed. The renderer does
   not use the offsets yet.
4. **Continuous dash phase.** Uses the stored offsets and geometry direction in
   line geometry, clipping, and shaders; the Vulkan pack is regenerated. Only
   patterned cycling infrastructure is phased. No color, width, or style change.
5. **Style preview.** The cycling style from #12692 replayed on parts 1-4. This is
   a visual preview, not a merge candidate; its base is a maintainer branch.

## Verification performed

| Step | Evidence |
| --- | --- |
| 1 | Full `indexer_tests` debug suite on a clean build of the exact branch. The debug run caught two fixture bugs, fixed in `6f9330d5c0`; `c24dc38dfe` only fixes clang-format. |
| 2 | `generator_tests --filter=OsmType` and the full `routing_common_tests` debug suite. The new order-invariance test failed before the fix and passes after it. The branch keeps the seven original incremental commits; its tree is identical to the commit the tests ran on. |
| 3 | `generator_tests --filter=Metalines`, full `indexer_tests`, and clip-splines tests pass on a clean build. |
| 4 | Clean debug build of `drape_frontend_tests`; clip-splines and reversed-metaline phase tests pass. Phone preview keeps solid/dashed/dotted styling. |
| 5 | Full `indexer_tests` debug suite on the preview branch. Sources are identical to #12692 except the selector/generator fixes. The appearance checklist below is still open. |

A real-generator comparison on the same road-only Vancouver extract retained
82,785 features in both builds. The MWM grew from 2,383,926 to 2,387,686 bytes
(+3,760, 0.16%). The candidate added 787 `lane`, 963 `shared_lane`, and 108
`track` type occurrences. Aggregate `hwtag`/`psurface` counts were unchanged
except two additional `hwtag|yescar` occurrences, explained by the
`motor_vehicle=permissive` handling. Counts are aggregate, not matched features;
they do not prove per-road routing correctness. Raw data is in
[`actual-generator-results.json`](actual-generator-results.json).

`rollout.sh --check` passes against the live repository with upstream `master`
at `44f481bbf3` and all five drafts present.

## Known open questions for review

- Side-specific facilities: deferred for this stack; the centerline summary is
  the agreed first step, with left/right rendering as a follow-up.
- The eight-type limit: a retention experiment on the Vancouver extract showed
  no change; other regions still need measuring before deciding whether to
  reserve the type.
- `motor_vehicle=permissive`: the cycling style needs it for shared-space ways,
  but it also changes two pedestrian/sidewalk classifications in the test extract.
- Metalines v3: version-1 readers reject the whole section, so merged-line labels and shields fall back to per-feature placement on all new maps. Is an append-only extension better than the version bump?
- Whether the style preview should merge into `ab/cycling-style` or wait for that branch to reach `master`.

## Review answers (vng)

The response is posted in
[#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

- **Model:** keep the road's main type plus one `cyclewaytag`; classifier types
  now, a richer binary feature section only if side-specific or pedestrian data
  becomes a committed requirement.
- **Visuals:** one conservative centerline category per road. Per-side rendering
  and per-side directions are deferred, so the current solid/dashed/dotted look
  is preserved.
- **Eight-type cap:** a local retention variant produced the same set of
  `cyclewaytag` combinations on the Vancouver extract (209 type-dump lines) and
  no visual change. The current ranking stays; other regions are not measured.
- **Routing:** PR 2/5 refines access/direction flags; the style consumes only
  `yescar`/`onedir`; routing-only attributes stay out of the style. End-to-end
  route-graph tests remain a gate.
- **Pedestrians:** a separate follow-up, not part of this stack.

## Publishing

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
- Upstream CI on step 1 once the draft exists.

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
