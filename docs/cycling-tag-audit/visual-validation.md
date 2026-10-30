# Visual equivalence audit

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

The Pixel 8 Pro remains disconnected. These desktop results do not certify
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
captures are reported separately from the absent Pixel/Vulkan coverage.

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
