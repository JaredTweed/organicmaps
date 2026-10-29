## Preview only — not for merge as-is.

Applies the cycling style to the new `cyclewaytag` types while preserving the current solid, dashed, and dotted presentation.

This draft exists so the appearance can be reviewed against the intended data model. It is based on `ab/cycling-style` plus parts 1-4.

This upstream PR targets `ab/cycling-style` and also contains parts 1-4. Review the `[styles]` commits.

## What to review

- Same roads at the same zoom levels and themes should keep the same solid/dashed/dotted appearance as #12692.
- Direction arrows and shared-lane dots should follow the additional types rather than replacing the road type.
- The diff against this base includes parts 1-4 because the preview depends on them; review the `[styles]` commits and the screenshots.
- The selector and generator changes pass the full `indexer_tests` suite on this branch.
- Generate the preview map from this branch or its `ab/cycling-style` base, not from `master`. `cyclewaytag` is allocated as 1658-1660 here and 1660-1662 on current `master`; a master-generated map makes these rules match the wrong types, so lane/track/shared styling looks inconsistent.

## Open questions

- When to add side-specific rendering as a follow-up.
- Whether other regions lose `cyclewaytag` at the eight-type cap; Vancouver did not.

Do not merge: the base branch is a maintainer branch mirror and the visual checklist above is not complete.

## Scope

- Centerline style only; side-specific facilities are deferred.
- The type-cap experiment on the Vancouver extract showed no visual change; the current ranking stays.
- Answers to @vng's questions: [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

## Stack

Part 5 of 5, in review order:

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. **organicmaps#14043 — cycling style preview (this PR)**
