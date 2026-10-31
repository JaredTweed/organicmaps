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
