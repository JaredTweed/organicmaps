# Topology-backed cycling junction prototype

Local experiment; no PR changes and no change to #12692.

The fixture preprocessor records junctions only where an accessible, separately
mapped cycling way shares an OSM node ID with a road carrying explicit side
tags. The connector's outgoing geometry identifies the approached side. It
rejects mismatched levels/layers, restrictions, barriers, and ambiguous
collinear approaches. Equal coordinates without a shared ID do not connect.

At an authorized point the existing side indicator smoothly reduces its
screen-space offset to zero over eight metres on each side. Its width, color,
pattern, and direction remain unchanged. Arrows use the same interpolated
offsets, including reversed arrows. Shared-lane dots remain centered. The
connector itself and routing geometry are not modified. This indicates
connectivity, not a marked or protected crossing.

The debug metadata has a version-2 extension. Old version-1 fixtures still
decode, but cannot show the new joins. A freshly generated fixture is required;
the previous map must not be passed off as topology-enabled.

This is deliberately conservative. Ambiguous sides, missing source nodes,
barriers, grade transitions with inconsistent tags, and simplification beyond
the one-metre projection tolerance may leave a gap. The preprocessor only
handles the separately mapped cycling connectors above, not arbitrary road
intersections, turn permissions, or routing restrictions. No near-endpoint
snapping, new crossing geometry, or additional cycling category is introduced.

## Verification

- 43 focused native clipping/rendering tests pass, including payload round-trip,
  reversal, taper interpolation, tile clipping, and ambiguous self-crossings.
- 19 tooling tests pass, including shared-ID versus coincident-coordinate cases,
  restrictions, barriers, grade mismatches, reversed roads, and unchanged source
  geometry/access tags.
- All 82,785 exported features match the preceding fixture after excluding only
  the new junction coordinates. Road geometry, category, side/direction, and all
  other metadata remain identical. There are 173 active track/lane-side junction
  annotations, including three on Stanley Park Causeway. Conservative renderer
  projection checks can still decline an annotation.
- No screenshot comparison is claimed. Host builds and map generation use one
  worker, a 1,800 MiB memory cap, and no swap allowance. The host generator's
  pre-existing submodule revision differences are recorded in the map manifest;
  they were not reverted.

## Phone Build

The isolated package remains `app.organicmaps.cyclingsides.debug` (OM Side
Offsets). The APK and matching map are under
`build-visual-artifacts/topology-junctions/`. The three confirmed Causeway points
are in `docs/topology-junction-examples.kml`.

After connecting and authorizing the phone:

```bash
python3 docs/cycling-tag-audit/install_thin_offsets.py \
  --apk build-visual-artifacts/topology-junctions/phone.apk \
  --bookmarks docs/topology-junction-examples.kml
```

This preserves existing app data and verifies the installed map hash. Open
Bookmarks, then Cycling Junction Examples, and inspect at street-level zoom.
