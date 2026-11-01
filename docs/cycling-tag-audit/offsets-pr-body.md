## Summary

Add fixed-screen-pixel side-line geometry, matching arrow displacement, clipping context, and topology-authorized junction tapers. The style integration in part 8 selects the road-relative indicators.

## Topic boundary

- Own topic commits [fa72babb6a](https://github.com/JaredTweed/organicmaps/commit/fa72babb6a573f178bf736d57fb69bbfd6fa8e97) and [6aefec7e5a](https://github.com/JaredTweed/organicmaps/commit/6aefec7e5a1ccafb3ba5eefb32003eb6c7135ea9) extend the junction data. The branch also merges upstream to preserve its triangle-clipping fix. Do not mistake upstream merge contents for this feature's source delta.
- Keep the gap fixed through fractional zoom; retain neighboring segment context and bound sharp-corner miters.
- Keep line and one-way-arrow displacement consistent, including reversed geometry and junction tapers.
- Never join by proximity or extrapolate ambiguous self-crossings. Tapers use an eight-meter minimum with a minimum screen length at low zoom.
- Preserve existing symbol-placement controls, cancellation, and ordinary non-offset rendering. Shared metaline serialization stays owned by indexer.
- Geometry padding is supplied by selected style rules, not another metadata read/decode in the geometry builder. Part 8 supplies exactly the previous padding predicate; no width, gap, taper, arrow or category policy changes.
- No new cycling category or routing access change.

## Testing

Exact current master-based head `6aefec7e5a` builds and passes 542 native checks with Debug assertions: 25 rendering, 213 geometry, 193 indexer, 84 focused generator, and 27 routing-common. Current final integration `ef743e8134` separately passes 556 native checks, including the added style-padding equivalence matrix. See the [nonvisual preparation report and exact-head results](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/nonvisual-merge-readiness.md). These results are not screenshot equivalence or a fresh build of every intermediate topic.

This is a cumulative upstream draft. Maintainer agreement on the rendering boundary, CI, and eventual master integration remain required.

## Stack

Part 7 of 8, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [side-aware data](https://github.com/organicmaps/organicmaps/pull/14074)
6. [topology-backed junctions](https://github.com/organicmaps/organicmaps/pull/14075)
7. **fixed-pixel offset renderer (this PR)**
8. [cycling style integration preview](https://github.com/organicmaps/organicmaps/pull/14043)

Prepared with Codex (LLM) assistance; original commit authorship is retained.
