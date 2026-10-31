# Thin offset prototype

Local branch: `prototype/cycling-thin-offsets`. This is independent of the
split PRs and does not modify #12692 or the previous full-width prototype.

Normal roads keep Standard-mode highway strokes, including their casing.
Explicit attached cycling facilities are drawn just outside that casing,
with a two-logical-pixel gap. Track is solid, lane dashed and shared lane
dotted. All three have exactly the same stroke width at each zoom:
2 logical pixels through zoom 16 and 2.5 from zoom 17 onward. Dash lengths
scale with the stroke so shared-lane dots do not become long rectangles.
There is no extra cycling casing or duplicate blue centerline on these roads.

Side rendering starts at zoom 14, subject to each existing pattern's visibility
threshold. Dedicated cycleways remain core lines, with the same width schedule
as the three indicators. Existing bicycle direction symbols are retained.
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
