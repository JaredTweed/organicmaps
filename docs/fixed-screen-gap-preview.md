# Fixed screen-gap preview

Branch: `demo/cycling-fixed-screen-gap`, based on the saved outlined-arrow
prototype. This is an archived phone prototype, not a PR. It does not modify
the split PRs or #12692.

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

## Installed revision and checks

Renderer revision `23b50207355c2756bddf50dc7776c499b6d521cb` was built, installed
and launched in the isolated `OM Side Offsets` app. The user accepted its phone
appearance. All 32 focused native tests and nine tooling tests pass; the new
cases cover intermediate zoom factors, pixel-gap consistency, bounded miters
and reversed arrow offsets. No automated screenshot verification was performed.

`fixed-screen-gap-checks.json` records the installed APK/native/map hashes and
test evidence. The existing fixture map was verified on the phone. Heavy jobs
ran sequentially with a 1800 MiB cap and no swap allowance.

The local APK and packaging manifest are under
`build-visual-artifacts/fixed-screen-gap/phone.apk` and `phone.json`; neither
binaries nor fixture maps are committed. The source remains a prototype:
successful local tests and an accepted phone trial are not upstream approval.
