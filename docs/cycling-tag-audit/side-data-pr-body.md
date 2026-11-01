## Summary

Store side-aware cycling rendering attributes in an optional `cycling_infra` MWM section. The road retains its primary highway type. This section adds no routing permissions, new path categories, POI metadata fields, or classifier-slot consumption.

## Topic boundary

- Exact topic range: `prepare/cycling-dash..prepare/cycling-side-data`.
- Sparse feature-ID index, versioned binary payload, bounded coordinates/counts/lengths, and lazy positional reads. Absent, unsupported, or invalid attributes fall back to the existing feature rendering.
- Generator-only raw-feature transport; no `FMD_TEST_ID` or debug OSM preprocessing.
- Left/right kind and direction follow stored geometry reversal. Junction lists are empty until part 6.
- No new presentation is enabled in this part. Parts 6-8 consume these attributes.

## Testing

The original side-data tree `d71ce8c593` passes 193 full indexer tests and 68 OsmType/FBuilder tests, including ordinary/MaxAccuracy raw round trips, legacy transport, malformed payloads, optional-section lookup, and side reversal. Subsequent shared-decoder hardening checks raw IEEE exponent bits before floating-point decoding, with explicit infinity/NaN regression coverage under `-ffast-math`. Current consuming-head results are recorded in the final integration report.

This PR is cumulative against master because the preceding fork branch cannot be an upstream base ref. Review the exact topic range above. All parts remain drafts pending maintainer review and CI.

## Stack

Part 5 of 8, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. **side-aware data (this PR)**
6. [topology-backed junctions](https://github.com/organicmaps/organicmaps/pull/14075)
7. [fixed-pixel offset renderer](https://github.com/organicmaps/organicmaps/pull/14076)
8. [cycling style integration preview](https://github.com/organicmaps/organicmaps/pull/14043)

Prepared with Codex (LLM) assistance; original commit authorship is retained.
