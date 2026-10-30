## Summary

Stores optional dash-phase offsets while retaining the legacy version-1 metalines section. This is the data-format half; the renderer use is part 4.

This upstream PR is cumulative: it also contains parts 1-2 and the independent motor-access prerequisite. The lane checkers now belong to the classifier/types PR, not this format PR.

## Changes

- Keeps `metalines` at version 1. A separate `metalines_offsets` section uses the already-supported version-3 layout, including feature IDs/directions and double offsets.
- Unnamed painted lane and shared-lane ways are added to metalines in separate chains.
- Grouping uses an ordered `(kind, name, ref)` key rather than collidable name hashes or numeric sentinels. This changes the generator's temporary collector format; regenerate intermediate files rather than mixing old and new collectors.
- Reads v1 (no offsets), experimental v2 (float offsets), and v3 (double offsets) explicitly. Consuming v2 offsets is essential to keep subsequent feature records aligned.
- Applies optional offsets only when every chain's feature list, reversal flags and offset count match the authoritative section. Damaged, stale or trailing optional data leaves the legacy model untouched; validation is all-or-nothing.

## Compatibility

- Older maps (version 1) still load; without offsets the renderer falls back to a running chain offset.
- Version-1 readers still receive a version-1 section with the same signed-feature layout; they can ignore the additional tag rather than losing all metalines. No backwards-safe trailer is assumed.
- This is a metalines-format compatibility argument, not a claim that every historical app/map-classifier combination has been tested.

## Testing

- `generator_tests --filter=Metalines` passes.
- Regression fixtures cover collector-key round trips and distinct grouping kinds; versioned decoding, reversal, unknown versions, truncated/trailing optional sections and stale feature/direction/count mismatches.
- Earlier full `indexer_tests` evidence predates this additive-section revision; do not treat it as an exact-head run.
- `drape_frontend_tests --filter=ClipSplines` passes.
- Exact original/candidate generators match all 82,785 Vancouver features and 2,010 directed chains/offsets. The optional section validates completely; preserving the legacy section costs 27,209 bytes (about 1.1%) on this map.
- Earlier phone previews are limited evidence, not a complete visual-equivalence result. Fixed-camera pixel comparisons across zoom, theme, reversal and clipping remain required; the current Pixel is disconnected.

## Scope

- Stores offsets only; the renderer use is 4/5.
- One centerline chain per road pattern; no side-specific data.
- Additive phase metadata preserves the authoritative legacy section. Emitted legacy records and resolved offsets are included in the matched-map audit; historical-client coverage is reported separately.
- Answers to @vng's questions: [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

## Stack

Part 3 of 5, in review order:

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. **organicmaps#14048 — metalines offsets (this PR)**
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
