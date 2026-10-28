## Summary

Keeps the dash phase continuous across adjacent road features instead of restarting it per feature. This removes the visible phase break where a dashed road is split into several OSM ways.

Stacked on the cycling-types PR because the phase is currently applied to patterned cycling infrastructure (`cyclewaytag=lane` and `cyclewaytag=shared_lane`).

## Changes

- The MWM metalines section version goes from 1 to 3 and stores one double dash-phase offset per feature. The reader accepts versions 1-3; version 2 was only an intermediate development format and is never written.
- The renderer combines the stored offset with the geometry direction.
- Shader sources are updated and the Vulkan shader pack is regenerated.

## Compatibility

- Older maps (version 1, and the intermediate version 2) still load; without offsets the renderer falls back to a running chain offset.
- New maps are readable by older clients, but a version-1 reader rejects the whole version-3 section, so merged-line labels and shields fall back to per-feature placement on every new map, not only cycling ways. This is graceful visual degradation, not a crash, but it is the main cost of the format change.
- An append-only alternative (keep version 1 and add a trailing offset block that old readers ignore) would avoid that regression. It is the main design choice to settle before merging this PR.

## Testing

- Clean debug build of `generator_tests` and `drape_frontend_tests`.
- Metalines and clip-splines tests pass.
- Device visual check is still required at all zoom levels and in both themes before this leaves draft.

## Stack

Part 3 of 4, in review order:

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [fork#1 — cycling types](https://github.com/JaredTweed/organicmaps/pull/1)
3. **fork#2 — dash phase (this PR)**
4. [fork#3 — cycling style preview](https://github.com/JaredTweed/organicmaps/pull/3)
