## Summary

Keeps the dash phase continuous across adjacent road features instead of restarting it per feature. This is the renderer half; part 3 stores the offsets.

This upstream PR is cumulative: it also contains parts 1-3.

## Changes

- Uses the stored metaline offset and geometry direction to advance the dash phase.
- Updates line geometry, clipping, line helpers, and shaders; the Vulkan shader pack is regenerated.
- Applies the phase only to patterned cycling infrastructure, using the shared lane checkers.

## Compatibility

- Older maps without offsets still load and fall back to a running chain offset.
- No color, width, or style change; only the phase across way boundaries.

## Testing

- Clean debug build of `drape_frontend_tests`.
- Clip-splines and reversed-metaline phase tests pass.
- Earlier phone spot checks showed Cambie lane dashes, shared-lane dots, and solid tracks. This is not exhaustive visual-equivalence evidence; fixed-coordinate checks across zooms, themes, clipping, direction reversal and graphics backends remain required.

## Scope

- Continuous phase on the centerline; no per-side rendering or per-side arrows.
- Uses the stored offsets; no color, width, or style change.
- Answers to @vng's questions: [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

## Stack

Part 4 of 5, in review order:

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. **organicmaps#14042 — continuous dash phase (this PR)**
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
