# Visual equivalence audit

## New baseline under validation

The appearance-preserving candidate is now `82b6f698878501810f4f6a2d7239e2bd36ff836e`.
Conflicting-tag order and collision-free chain-key fixes are separate follow-ups,
not included in that baseline. Its classification logic and chain grouping are
the original #12692 implementation; the generator's retained difference is the
additive compatibility format. All runtime sources and tracked assets match the
earlier candidate, and rebuilding produces the identical Android native binary.

The Pixel comparison is complete. The reference/candidate matrix uses reference-only
camera normalization to an exact serialized fixed point, then rejects any
candidate camera drift. It includes real OpenGL and Vulkan, both themes, three
nominal deep-link zooms, five sites and repeated independent cold starts.
The saved camera rectangles, not the fixture names, define the exact viewports.
Neither a strict complete phone pass nor an all-regions guarantee is claimed.

The new matched-map result is in
[visual-equivalence-baseline-data.json](visual-equivalence-baseline-data.json):
82,785 features and 2,010 directed chains/offsets match exactly, with no
unidentified or ambiguous features. Its exact-head native result is
[equivalence-style-native-results.json](equivalence-style-native-results.json):
62 generator, 23 reader/clipping/phase, 181 indexer and 27 routing-common
tests pass (293 total), all with Debug assertions.

The completed original-reference phone run repeats exactly in 10 of 60
views. The largest observed reference-repeat difference is 182 pixels in
the fixed 1,219,096-pixel map region. This precludes a strict full-matrix
repeat-stable pass on this run; it is not a candidate regression and not
permission to ignore candidate differences.

### Completed phone result

[visual-phone-results.json](visual-phone-results.json) records all 60 views:
11 cross-build pairs match exactly; 10 reference views and 11 candidate views
repeat exactly. Two pairs are exact and stable in both builds, with no
cross-build discrepancies among the pairs stable in both builds. The largest
cross-build difference is 289 of 1,219,096 pixels (about 0.024%). The strict
equivalence flag is false: no pixel tolerance or baseline-variability waiver
was introduced.

One candidate screenshot contained Android's volume panel. Both cold starts
of that complete case were recaptured using identical provenance/settings,
not selected for pixel agreement. Original captures and the contaminated
comparison remain preserved locally; the new manifest records superseded
image hashes, both manifest hashes and the replacement reason. Capture now
rejects visible volume, notification or keyboard overlays before/after a frame.

The [reference manifest](visual-phone-baseline-manifest.json) and
[candidate manifest](visual-phone-candidate-manifest.json) bind exact APK,
native, asset, map and PNG hashes. Raw frames remain under
`organicmaps-cycling-visual-check/build-visual-artifacts/` in
`baseline-phone-reference`, `equivalence-phone`,
`equivalence-phone-overlay-recapture` and `equivalence-phone-validated`.
Private settings backups and window-manager dumps are not committed.

No styling regression was apparent in the inspected views. This does not
certify every frame, supported GPU, region, zoom or final merged-master base.

The following results are retained evidence for the earlier candidate. They
must not be described as new exact-head generation or phone results.

This audit compares original PR #12692 at
`955cd49403ed025c24beec09f5551e8d274a38ff` with the candidate style tree at
`f8f603fc7e24e1cad765423fc75c392d3aa0ae56`. It does not modify the original
branch. Results apply to the recorded Vancouver road extract, not every map.

## Verified data

The machine-readable result and build/map provenance are in
[visual-data-results.json](visual-data-results.json).

- Both exact source revisions produced native Android arm64 libraries with
  Debug assertions. Builds used one compiler worker, a 1800 MiB hard memory
  limit, no additional swap, and reduced debug information.
- The entire tracked `data/` tree is identical, including classifier mappings,
  generated drawing rules, symbols, colors and patterns. Its Git tree is
  `4c257be6638d2be4cec4156b48645734f6ea84af`.
- Separate generators built from each clean source revision processed the
  same OSM input with one worker. Classifiers came from the matching revision.
- All 82,785 features match by OSM identity and exact segment geometry. Their
  retained types, names, references, layers, ranks, addresses and binary
  metadata match. There are no ambiguous identity groups.
- All 2,010 directed chains and their offsets match. No overlapping-chain
  ordering ambiguity occurs in this extract.
- The original map contains a version-3 `metalines` section. The candidate
  contains authoritative version-1 `metalines` plus optional version-3-layout
  `metalines_offsets`; the optional data validates and applies completely.
- The candidate map grows from 2,447,904 to 2,475,113 bytes (+27,209, about 1.1%).
  The extra legacy section is the deliberate cost of compatibility.

This is stronger evidence than the earlier 209 aggregate type-dump lines,
which could conceal per-road changes. It is still **not pixel equivalence**.
The unchanged type-retention policy is being compared here; this is not a
per-feature validation of the earlier retention experiment.

## Rendering gate: not certified

[visual-pixel-results.json](visual-pixel-results.json) records an actual Qt
OpenGL comparison on Mesa Intel UHD 620: 60 fixed-camera views, each captured
twice independently. Sites cover lane, shared lane, track, feature zero and
mixed-side contraflow, at zooms 14/16/18, light/dark themes and densities 1/2.

- 36 baseline/candidate pairs are pixel-identical; 23 also repeat identically
  within both builds.
- The largest cross-build difference is 105 of 725,760 pixels (about 0.015%).
  The candidate itself varies by up to 168 pixels between repeats.
- One dark shared-lane view repeats identically within each build but differs
  by 17 grayscale road-edge pixels across builds. This remains an explicit
  discrepancy, not a silently ignored tolerance or a proven harmless change.
- A repeated light-theme control using untouched #12692 on single-threaded
  llvmpipe also varies (up to 115 pixels). This demonstrates baseline
  variability, but does not prove every cross-build discrepancy harmless.
- The strict full-matrix equivalence flag is therefore **false**. No tolerance
  was added to manufacture a pass. The solid/dashed/dotted styling shows no
  visible regression in inspected views; this is not universal pixel proof.
- The original and candidate Qt processes sometimes stall after reporting all
  screenshots saved. Cleanup after that completion signal is bounded and
  recorded separately in the capture manifests.

At the time of these desktop captures the Pixel 8 Pro was disconnected. These desktop results do not certify
Pixel OpenGL/Vulkan behavior. Generated route graphs are also outside this
road-only fixture.

`visual_phone.py` packages the exact native libraries into the isolated
`app.organicmaps.cyclingfinal.debug` shell. It validates source/map/classifier
provenance, preserves the normal Organic Maps app, and captures repeated cold
launches at the same saved camera. Graphics fallback is an error.

`visual_equivalence.py` requires an explicit map-region rectangle, identical
camera/settings and matching assets. It compares exact pixels, checks repeat
stability, and binds captures to the corresponding map/export checksums and
source revisions. Missing screenshots never count as a pass. Desktop OpenGL
captures are reported separately from the new Pixel/Vulkan runs.

Required fixtures include solid track, dashed lane, dotted shared lane, mixed
sides, contraflow, reversed chains and clipped intersections at multiple zooms,
light/dark themes and supported backends. Preserve raw images and manifests.

## Deliberately unchanged edge

The legacy signed-feature encoding cannot express the direction of feature
zero independently. Original code treats zero as reversed when reading. This
revision retains that behavior rather than silently fixing it and calling the
result equivalent. The Vancouver map includes feature zero in a Grant
McConachie Way chain; include that area in rendering checks. Any encoding fix
needs a separate compatibility and appearance review.

Generated bicycle route tests remain a separate gate. Matching classification
and rendered maps does not prove routing correctness.
