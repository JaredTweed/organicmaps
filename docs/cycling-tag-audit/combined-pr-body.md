## Combined Integration Preview

This is the combined preview of the eight-part cycling stack, now using the author-approved **OM Test gray-road/reduced-clutter presentation**. It targets `ab/cycling-style`, not master. Head `fd7b8f32d3` has the same file tree as final style topic #14043 at `3ab7ff9e66`. This is not approval to release the experimental data formats or rendering policy.

## Presentation

- Neutral gray car-road hierarchy and subdued buildings in light/dark themes.
- Reduced routine POI icons, minor street labels and addresses at overview zooms, with close-up detail restored. Bicycle shops and existing cycling services remain available.
- Ordinary road cores plus narrow attached track/lane indicators; shared-lane dots remain centered. Three cycling patterns remain: solid track, dashed lane, dotted shared lane. These represent mapped facility categories, not guaranteed safety or pavement quality.
- Cycling colors, widths, offsets, one-way arrows, fixed screen-space gaps and topology-backed junction tapers are unchanged by the quiet-style revision. Rendering hints do not create routing connections or assert marked crossings.
- **Scope caveat:** the OM Test design changes shared default palettes as well as cycling presentation. Other styles inherit some default colors; this is not a cycling-mode-only patch. Maintainers still need to agree the final product boundary.

## Review Units

1. #14040: selector membership.
2. #14041: cycling classification/access flags.
3. #14048: optional metaline phase data while retaining the legacy section.
4. #14042: continuous phase rendering.
5. #14074: side-aware data in an optional `cycling_infra` section.
6. #14075: topology-backed junction generation.
7. #14076: offset/taper/clipping/arrow geometry.
8. #14043: style selection and integrated presentation.

Independent #14054 owns permissive motor access. The master-based dependent PRs are cumulative, not isolated upstream stacked diffs; review their linked topic ranges and integrate sequentially or with agreed upstream base refs.

## Validation and Limits

The quiet style's generated files match the installed OM Test experiment byte-for-byte. The matching final style head passes 193 full indexer and 46 focused renderer tests; 79 research tests pass. Line-rule comparison preserves geometry across all four families and both themes, plus cycling colors/patterns/symbols. Classifier mappings, map data and native code are unchanged by this visual revision. Source and generated assets are separate signed commits.

Phone screenshots are spot checks on the existing road-only Vancouver fixture, not evidence of full building/POI density, controlled pixel equality or region-wide routing correctness. Full-map/coastline generation is separate work and is not included here. Historical 556/542 native results retain their earlier source pins; they are not new exact-head runs for this styling update.

See [the promotion report](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/quiet-style-promotion.md). Review of model/schema compatibility, rendering and generator performance, the broader default-style effect, CI, and eventual master integration remains required. Earlier approvals do not establish review of these new changes.

The original head `955cd49403` is preserved on [`backup/pr-12692-before-split`](https://github.com/JaredTweed/organicmaps/tree/backup/pr-12692-before-split); subsequent integration history is retained without force-pushing.

Prepared with Codex (LLM) assistance; original authorship is retained.
