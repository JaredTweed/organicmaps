## Summary

Store side-aware cycling rendering attributes in an optional `cycling_infra` MWM section. The road retains its primary highway type. This section adds no routing permissions, new path categories, POI metadata fields, or classifier-slot consumption.

## Topic boundary

- Exact topic range: [phase renderer to side data](https://github.com/JaredTweed/organicmaps/compare/c1f68d2aadc5383a85ffc9aa9754a0c871ecd957...ac284a82895ae7e05d438d766ab351d0af15c14d).
- Sparse feature-ID index, versioned binary payload, bounded coordinates/counts/lengths, and lazy positional reads. Absent sections and unsupported versions retain the existing rendering fallback; invalid section-index bounds and failed reads follow the repository's fail-fast policy rather than silently losing attributes. The bounded payload decoder still rejects malformed payloads.
- OSM-tag policy and its tests live in generator, not the runtime indexer header. Release section reads do not decode/allocate side vectors only to discard them before the consumer's decode; Debug assertions still check writer invariants.
- Generator-only raw-feature transport; no `FMD_TEST_ID` or debug OSM preprocessing.
- Left/right kind and direction follow stored geometry reversal. Junction lists are empty until part 6.
- No new presentation is enabled in this part. Parts 6-8 consume these attributes.

## Testing

The original side-data tree `d71ce8c593` passes 193 full indexer tests and 68 OsmType/FBuilder tests. Current final integration `ef743e8134` passes 556 native checks, including ordinary/MaxAccuracy raw round trips, legacy transport, bounded malformed-payload decoding, optional-section lookup, side reversal, and generator-owned tag-policy tests. Non-finite wire values are rejected under `-ffast-math`. The tag-policy body and payload codec are unchanged; see the [nonvisual preparation report](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/nonvisual-merge-readiness.md). These are exact final-integration results, not a claim that every intermediate head was freshly rebuilt.

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
