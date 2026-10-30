# Primary road and infrastructure constraints

Discussion: [vng on #14040](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6523827420).
Response: [proposed boundary](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6524260599).
User decision, 2026-10-30: preserve #12692's appearance; keep offset rendering
as a separate proposal/prototype. This is not an assertion that vng accepted
the existing centerline preview as the final rendering design.

## Proposed contract

- Keep one primary highway family on an ordinary road. Nested subtypes such
  as `highway|footway|bicycle` still belong to the footway family.
- Attached bicycle/pedestrian infrastructure is additional data, represented
  by `cyclewaytag` / a future `footwaytag`, not a synthetic second highway.
- A shared footway/cycleway can carry both families on one physical geometry,
  as in the linked shared-path photograph. This does not justify arbitrary
  secondary/cycleway or residential/cycleway combinations.
- Keep `extra_tag` bounded to resolved classifier membership (`=` / `!=`),
  including parent-path matching. Classification and style policy own the
  road-model constraints; the selector does not manufacture or prioritize types.

Existing `OsmType_Hwtag` fixtures already assert exact type counts for primary,
secondary and residential roads with lane/track/shared-lane infrastructure.
These pass in the final master-based audit, rather than merely asserting that
the main type appears somewhere in an otherwise unconstrained type set.

## Measured legacy exception

The complete, matched Vancouver exports have the same 137 line features with
footway + cycleway and six with footway + ford; no other multi-highway-family
combinations occur in this extract. The audit reports this explicitly rather
than concealing it in an automatically approved exception list.

The upstream classifier already maps `ford=yes` and related values to
`highway=ford` through `data/replaced_tags.txt`. That file already has a TODO
to move away from the deprecated representation. This is an ancillary legacy
modifier, but vng must clarify how it fits the stated namespace constraint.
Do not remove it here: that would be unrelated classifier/routing/style work
and could change the reference appearance.

## Rendering is a separate decision

A dedicated, separately mapped cycleway has its own core geometry. Attached
infrastructure can reasonably use offset strokes in a future style, including
the generic style. That proposal is not implemented by the current preview.

The current generator collapses differing left/right infrastructure into one
conservative centerline category. It cannot truthfully support side-aware
offsets without preserving side, facility category and direction first.
A prototype must define side relative to OSM way direction, reversal handling,
clipped joins, intersections, arrows, mixed facilities and the treatment of
`cycleway=separate` so separately mapped paths are not duplicated. The eight-type
budget must be measured before adding per-side classifier entries.

No offset shader/geometry or retention-policy change belongs in the
#12692-equivalence baseline. Compare any prototype separately and label its
intentional visual differences. Generic-style adoption needs its own review.

## Publication boundary

After the user's subsequent authorization and exact-head native validation,
the split code heads were updated to the pins in `stack-readiness.md`.
The independent motor-access draft is #14054. All six remain drafts; this
author-side authorization does not resolve vng's model/rendering questions.
The selector's code is unchanged. Side-offset line rendering is still separate.
Original #12692 code remains protected at `955cd49403`.
