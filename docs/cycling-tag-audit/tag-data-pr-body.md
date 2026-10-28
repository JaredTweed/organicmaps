## Draft: cycling facility attributes

This is a fork-only review draft based on `prepare/cycling-selector`. It is not
yet a proposal to release a new map format or to merge into upstream.

The prototype retains the road's existing classifier type and adds one derived
`cyclewaytag` value for a centerline cycling style: `track`, `lane`, or
`shared_lane`. It extracts the generator-side changes from
organicmaps/organicmaps#12692, including
changes to bicycle access and direction classification. The new mapping entries
are appended after the existing upstream entries. This draft contains no cycling
style, renderer, shader or metalines changes.

Tag-order aggregation is deterministic when a negative whole-road cycleway tag
and an explicitly tagged side lane coexist; a regression test covers that case.
That policy and other generic/side conflicts need review. The type list remains
limited to eight; the prototype does not yet prove that access, direction or
surface types cannot be dropped under pressure.

## Validation and blockers

- Debug `generator_tests --filter=OsmType` and full `routing_common_tests`
  passed on the prepared branch. These tests do not prove end-to-end routing.
- On the same road-only Vancouver extract, the geometry/index-only MWM grew by
  3,760 bytes; two additional `hwtag|yescar` occurrences were observed in
  aggregate. These are not per-feature routing checks. Full-map,
  old-client/new-map, mixed-version, and routing-graph tests remain necessary.
- Confirm whether centerline-only information is sufficient and how the design
  relates to future side-specific cycling and pedestrian attributes.
- The cycling style depends on the separate `ab/cycling-style` foundation.
  No claim of preserved organicmaps/organicmaps#12692 appearance is made without
  visual comparisons.

LLM tools were used while developing and testing these changes.
