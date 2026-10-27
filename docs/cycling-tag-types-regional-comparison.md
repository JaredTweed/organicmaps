# Controlled cycling representation comparison

## Conclusion

The separate-type candidate is the better of the **two prototypes tested** if
older type mappings must still recognize the road. It retains the existing road
type, whereas the naive combined-type prototype replaces it with an unknown
type. This is not yet a universal winner: dual-writing or gating combined types,
other representations, full routing, different regions and release rendering
performance were not tested. It also does not establish visual equivalence to
PR #12692 or require any change to that PR's appearance.

## Method

The same road-only Vancouver OSM extract was annotated once with a small,
synthetic cycling category and processed with the same generator and settings.
The annotations cover only eight road classes and unambiguous positive track,
lane or shared-lane values. They are an experimental input, not a proposed OSM
normalization policy. The candidates were:

* **Separate type:** keep the highway type and add an `hwtag|research_*` type.
* **Combined type:** replace the highway type with a road-class-specific
  `highway|...|research_*` subtype.

Both use generated synthetic Outdoors rules, not the PR's actual cycling
rules. The generated MWMs contain geometry and index sections, not full
search, routing, access or production map content. A second, downtown bounding
polygon overlaps the first extract; it is not an independent region.

The annotated source SHA-256 is
`6d09f0b6df237933b9ade859c6c39a77ce71221991ff1f05fdc44b9b6a007948`.
Full machine-readable results, checksums and one-run timings are in
[`cycling-tag-audit/regional-vancouver-results.json`](cycling-tag-audit/regional-vancouver-results.json),
[`cycling-tag-audit/regional-urban-results.json`](cycling-tag-audit/regional-urban-results.json)
and [`cycling-tag-audit/regional-compat-results.json`](cycling-tag-audit/regional-compat-results.json).
The accompanying scripts document the commands and are research tooling only.

## Results

| Measurement | Separate type | Combined type |
| --- | ---: | ---: |
| Vancouver feature count | 82,785 | 82,785 |
| Features with a research category | 890 | 890 |
| Vancouver MWM bytes | 2,386,179 | 2,384,838 |
| Downtown MWM bytes | 2,235,526 | 2,234,373 |
| Synthetic merged drawing rules bytes | 223,764 | 231,989 |
| Vancouver features recognized as highway by baseline mapping | 79,690 | 78,808 |

Category counts match: 252 lane, 626 shared lane and 12 track in Vancouver;
190, 573 and 12 respectively in the overlapping downtown polygon. Aggregate
existing `hwtag` and `psurface` counts match, and both candidates logged the
same two pre-existing type-overflow warnings. Aggregate counts do not prove
per-feature equality or routing equivalence. A separate type consumes another
slot: the Vancouver separate-type map has 17 eight-type features, while the
combined map's maximum is seven. The sample is too limited to establish global
overflow risk.

The compatibility experiment uses the current reader with the pinned baseline
type mapping, not an actual historical app. In this test 882 highway features
lose recognition under the naive combined mapping, while the separate-type
candidate retains the same aggregate highway count. This is a real issue for
that encoding, not proof that every combined-type migration must fail. An
unknown added type does not guarantee complete compatibility either.

## Phone and remaining work

Pixel 8 Pro research APKs and maps were prepared and attempted on-device.
Neither attempt produced a valid viewport comparison. The first used a map
version different from the catalogue; the second matched the catalogue date
but the synthetic map's size differed from the official catalogue entry. The
debug app aborted its map consistency check. An intermediate attempt caused
the isolated research app to download an official map; it was stopped, and the
download was moved to the research app's private archive. No timings from these
runs should be used as performance results.

For a valid phone run, create a research-only catalogue matching each generated
map's version **and byte size**, verify the actually loaded MWM and generated
style, then compare identical viewports and rendering output on the same device.
Use repeated runs, a release-like build and controlled thermal/cache conditions
before drawing a performance conclusion. Also test older and newer actual app
versions, mixed maps, per-feature retained types, routing/access, and multiple
independent full OSM regions. Until then, the preferred separate-type approach
is conditional and the requested full comparison is incomplete.
