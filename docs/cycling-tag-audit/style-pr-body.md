## Preview only — not for merge as-is.

Applies the cycling style to the new `cyclewaytag` types while preserving the current solid, dashed, and dotted presentation.

This draft exists so the appearance can be reviewed against the intended data model. It is based on `ab/cycling-style` plus the selector, cycling-types, and dash-phase PRs, because the cycling style itself is not on `master` yet.

## What to review

- Same roads at the same zoom levels and themes should keep the same solid/dashed/dotted appearance as #12692.
- Direction arrows and shared-lane dots should follow the additional types rather than replacing the road type.
- The generator and selector parts are already split into their own PRs; only the style delta is new here.

## Open questions

- Whether the final style PR should target `ab/cycling-style` directly after the generator work lands.
- Whether side-specific facilities need separate rendering before this is merged.
- How the classifier-type limit should be handled when a road already carries many types.

Do not merge: the base branch is a maintainer branch mirror and the visual checklist above is not complete.
