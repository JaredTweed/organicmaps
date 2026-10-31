# Fixed screen-gap preview

Local branch: `demo/cycling-fixed-screen-gap`, based on the saved outlined-arrow
prototype. This trial is not pushed to GitHub and does not modify the split PRs
or #12692.

Attached cycling indicators no longer use map-coordinate equidistant geometry.
Their axis stays on the road; the stroke vertices include a pixel displacement
equal to half the visible road width, half the cycling width and a two-logical-
pixel gap. Existing line shaders preserve that displacement through continuous
zooming, using the same extrusion mechanism as the road's width. Solid joins
and caps use the displaced pixel center too; the hardware thin-line shortcut
is disabled for displaced strokes. Miter length is bounded at sharp reversals.

Arrows use the same signed pixel offset. Reversing an arrow reverses the offset
sign relative to its new tangent, keeping it on the same side. Shared dots and
their arrows keep zero displacement. All three pattern widths, category
selection and the color-matched arrow outlines are preserved. No shader,
classifier, routing or map-schema changes are required.

This addresses within-scale zoom drift. Discrete road-width changes still
move the indicator to follow the newly rendered edge. Complex junctions and
acute angles remain prototype limitations, not a production routing proposal.
