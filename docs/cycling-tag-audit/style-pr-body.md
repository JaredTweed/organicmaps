## Preview only — not for merge as-is.

Applies the cycling style to the new `cyclewaytag` types, with preservation of #12692's solid, dashed, and dotted presentation as the validation objective.

This draft exists so the appearance can be reviewed against the intended data model. It is based on `ab/cycling-style` plus parts 1-4.

This upstream PR targets `ab/cycling-style` and also contains parts 1-4 plus the independent permissive-motor-access prerequisite. Review the `[styles]` commits; this is not an isolated style-only GitHub diff.

## What to review

- Same roads at the same zoom levels and themes should keep the same solid/dashed/dotted appearance as #12692.
- Direction arrows and shared-lane dots should follow the additional types rather than replacing the road type.
- The diff against this base includes parts 1-4 because the preview depends on them; review the `[styles]` commits and the screenshots.
- Earlier `indexer_tests` passed on the preview; new revisions need their own applicable checks before merge.
- Exact baseline/candidate Android native builds succeed. The complete tracked `data/` trees match. Separately generated Vancouver maps match all 82,785 features (including stored type order and metadata) and all 2,010 directed chains/offsets using isolated, explicitly verified classifiers. Aggregate type counts are not used as the proof.
- On exact candidate `82b6f69887`, 293 native tests pass with Debug assertions: 62 classification/metalines tests, 23 reader/clipping/phase tests, 181 indexer tests and 27 routing-common tests. This is not generated-route or pixel-equivalence evidence.
- The earlier Qt/OpenGL audit had a stable-pair discrepancy of 17 grayscale road-edge pixels; it remains archived, not erased by the new phone result.
- Completed Pixel OpenGL/Vulkan audit: 60 saved-camera views, both themes and repeated cold starts. Eleven cross-build pairs are exact; the reference repeats exactly in 10 views and the candidate in 11. No pair stable in both builds differs cross-build. Maximum difference is 289/1,219,096 map pixels (about 0.024%). Strict pixel equivalence remains unverified; no tolerance was introduced. One volume-panel-contaminated case was recaptured in full with identical settings and explicit provenance, preserving the raw evidence.
- Generate preview maps from this branch with its matching classifier and renderer format. On these pinned branches, the cycling entries occupy lines 1658-1660 of `types.txt` here (stored indices 1657-1659), versus lines 1660-1662 on the master-based types branch (stored indices 1659-1661). Mismatched app/map mappings already caused incorrect lane/track/shared rendering in a preview. The base branch alone does not supply the added types.

## Open questions

- When to add side-specific rendering as a follow-up.
- Whether individual roads lose `cyclewaytag` at the eight-type cap; aggregate Vancouver dumps do not resolve this.

Do not merge as-is: the base is the maintainer's `ab/cycling-style` branch, dependencies remain cumulative, and the visual checklist above is not complete.

## Scope

- Centerline style only; side-specific facilities are deferred.
- Conflicting-tag order and collision-free chain grouping are separate behavioral follow-ups, excluded to preserve #12692's classification and grouping logic.
- This old-base preview does not certify the eventual merged-master integration. Rebase/regenerate and repeat the comparison on that actual integration before claiming final equivalence; do not silently revert unrelated upstream work to match an older baseline.
- The type-cap experiment produced equal aggregate type-combination dumps on the Vancouver extract, not a per-road or pixel-equivalence proof. The current ranking stays pending matched-feature measurements.
- Answers to @vng's questions: [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

## Stack

Part 5 of 5, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. **organicmaps#14043 — cycling style preview (this PR)**
