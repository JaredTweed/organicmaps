# Bridge continuity preview

Branch: `demo/cycling-bridge-continuity`, based on the fixed-screen-gap
prototype. This is an archived phone prototype, not a PR. It does not change
#12692 or the split PRs.

The styling stage supplies the ordinary road width separately from its bridge
decoration. For `highway|<class>|bridge`, cycling displacement uses the matching
`highway|<class>` Standard-style strokes, with the same theme and zoom. The full
bridge drawing rules are still rendered unchanged. Cycling indicators already
have higher priority than the decorative strokes on that feature.

The renderer uses that width for both the cycling line and its arrows. An
otherwise unchanged road therefore keeps the same pixel displacement across
the bridge transition. Centered dots retain zero displacement. Fixed smooth-
zoom spacing, equal pattern widths, side directions and outlined arrows are
preserved. A real change in road class or cycling tags can still change the
treatment; this does not invent continuity across different infrastructure.

The regression checks compare ordinary/bridge pairs across road classes,
light/dark Standard and Cycling modes, selected zooms from 14 through 20, all three cycling
patterns and multiple pixel densities. They also assert that bridge decoration
is still drawn and remains below the cycling indicator.

## Installed revision

Revision `71aaa9aa1b09a2a5fb2bbaf7ef0e8527a4bc7a4b` was built, installed and
launched in the isolated `OM Side Offsets` app. All 33 focused native tests and
nine tooling tests pass. The fixture map checksum was verified on the phone;
no automated screenshot verification was performed.

`bridge-continuity-checks.json` records the installed APK/native/map hashes and
test evidence. Heavy jobs ran sequentially with a 1800 MiB cap and no swap
allowance. The local APK and manifest are under
`build-visual-artifacts/bridge-continuity/phone.apk` and `phone.json`.
Binaries and fixture maps are not committed. This remains a prototype, not
upstream approval or a claim that every bridge configuration has been tested.
