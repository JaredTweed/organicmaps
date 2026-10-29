## Summary

Adds `cyclewaytag|track`, `cyclewaytag|lane`, and `cyclewaytag|shared_lane` as additional types while keeping the road's main `highway` type. Styles can then distinguish cycling infrastructure without replacing the road classification.

Draft: the access and direction changes in this PR affect bicycle routing and need review.

This upstream PR is cumulative: it also contains part 1 (the selector). Review the `[generator]` commits.

## What changes

- The generator classifies `cycleway*` tags into one additional type, with `track` > `lane` > `shared_lane` precedence and side/forward/backward handling.
- `cycleway=no` combined with a positive side-specific value now resolves independently of OSM tag order; a regression test reproduces the previous bug.
- Bicycle direction and access flags are refined in the same classification pass.

## Compatibility

- New types are appended after the existing classifier IDs; no MWM section format change.
- Old maps remain readable, and old readers ignore unknown types.

## Testing

- `generator_tests --filter=OsmType` passes on a clean debug build.
- Full `routing_common_tests` suite passes.
- On a road-only Vancouver extract, both builds retained 82,785 features; the MWM grew by 3,760 bytes (0.16%), with 787 lane, 963 shared-lane, and 108 track occurrences.
- The new order-invariance regression fails before the fix and passes after it.

## Review notes

- The cycling style uses `hwtag=yescar` to render ways where motor vehicles are allowed as shared space. This PR now treats `motor_vehicle=permissive` like `yes`, so two additional `hwtag|yescar` combinations appeared on the test extract: one pedestrian way and one sidewalk. The intent is cycling-related, but the pedestrian/sidewalk side effect deserves review.
- `cyclewaytag` is registered in `UselessTypesChecker`, so it can be dropped when a feature exceeds the eight-type limit. That ordering decides whether a type-heavy road keeps its lane rendering and should be reviewed deliberately.
- Aggregate counts are not matched features; individual routing correctness still needs route-graph tests.

## Review questions

Answers to @vng's questions in [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067):

- The stack keeps the road's main type and adds one centerline `cyclewaytag`; per-side rendering and per-side directions are deferred.
- Eight-type cap: a local retention experiment on the Vancouver extract produced the same set of `cyclewaytag` combinations (209 type-dump lines), so the cap did not change the look there. The current ranking stays; other regions still need measuring.
- Routing: this PR refines access/direction flags; the style consumes only `yescar`/`onedir`. End-to-end route-graph tests are still needed.
- Pedestrian reuse is a follow-up, not part of this stack.

## Stack

Part 2 of 5, in review order:

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. **organicmaps#14041 — cycling types (this PR)**
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
