# Rendering polish preview

Branch: `demo/cycling-rendering-polish`, based on the saved bridge-continuity
prototype. This is an archived phone prototype, not a PR. Neither the split
PRs nor #12692 are changed.

Focused fixes:

- Tunnel decoration no longer inflates the cycling offset, following the same
  ordinary-road-width convention as bridges. Structural drawing rules remain.
- A cycling indicator remains drawable when its base road has no visible
  stroke at the current zoom. Visibility/dispatch and geometry accept side-only
  line rules instead of dropping them or requiring an unrelated base stroke.
- Clipping can return source distance ranges and segment indices. Dash phase
  no longer searches for the first matching coordinate, which was ambiguous
  on repeated/self-crossing paths. The default geometry output is unchanged.
- Cycling arrow spacing is anchored to the feature, not restarted at every
  tile fragment. Reversed side arrows anchor to the reversed feature. The
  original leading-arrow offset and zoom thresholds are preserved.
- Pixel-offset endpoint normals retain the full source corner context. A tile
  cut through a corner no longer substitutes a straight endpoint normal.
- Side metadata can request dash-phase lookup even if the aggregate cycling
  classifier type is absent. Clipping is shared across a road's side indicators
  instead of repeated for each side.

All three pattern categories, their equal widths, centered shared-lane dots,
conservative shared directions, fixed pixel gaps and outlined solid arrows
remain. No classifier, routing or map-format changes are made. The optional
clipping metadata describes existing geometry; existing callers can omit it.

This is not a complete intersection/offset renderer redesign. Country-wide
coverage, exact pixel equality across devices, perfect acute-angle joins and
global arrow spacing across distinct OSM ways are not claimed. Arrows exactly
on a shared clipping endpoint can still be emitted by both neighboring tiles.

## Installed revision and verification

Revision `b63c410edc4ae8322a4e06a862cc99d013f79801` was built, installed and
launched in the isolated `OM Side Offsets` app. All 38 focused rendering tests,
204 geometry tests (the full geometry suite), and 10 tooling tests pass.
The fixture map checksum was verified on the phone. No automated screenshot
verification was performed; local tests do not constitute upstream approval.

`rendering-polish-checks.json` records source, test, APK, native-library and map
hashes. Heavy jobs ran sequentially with a 1800 MiB memory cap and no swap
allowance. The local APK and packaging manifest are under
`build-visual-artifacts/rendering-polish/phone.apk` and `phone.json`.
Binaries and fixture maps are not committed.
