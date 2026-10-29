## Summary

Stores a dash-phase offset per metaline feature so the renderer can keep a dash pattern continuous across OSM way boundaries. This is the data-format half; the renderer use is part 4.

This upstream PR is cumulative: it also contains parts 1-2.

## Changes

- The metalines section goes from version 1 to 3 and stores one double offset per feature.
- Unnamed painted lane and shared-lane ways are added to metalines in separate chains.
- Adds shared `ftypes` checkers for the two painted-lane types, uses stable 64-bit chain keys instead of `std::hash`, and removes the dead version-2 reader.

## Compatibility

- Older maps (version 1) still load; without offsets the renderer falls back to a running chain offset.
- Old clients reject the version-3 section and lose merged labels/shields on new maps. An append-only extension is the main alternative to decide before merging.

## Testing

- `generator_tests --filter=Metalines` passes.
- Full `indexer_tests` suite passes.
- `drape_frontend_tests --filter=ClipSplines` passes.
- Phone preview with a map generated from this classifier keeps solid/dashed/dotted styling unchanged.

## Stack

Part 3 of 5, in review order:

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. **organicmaps#14048 — metalines offsets (this PR)**
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
