## Summary

Adds `cyclewaytag|track`, `cyclewaytag|lane`, and `cyclewaytag|shared_lane` as additional types while keeping the road's main `highway` type. Styles can then distinguish cycling infrastructure without replacing the road classification.

Draft: the access and direction changes in this PR affect bicycle routing and need review.

This upstream PR is cumulative: it contains part 1 (the selector) and an independent motor-access prerequisite. The prerequisite is merged as its own exact commit before the incremental cycling-classification commits; it is not hidden inside the display-type diff.

## What changes

- The generator classifies `cycleway*` tags into one additional centerline type. Where explicitly tagged sides/directions differ, the least-protected category wins: `shared_lane`, then `lane`, then `track`. Side-specific information is not retained.
- Keeps #12692's existing conflicting-tag precedence. An order-invariance fix for `cycleway=no` plus a positive side-specific value is a separate follow-up, because it can change classification and appearance.
- Bicycle direction and access flags are refined in the same classification pass.
- Owns the lane/shared-lane `ftypes` checkers used by the renderer, so the format PR no longer introduces classifier APIs. Baseline generator grouping remains #12692's implementation.
- Includes the generated classifier assets in the first commit consuming the new types, so intermediate commits do not depend on a later regeneration commit to load them.
- Formatting-only CI preparation uses clang-format 23; classification and rendering behavior are unchanged. This preparation was assisted by Codex.

## Compatibility

- New types are appended after the existing classifier IDs; no MWM section format change.
- No existing classifier entry is intentionally renumbered on this base. Old maps remain readable by this implementation. Historical-client handling of newly written type indices still needs a matched-map compatibility test; app and generator classifier mappings must match.

## Testing

- `generator_tests --filter=OsmType` passes on a clean debug build.
- Full `routing_common_tests` suite passes.
- On a road-only Vancouver extract, both builds retained 82,785 features; the MWM grew by 3,760 bytes (0.16%), with 787 lane, 963 shared-lane, and 108 track occurrences.
- The order-invariance regression belongs to the separate behavioral follow-up, not this equivalence baseline.

## Review notes

- The cycling style uses `hwtag=yescar` for shared-space treatment. The independent `prepare/motor-vehicle-permissive` prerequisite owns that access change and its dedicated tests, including pedestrian/sidewalk implications. The complete preview retains the behavior rather than silently removing it during extraction.
- `cyclewaytag` is registered in `UselessTypesChecker`, so it can be dropped when a feature exceeds the eight-type limit. That ordering decides whether a type-heavy road keeps its lane rendering and should be reviewed deliberately.
- Aggregate counts are not matched features. The separate research probe now exercises generated routing/access sections and the production router on controlled fixtures; this is not a broad country-specific routing audit.

## Review questions

Answers to @vng's questions in [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067):

- The stack keeps the road's main type and adds one centerline `cyclewaytag`; per-side rendering and per-side directions are deferred.
- Eight-type cap: a per-feature follow-up on the earlier retention-map pair finds unchanged complete type lists on all 1,858 cycling features. The whole maps are not certified equal (generated roundabout identities differ), and the earlier generator build pins were not archived. This is bounded evidence, not an all-regions or exact-current-head result; keep the current priority policy pending review.
- Routing: this PR still changes bicycle access/direction flags as well as display classification. Motor access is an independent prerequisite. Generated-map fixtures now cover bicycle access, ordinary/explicit/reversed one-way directions and contraflow; conflicting-tag and country-specific policy review remains. No general claim of routing/visual independence is made.
- Pedestrian reuse is a follow-up, not part of this stack.

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Stack

Part 2 of 5, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. **organicmaps#14041 — cycling types (this PR)**
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
