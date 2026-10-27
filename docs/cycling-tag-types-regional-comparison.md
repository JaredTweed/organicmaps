# Controlled cycling representation comparison

## Conclusion

**Best overall recommendation for the current centerline cycling style: keep
the road's existing primary type and use one separate, normalized cycling
attribute type.** This is an informed engineering judgment, not a proven
universal winner. It gives the clearest compatibility advantage in the tested
comparison, avoids multiplying types by road class, and has a small measured
map-size cost. The evidence also shows potential selector cost and type-slot
pressure, so release approval should depend on those checks below.

The separate-type candidate retains the existing road type, whereas the naive
combined-type prototype replaces it with an unknown type. Dual-writing or
gating combined types, other representations, full routing, different regions
and release rendering performance were not tested. This recommendation does
not establish visual equivalence to PR #12692 or require any change to that
PR's appearance.

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

On a later attempt, research-only catalogues were rebuilt with the matching map
sizes and both candidate maps loaded on the Pixel 8 Pro. Both nine-viewport
OpenGLES debug scenarios completed. However, the generated tag style does not
preserve ordinary roads: its compiled rules (for example `highway-living_street`
at z14) place the base line and label inside each `extra_tag` predicate, with
no equivalent unconditional rule at that zoom. On-screen captures show major
differences between candidates. Consequently the two timing sequences in
`regional-phone-tag-result.json` and `regional-phone-combined-result.json` are
**invalid for deciding relative rendering performance**: they measure different
rendering workloads. They are single debug runs, not release benchmarks. The
candidate styles are synthetic and neither alters the PR.

An explicit no-cycling-tag fallback was then added to the synthetic tag fixture
and recompiled. Both variants completed two alternating nine-viewport runs on
the same Pixel, OpenGLES and debug build. The inspected z14 screenshots show
the previously missing ordinary roads restored and appear close, but this is
not a pixel-perfect verification of all zooms or the actual PR style. Across
the 18 recorded viewport-ready times per candidate, the medians were 309.7 ms
for combined and 366.2 ms for tags, approximately 18% higher for tags. These
are small, sequential debug samples with uncontrolled caching and thermal
state; viewports are not independent samples, so this is a warning about the
selector path, not a production-speed estimate or proof of a fixed 18% cost.
The corrected fixture uses three negative predicates for the fallback; a better
compiler or selector implementation could have a different cost. The original
combined trace and the corrected tag and repeat traces are saved as JSON beside
the scripts. Single-run timings in the map-generation report remain historical
for the initial fixture; do not treat its style size as a measurement of the
corrected fallback.

Before shipping, verify equivalent output across all relevant viewports and the
actual cycling style, then benchmark repeated traces on a release-like build
with controlled thermal/cache conditions. Also test older and newer actual app
versions, mixed maps, per-feature retained types, routing/access, and multiple
independent full OSM regions. The recommendation is conditional on acceptable
selector performance and avoiding loss of routing-critical types.
