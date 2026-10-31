# Solid-arrow outline preview

Branch: `demo/cycling-solid-arrow-outline`, based on
`prototype/cycling-thin-offsets-shared-centerline`. This is a saved phone
experiment, not a PR or a change to the split stack or #12692.

Only `cycling-arrow-solid-xs/s/m` change. Their existing white/light-theme
and black/dark-theme fills retain their geometry and scale. A rounded outline
is drawn beneath the fill, using the solid cycling line's color:
`#0D47A1` in light mode and `#90CAF9` in dark mode. The SVG stroke is 0.6 view
units; the exposed border is approximately 0.2 logical pixels per side.
The viewport gains one logical pixel of padding without scaling the arrow
body, preventing the outline from being clipped.

Shared-lane dots remain centered; lane/track indicators remain offset.
Stroke widths, direction selection, routing, classifier data and renderer
code are unchanged. Dashed/dotted arrow symbols are untouched.

## Generated assets and checks

The six SVG sources and all twelve light/dark density atlases are saved here.
Atlases were regenerated with the repository's `skin_generator_tool`, one
at a time under a 1800 MiB memory cap and with no swap allowance. Its generator
source matched this checkout. The regular symbol-generation workflow can
rebuild these assets; keep generation sequential and memory-limited.

Per-symbol comparisons cover 864 symbols per atlas. Exactly the three solid
arrow sizes change in each of twelve profiles; every unrelated symbol is
pixel-identical, even where atlas packing positions change. All 36 outlined
glyphs contain visible blue contour pixels. See
`solid-arrow-outline-checks.json` for source/asset hashes and checks.

The preview APK was installed and launched in the isolated `OM Side Offsets`
app. Its renderer is the shared-centerline revision `63975ebfa4`; only the
24 atlas PNG/XML entries and signing metadata differ from that installed base
APK. Map data and all other APK contents are unchanged. Binaries and local
fixture maps are not committed. The earlier 29 native and eight tooling checks
belong to the unchanged renderer; the outline change is validated by the asset
and package comparisons, not a new native test run.
