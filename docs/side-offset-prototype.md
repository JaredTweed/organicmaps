# Local side-offset visual prototype

This branch is a local experiment, not part of the split PRs and not a change
to #12692. Do not push it or edit GitHub as part of this experiment.

## Behavior

- Ordinary roads retain their primary highway styling. Explicit left/right
  or both-side cycling facilities are rendered alongside that road.
- Dedicated cycleways retain their core-line treatment.
- Solid track, dashed lane and dotted shared-lane strokes reuse the existing
  cycling drawing rules, at 65% stroke scale and a visible gap from the road.
- Explicit side-specific tags override both-side tags; reversed OSM geometry
  swaps sides and reverses stored directions. Separately mapped facilities
  are not duplicated by attached offset strokes.
- Unqualified tags without explicit sides retain the existing centerline
  fallback. This prototype does not guess an unrecorded side.
- Generic and cycling styles can both display the offset strokes.

## Deliberate limits

This is not a production data-model or routing proposal. The demo map uses
the existing test-only metadata field, with a versioned payload, rather than
consuming more classifier slots or inventing extra highway types. Production
side storage needs its own reviewed schema. The prototype preserves explicit
side directions but does not add per-side arrows. It does not change routing
access flags. Offset joins, intersections, changing road widths and phase
across differently tagged ways still need production design and review.

Offset geometry uses the existing spline equidistant implementation before
tile clipping. Its acute-angle limitations are not resolved by this demo.
The map is a road-only Vancouver fixture, not a routable production download.

## Phone

Install separately as `app.organicmaps.cyclingsides.debug`, labeled
`OM Side Offsets`. Do not replace the normal app or the centerline demo.

The included `side-offset-examples.kml` category provides six real OSM
locations. Side means relative to OSM way direction, not screen left/right.
Inspect at street-level zoom; the offset overlay begins at zoom 14.

- Water Street: lane on one side and shared lane on the other.
- West 49th Avenue: lane on one side and track on the other.
- East 14th Avenue: shared lanes on both sides.
- West 1st Avenue: a one-sided lane.
- Ash Street: lanes on both sides.
- East 5th Avenue: a one-sided track.

Coordinates and tag examples come from the local Vancouver OSM fixture, not
a claim that these are current on-the-ground infrastructure conditions.
