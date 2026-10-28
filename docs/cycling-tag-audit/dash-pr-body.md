## Summary

Keeps the dash phase continuous across adjacent road features instead of restarting it per feature. This removes the visible phase break where a dashed road is split into several OSM ways.

Stacked on the cycling-types PR because the phase is currently applied to patterned cycling infrastructure (`cyclewaytag=lane` and `cyclewaytag=shared_lane`).

## Changes

- The MWM metalines section version is bumped from 2 to 3 and stores a per-feature dash phase offset; readers accept versions 1-3.
- The renderer combines the stored offset with the geometry direction.
- Shader sources are updated and the Vulkan shader pack is regenerated.

## Compatibility

- Older maps (versions 1-2) still load; the reader accepts them.
- New maps are readable by older clients, but those clients ignore the version-3 metalines section and fall back to per-feature text/shield placement instead of the merged metaline. This is a graceful visual degradation, not a crash.

## Testing

- Clean debug build of `generator_tests` and `drape_frontend_tests`.
- Metalines and clip-splines tests pass.
- Device visual check is still required at all zoom levels and in both themes before this leaves draft.
