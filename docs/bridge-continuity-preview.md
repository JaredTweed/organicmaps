# Bridge continuity preview

Local branch: `demo/cycling-bridge-continuity`, based on the fixed-screen-gap
prototype. This trial is not pushed to GitHub and does not change #12692 or
the split PRs.

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
light/dark Standard and Cycling modes, zooms 14 through 20, all three cycling
patterns and multiple pixel densities. They also assert that bridge decoration
is still drawn and remains below the cycling indicator.
