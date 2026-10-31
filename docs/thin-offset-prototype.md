# Thin offset prototype

Branch: `prototype/cycling-thin-offsets-shared-centerline`, based on
`prototype/cycling-thin-offsets`. This is independent of the
split PRs and does not modify #12692 or the previous full-width prototype.

Normal roads keep Standard-mode highway strokes, including their casing.
Explicit attached tracks and lanes are drawn just outside that casing,
with a two-logical-pixel gap. Track is solid, lane dashed and shared lane
dotted. Shared-lane dots always use one centerline treatment, including when
both sides are shared. Mixed roads combine centered dots with the relevant
offset track or lane. All three have exactly the same stroke width at each zoom:
2 logical pixels through zoom 16 and 2.5 from zoom 17 onward. Dash lengths
scale with the stroke so shared-lane dots do not become long rectangles.
There is no extra cycling casing. Only shared lanes keep a cycling centerline
when separate side data is rendered.

Side rendering starts at zoom 14, subject to each existing pattern's visibility
threshold. Dedicated cycleways remain core lines, with the same width schedule
as the three indicators. Existing bicycle direction symbols are retained.
For offset facilities, one-way bicycle arrows follow the same offset geometry,
not the road centerline. Explicit side direction overrides the road-wide
direction: backward sides reverse only their arrow geometry, and two-way sides
have no one-way arrows. Where a side's direction is unknown, the existing
road-wide bicycle one-way flags supply the fallback. The original arrow zoom
threshold (15) is retained. Dedicated/core cycling arrows remain on their core
lines; the three stroke widths and patterns do not change.
Shared-lane arrows follow their centered dots. If several shared sides are
combined, an arrow is shown only when every represented side resolves to the
same one-way direction. Opposing directions, explicit two-way access and
unresolved disagreements never become a misleading single one-way arrow.
Unqualified facilities without recorded sides retain a single thin centerline;
the prototype does not fabricate which side has a facility. Below the side-line
threshold, the conservative summary uses that same thin width schedule.

The existing side-metadata Vancouver fixture can be reused: no generator,
classifier, map schema or routing changes are made. The inherited acute-angle
offset and intersection limitations remain experimental. This is not a
production navigation map.

The APK uses the isolated `OM Side Offsets` application and can replace that
demo with `adb install -r`, without replacing the normal or centerline apps.
See the `Side offset examples` bookmark category: Water Street (lane/shared),
West 49th Avenue (lane/track), East 14th Avenue (shared/shared), Ash Street
(lane/lane), West 1st Avenue (one-sided lane), East 5th Avenue (one-sided track).

Once a phone is connected and USB debugging is authorized, install the prepared
APK and matching fixture without clearing demo data:

```sh
python3 docs/cycling-tag-audit/install_thin_offsets.py
```

The helper validates APK/map hashes and only updates the isolated demo. It
keeps existing settings, including the current map-style selection. The APK
and its manifest are under
`build-visual-artifacts/side-offsets/thin-offsets/phone.apk` and `phone.json`.

## Shared-centerline revision

This branch is saved separately from the previously installed all-offset
prototype. Its centered shared-lane change passes 29 focused native tests
(`ClipSplines|DashedLinePhase`) and eight tooling tests. The regression cases
cover both shared sides collapsing to one centered stroke, mixed facilities,
equal stroke widths, and one-way direction agreement or suppression.
See `thin-offset-shared-centerline-checks.json` for the tested source and hashes.

The Android APK has not been rebuilt or installed for this revision. Existing
ignored APK files may still contain the previous all-offset renderer; rebuild
and repackage before using the installer to try this branch on a phone.
No split PR or #12692 code was changed, and no PR is opened for this branch.
