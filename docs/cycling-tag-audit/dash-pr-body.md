## Summary

Keeps the dash phase continuous across adjacent road features instead of restarting it per feature. This is the renderer half; part 3 stores the offsets.

This upstream PR is cumulative: it also contains parts 1-3.

## Changes

- Uses the stored metaline offset and geometry direction to advance the dash phase.
- Updates line geometry, clipping, line helpers, and shaders; the Vulkan shader pack is regenerated.
- Applies the phase only to patterned cycling infrastructure, using the shared lane checkers.
- Uses the shared `indexer` metaline codec from part 3. Its ownership-only relocation does not change any phase calculation, classification, shader or style asset.

## Compatibility

- Older maps without offsets still load and fall back to a running chain offset.
- No color, width, or style change; only the phase across way boundaries.

## Testing

- Clean debug build of `drape_frontend_tests`.
- Clip-splines and reversed-metaline phase tests pass.
- Exact head `c1f68d2aad` passes 298 native tests: 65 classification/metalines, 18 clipping/phase, 188 indexer (including 7 codec tests) and 27 routing-common tests, all with Debug assertions.
- A separate research probe on this exact head passes 88 actual route checks across 44 synthetic OSM networks, through map/routing/access generation and the production router. It covers motor-access overrides, bicycle direction/access and pedestrian access. This is not a downloaded-region routing audit or a claim that the probe is in normal PR CI.
- Clang-format checks pass on all C++ files changed by this review unit. The final formatting-only revision changes no shader, classifier, phase calculation or style asset.
- Complete style-preview Pixel audit covers 60 saved-camera views on OpenGL/Vulkan with repeated cold starts. Eleven pairs are exact; no pair stable in both builds differs. Maximum difference is 289/1,219,096 map pixels. Repeat variability prevents strict pixel certification; this is not an exact-head screenshot test of this master-based branch.
- Earlier phone spot checks showed Cambie lane dashes, shared-lane dots, and solid tracks. This is not exhaustive visual-equivalence evidence; fixed-coordinate checks across zooms, themes, clipping, direction reversal and graphics backends remain required.

## Scope

- This revision was refined with Codex assistance.
- Continuous phase on the centerline; no per-side rendering or per-side arrows.
- Uses the stored offsets; no color, width, or style change.
- Answers to @vng's questions: [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Stack

Part 4 of 5, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. **organicmaps#14042 — continuous dash phase (this PR)**
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
