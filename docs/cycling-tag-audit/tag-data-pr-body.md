## Summary

Adds `cyclewaytag|track`, `cyclewaytag|lane`, and `cyclewaytag|shared_lane` as additional types while keeping the road's main `highway` type. Styles can then distinguish cycling infrastructure without replacing the road classification.

Draft: the access and direction changes in this PR affect bicycle routing and need review.

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

- This PR also adds explicit `motor_vehicle=permissive` handling. Two additional `hwtag|yescar` combinations appeared on the test extract (one pedestrian way, one sidewalk), so this is not a visual-only change.
- Aggregate counts are not matched features; individual routing correctness still needs route-graph tests.

Stacked on the selector PR.
