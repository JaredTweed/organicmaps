# Cycling PR stack readiness

Status: **prepared, not published**. No pull request was created, edited, closed,
or commented on while building this kit. PR #12692 is untouched and the rollout
script has a hard guard against ever targeting it.

The single publication entry point is [`rollout.sh`](rollout.sh). It is
self-contained: pins, PR titles, and PR bodies live inside it. The `*-pr-body.md`
files next to it are generated copies (`rollout.sh --dump-bodies DIR`) and are
checked against the script by the tests.

## The stack

| # | Branch on `JaredTweed/organicmaps` | Head | PR base | Target | Draft |
| - | --- | --- | --- | --- | --- |
| 1 | `prepare/cycling-selector` | `6f9330d5c0` | `master` | `organicmaps/organicmaps` | yes |
| 2 | `prepare/cycling-tag-data` | `8e641f3e90` | `prepare/cycling-selector` | `JaredTweed/organicmaps` | yes |
| 3 | `prepare/cycling-dash` | `352e040b4c` | `prepare/cycling-tag-data` | `JaredTweed/organicmaps` | yes |
| 4 | `prepare/cycling-style` | `ca0586974c` | `prepare/cycling-style-base` | `JaredTweed/organicmaps` | yes |

`prepare/cycling-style-base` is a byte-for-byte mirror of upstream
`ab/cycling-style` at `7af82a316a` and exists so the style preview has a base
inside the fork.

Step 1 is the only upstream PR: a self-contained selector capability with no new
types and no MWM format change. Steps 2-4 are fork review PRs because GitHub's
native stacked PRs do not work across forks and the author has read-only access
to `organicmaps/organicmaps`.

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
3. **Dash phase.** Metalines section version 1 -> 3, one double dash-phase offset
   per feature (8 bytes per chained feature); readers accept 1-3. Continuous phase across adjacent ways, limited
   to patterned cycling infrastructure. Vulkan shader pack regenerated.
4. **Style preview.** The cycling style from #12692 replayed on the selector and
   cycling-type work. This is a visual preview, not a merge candidate; its base
   is a maintainer branch.

## Verification performed

| Step | Evidence |
| --- | --- |
| 1 | Full `indexer_tests` debug suite on a clean build of the exact branch. The debug run caught two fixture bugs, fixed in `6f9330d5c0`. |
| 2 | `generator_tests --filter=OsmType` and the full `routing_common_tests` debug suite. The new order-invariance test failed before the fix and passes after it. The branch keeps the seven original incremental commits; its tree is identical to the commit the tests ran on. |
| 3 | Clean debug build of `generator_tests` and `drape_frontend_tests`; metalines and clip-splines suites. Rebased onto the cycling-types head after the history change; tree identical to the tested commit. |
| 4 | Full `indexer_tests` debug suite passes on the preview branch itself. Sources are identical to #12692 except the selector and generator commits, both also verified above. The appearance checklist below is still open. |

A real-generator comparison on the same road-only Vancouver extract retained
82,785 features in both builds. The MWM grew from 2,383,926 to 2,387,686 bytes
(+3,760, 0.16%). The candidate added 787 `lane`, 963 `shared_lane`, and 108
`track` type occurrences. Aggregate `hwtag`/`psurface` counts were unchanged
except two additional `hwtag|yescar` occurrences, explained by the new
`motor_vehicle=permissive` handling. Counts are aggregate, not matched features;
they do not prove per-road routing correctness. Raw data is in
[`actual-generator-results.json`](actual-generator-results.json).

`rollout.sh --check` passed against the live repository on 2026-10-28, with
upstream `master` at `1b9a011b` and no existing PR for any stack branch.

## Known open questions for review

- Side-specific facilities: one centerline summary today; is that enough before
  separate left/right rendering and routing are added?
- The eight-type limit: `cyclewaytag` is registered in `UselessTypesChecker`, so it can be dropped on type-heavy roads. Should lane rendering outrank `hwtag`/`psurface` types instead?
- `motor_vehicle=permissive`: the cycling style needs it for shared-space ways,
  but it also changes two pedestrian/sidewalk classifications in the test extract.
- Metalines v3: version-1 readers reject the whole section, so merged-line labels and shields fall back to per-feature placement on all new maps. Is an append-only extension better than the version bump?
- Whether the style PR should eventually target `ab/cycling-style` directly.

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
records them in `~/.local/state/organicmaps-cycling-rollout/state.tsv`. It does
not edit existing PR bodies unless `UPDATE_PR_BODIES=YES` is set.

To undo a publish before review starts:

```bash
ROLLBACK_CYCLING_STACK=YES ./rollout.sh --rollback
```

Rollback closes only the drafts recorded in the state file, only if they are
still open drafts, and never deletes branches.

## Remaining gates before any PR leaves draft

- Device screenshots for step 4 at several zoom levels in light and dark themes,
  on the same roads used for #12692.
- End-to-end bicycle route tests on generated graphs for step 2, not just unit
  suites.
- A decision on the `motor_vehicle=permissive` side effect.
- Upstream CI on step 1 once the draft exists.

## Promotion path after review

The fork PRs are for review visibility, not for merging. As each step is
accepted:

1. Merge the selector PR upstream.
2. Rebase `prepare/cycling-tag-data` onto the new `master`, check that no new
   classifier IDs were appended, retest, and open it upstream.
3. Rebase `prepare/cycling-dash` onto the accepted cycling-types head and open it
   upstream. The metalines version change still needs its own compatibility
   review.
4. Rebase the style work onto `ab/cycling-style` (or `master` once that lands),
   regenerate the rules, and verify the visual checklist before opening a final
   style PR. Do not reuse the preview branch as-is.

`rollout.sh --check` fails if `master` changes a file a stack PR edits, so an
upstream ID append or a renderer change blocks publication until the branch is
rebased and retested.

## Notes

- Classifier IDs are assigned relative to each branch's base. On current
  `master` the cycling types are `1660-1662`; on the older `ab/cycling-style`
  base they are `1658-1660`. This is why the style preview cannot be squashed
  blindly into the stack: after the types land, the style branch must be rebased
  and its generated rules regenerated once.
- A separate, unmodified local branch `feature/bicycle-routing-improvements`
  also adds bicycle types (`hwtag|bicycle_access`, `cyclewaytag|*`,
  `hwtag|bicycle_ramp`) on an August base. It was not touched. If revived, its
  IDs will collide with the current stack and must be renumbered.
- The earlier experimental `prepare/cycling-kothic` branch in the Kothic fork is
  not part of this stack; the style preview uses the Kothic revision already
  pinned by `ab/cycling-style`.
