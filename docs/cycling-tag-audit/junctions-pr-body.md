## Summary

Collect topology-backed cycling junction hints through the normal country generator. This replaces the phone prototype's Python annotation step; it does not invent routing connections or marked crossings.

## Topic boundary

- Exact topic range: `prepare/cycling-side-data..prepare/cycling-junction-data`.
- Shared OSM node IDs authorize a join; coordinate proximity alone does not.
- Match accessible dedicated cycling connectors to the approached road side at equal layer/level. Reject barriers, restrictions, collinear approaches, and contradictory duplicates.
- Preserve the prototype's explicit-side junction opt-in (`cycleway:left/right/both`). Modifier-only facilities still render as lanes, but do not acquire additional inferred tapers in this revision; the normal-generator fixture covers this boundary.
- Preserve stored geometry direction. Shared-lane dots remain centered; only track/lane sides receive junction hints.
- Worker spool files and country shards cap open writers; blocked-node queries use a sorted on-disk index. Country-relevant road/connector memory and planet-scale performance still need review.
- No renderer changes in this part; part 7 provides the geometry primitives and part 8 enables presentation.

## Testing

Five junction tests pass, including a real normal-generator fixture from OSM through the optional MWM section to FeatureType. Cases cover shared topology, coordinate coincidence without connectivity, grade separation, barriers, access restrictions, reversal, and centered shared lanes.

This is a cumulative upstream draft; review the topic range above. It is not an end-to-end routing-graph test.

## Stack

Part 6 of 8, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [side-aware data](https://github.com/organicmaps/organicmaps/pull/14074)
6. **topology-backed junctions (this PR)**
7. [fixed-pixel offset renderer](https://github.com/organicmaps/organicmaps/pull/14076)
8. [cycling style integration preview](https://github.com/organicmaps/organicmaps/pull/14043)

Prepared with Codex (LLM) assistance; original commit authorship is retained.
