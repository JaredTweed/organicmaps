## Summary

Add fixed-screen-pixel side-line geometry, matching arrow displacement, clipping context, and topology-authorized junction tapers. The style integration in part 8 selects the road-relative indicators.

## Topic boundary

- Own topic commit [fa72babb6a](https://github.com/JaredTweed/organicmaps/commit/fa72babb6a573f178bf736d57fb69bbfd6fa8e97) extends `prepare/cycling-junction-data`; the branch also merges current upstream to preserve its triangle-clipping fix. Do not mistake upstream merge contents for this feature's source delta.
- Keep the gap fixed through fractional zoom; retain neighboring segment context and bound sharp-corner miters.
- Keep line and one-way-arrow displacement consistent, including reversed geometry and junction tapers.
- Never join by proximity or extrapolate ambiguous self-crossings. Tapers use an eight-meter minimum with a minimum screen length at low zoom.
- Preserve existing symbol-placement controls, cancellation, and ordinary non-offset rendering. Shared metaline serialization stays owned by indexer.
- No new cycling category or routing access change.

## Testing

On `398c4ed223`, all 26 offset/clipping tests, 214 geometry tests, 194 indexer tests, and 82 focused generator tests pass with Debug assertions. The final style integration has separate validation; these results are not screenshot equivalence.

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
