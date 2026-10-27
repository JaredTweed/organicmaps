# Cycling infrastructure: feature types and tag-like attributes

Research for [PR #12692](https://github.com/organicmaps/organicmaps/pull/12692)
and [the maintainer's request](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6400762580).
This is a design discussion, not a proposal to ship a map format or a completed
benchmark. Source inspection is pinned to upstream master
[`936c7834fb`](https://github.com/organicmaps/organicmaps/tree/936c7834fb),
cycling-style base [`7af82a316a`](https://github.com/organicmaps/organicmaps/tree/7af82a316a),
and experimental PR head [`955cd49403`](https://github.com/JaredTweed/organicmaps/tree/955cd49403).
The latter two are different branches; comparisons below are explicitly scoped.

## Recommendation

Update after reviewing the independent solution: see
[the decision audit](cycling-tag-types-decision-audit.md) for corrections,
reproducible checks, alternatives, and coverage of all three maintainer requests.
For a centerline-only first version, prioritize testing one derived cycling
attribute alongside a generated-combination baseline. This is a prototype
priority, not a release verdict. Keep existing designated path types intact
until decomposition's extra slot and compatibility costs are justified.

Keep the road's primary classifier type and model **side-qualified cycling
attributes** independently of the road class when side fidelity is required.
A strong candidate for a
side-aware design is a small, structured record per side, because it preserves
the relationships without consuming one classifier slot for every attribute.
For a narrower centerline-only first version, evaluate one derived
cycling category as an additional classifier type. Do not ship either encoding
until representative maps establish type-slot pressure, size, speed, rendering
correctness, and upgrade behavior. The decision about whether the extra detail
is actually needed belongs with the product and renderer design.

Separate attributes avoid duplicating every cycling combination under every
highway class. They do not automatically solve the current eight-type limit,
correlate properties on opposite sides, or make existing styling rules match a
combination. A compact, versioned side record is a candidate for richer data;
it has more implementation and compatibility cost and is not yet justified by
measurements. A limited set of side-qualified classifier types is another
candidate worth measuring before a format change; existing per-feature metadata
is also a reuse baseline, not a POI-only mechanism. This is the strongest
conditional recommendation supported by the evidence; calling one option the
best overall before the benchmarks and product requirements are known would be
unjustified.

## What the current code actually does

* A feature already carries multiple classifier types. Its feature header
  allocates three bits to the type count, so it holds **one to eight types**.
  Each type is stored as a variable-length integer index into the app's
  `types.txt` mapping. See
  [feature_data.hpp](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/feature_data.hpp#L21),
  [serialization](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/feature_data.hpp#L273), and
  [types mapping](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/types_mapping.cpp#L12).
* When more than eight types are produced, the generator sorts by its existing
  usefulness rules and truncates them. This is a correctness risk for cycling
  attributes **and existing attributes**, not merely a size question. The
  experimental PR ranks `cyclewaytag` among lower-priority types; inspect the
  full combination, including routing tags, when evaluating overflow.
  [Upstream truncation](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/feature_data.cpp#L464),
  [experimental priority](https://github.com/JaredTweed/organicmaps/blob/955cd49403/libs/indexer/feature_data.cpp#L139).
* `hwtag` and `psurface` already act as tag-like classifier families. They are
  retained for line features even without ordinary drawing rules; adding a new
  family requires equivalent attention to filtering and indexing. The
  experimental branch does this for `cyclewaytag`.
  [Upstream filtering](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/feature_visibility.cpp#L164),
  [experimental filtering](https://github.com/JaredTweed/organicmaps/blob/955cd49403/libs/indexer/feature_visibility.cpp#L166).
* Style lookup gathers rules for each feature type separately, then applies
  runtime selectors and resolves rule priorities. Merely attaching two types
  does not by itself define a rule for their conjunction. The experimental PR
  adds an `extra_tag` runtime selector to test another classifier type; upstream
  at the pinned revision contains a commented-out older `TypeSelector`.
  [Stylist](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/drape_frontend/stylist.cpp#L213),
  [experimental selector](https://github.com/JaredTweed/organicmaps/blob/955cd49403/libs/indexer/drules_selector.cpp#L117).
  The full MapCSS-to-rule pipeline and interactions with priority, visibility,
  and indexing still need testing for any proposed generalized selector.
* The experimental generator assigns one `cyclewaytag` category per road,
  choosing the least protected explicitly tagged category when sides differ.
  This is a deliberate centerline summary, not a representation of which side
  has which facility. It cannot later reconstruct the original side details.
  [Experimental generator](https://github.com/JaredTweed/organicmaps/blob/955cd49403/generator/osm2type.cpp#L1112).
* Bicycle routing already consumes classifier information such as
  `hwtag=yesbicycle`, `nobicycle`, `nocycleway`, and bicycle direction. Road
  access and conditional access have separate generation paths. Drawing and
  routing therefore need a shared interpretation of the source data, but a
  visual category is not automatically sufficient to make routing correct.
  [Bicycle model](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/routing_common/bicycle_model.cpp#L178),
  [access generator](https://github.com/organicmaps/organicmaps/blob/936c7834fb/generator/road_access_generator.cpp#L42).

## The association problem

Consider a way whose OSM direction runs from node A to node B:

| Input | Required information if sides are shown |
| --- | --- |
| `cycleway:left=track`, `cycleway:right=lane` | Left is a track; right is a lane. |
| `cycleway:left=lane`, `cycleway:right=track` | Left is a lane; right is a track. |
| `cycleway:left=lane`, `cycleway:right=lane`, with differing direction restrictions | Two lanes, with the direction associated with the correct side. |
| `cycleway:left=no`, right unspecified | Explicit absence on the left; unknown on the right. |

The unordered set `{left, right, lane, track}` is identical for the first two
rows and cannot distinguish them. The set `{left-lane, right-track}` can;
another independent direction flag is still ambiguous if both sides differ.
Use side-scoped values or side-scoped records to preserve these associations.
`both`, generic `cycleway=*`, conflicting tags, and missing values need an
explicit precedence policy, with unknown distinguished from `no`. Left/right
are relative to the OSM way direction: any geometry reversal, splitting,
merging, or routing direction transformation must preserve that relationship.
The generator already reverses geometry for `oneway=-1`: see
[osm2type.cpp](https://github.com/organicmaps/organicmaps/blob/936c7834fb/generator/osm2type.cpp#L1124),
[feature_maker.cpp](https://github.com/organicmaps/organicmaps/blob/936c7834fb/generator/feature_maker.cpp#L112)
and [feature_builder.cpp](https://github.com/organicmaps/organicmaps/blob/936c7834fb/generator/feature_builder.cpp#L96).
If attributes are relative to the stored geometry, reversal must swap left and
right **and** invert forward/backward directional values. Apply the transform
once and test it; avoid doing it independently in multiple consumers.

OSM's [cycleway documentation](https://wiki.openstreetmap.org/wiki/Key:cycleway)
defines side relative to the drawn way and documents side-specific direction.
Its [separation documentation](https://wiki.openstreetmap.org/wiki/Key:cycleway:separation)
also illustrates why a barrier's presence alone is not always enough: the
adjacent traffic mode and which edge of the facility is separated matter.
Unknown, unspecified, and contradictory inputs should not be presented as
verified safety or legal access. Country-specific traffic rules and conditional
restrictions belong in the established access/routing policy, not assumptions
baked into a visual enum.

Offset drawing also needs more than storage: define side placement at curves,
intersections, clipping and tiles, bridges/tunnels, dashed lines, zooms, and
lane direction arrows. Road-center routing may continue to use the existing
graph, but separate OSM cycleway geometries are separate features and must not
be confused with road-attached lanes or double counted. A side record alone
does not solve crossings, turn restrictions, connectivity, or access.

## Options

| Representation | Advantages | Costs and risks |
| --- | --- | --- |
| Combined hierarchy, e.g. road class + every cycling combination | Fits the existing per-type rule lookup; a single type can represent an associated combination. | Multiplication of classifier entries and rules by road class, side, facility, and direction; difficult fallback and consistency; may displace existing road types and break consumers. Generating duplicated rules with an LLM does not remove binary size, data growth, semantic consistency, or runtime costs. |
| One tag-like type for a centerline summary, as in the experimental PR | Small change; reuses feature types, supports an understandable initial cycling style; does not multiply by road class. | Loses side and direction detail; adds type-slot and mapping pressure; requires explicit matching/priority rules and legacy policy. Does not provide detailed routing semantics. |
| Side-qualified tag-like classifier types, e.g. `left-track`, `right-lane` | Associates facility with side; uses existing type infrastructure and can be independently selected. | Two or more slots per road; adding per-side direction, access and protection consumes further slots or creates combinations inside the tag namespace. Must define conflict and retention policy and evaluate renderer overhead. |
| Structured, versioned side attributes, inline or in a separate feature-ID-indexed section | Can represent correlated fields without multiplying by road class or using many classifier slots; potentially reusable for sidewalks. | New generator, storage, lookup, renderer, tests, and migration work. Sparse and inline layouts have different overheads; old-app/new-map behavior depends on the chosen format. Requires a clear ownership and lifecycle contract for feature IDs. |

These are design alternatives, not measurements of final map size or speed.
For illustration only, four side states (unknown, none, lane, track) yield
16 ordered left/right pairs before adding direction or access; across eight
road classes that is up to 128 road/pair combinations. Real combinations may
be sparse and generators can share style declarations, so this is an upper
bound for this toy model, not an estimate of real classifier growth.

## Proposed prototype contract

This contract is a design to test, not a proposed released binary layout:

* Normalize OSM tags once in the generator into a road-level record and optional
  left/right records. Each side should carry a bounded facility kind, a
  direction value (`forward`, `backward`, `both`, or `unknown`), and a
  protection classification with an explicit `unknown` state. Do not infer
  legal bicycle access merely from a painted or protected facility.
* Preserve road-level or side-unspecified facts as such. A bare `cycleway=*`
  does not necessarily establish which side; never manufacture left and right
  values just to simplify drawing. Keep bicycle roads and separate bicycle ways
  distinct from attached lanes. Normalize `both` only where its semantics are
  unambiguous, and document precedence for conflicting keys.
* Keep routing's existing access, oneway and conditional rules authoritative
  until a dedicated routing change is reviewed. A derived centerline category
  can be computed for the current cycling style, with explicit conservative
  behavior when the sides differ. Do not use a safety ranking as a legal rule.
* Implement the prototype behind a reader API returning a normalized view.
  Compare side-qualified classifier IDs with a sparse, versioned side section;
  add a section-local version, defined unknown values, bounds checks, and an
  explicit behavior for missing or unsupported versions. A separate section is
  only a candidate: verify how old clients and download policy behave.
* If indexed by feature ID, write the section against the **final** feature IDs
  of the same MWM. The generator sorts features before collection; IDs cannot be
  carried blindly from pre-sort temporary features or between map generations.
  See [feature_sorter.cpp](https://github.com/organicmaps/organicmaps/blob/936c7834fb/generator/feature_sorter.cpp#L360).
  Measure sparse index, offsets, per-record bytes, and lookup/cache costs rather
  than assuming the payload alone is the full cost.
* Restrict any drawing change to the cycling style at first. A road-level
  summary can be displayed on the centerline; offset geometry and per-side
  rules require independent visual, clipping, merge, and performance tests.
  Keep the normal style and current routing behavior as regression baselines.

### Compatibility issue found in the current branches

At the pinned experimental head, `types.txt` assigns indices 1657 and 1658 to
`cyclewaytag|track` and `cyclewaytag|lane`. At pinned upstream master, those
same indices represent `railway|station|subway|suzhou` and
`railway|subway_entrance|suzhou`, respectively. This is branch divergence, not
evidence that released production maps are corrupted. However, a map generated
with one mapping and read with the other can silently resolve those *valid*
indices to unrelated types; the invalid-index-to-stub fallback does not catch a
valid collision. Before any experimental map is distributed or the work is
rebased, reconcile type IDs against the authoritative mapping, establish which
map snapshots may already use them, and test both version directions. Reassigning
an experimental ID itself can require migration for any already-shared maps.
[Experimental mapping](https://github.com/JaredTweed/organicmaps/blob/955cd49403/data/types.txt#L1658),
[upstream mapping](https://github.com/organicmaps/organicmaps/blob/936c7834fb/data/types.txt#L1658).

## What can be quantified now

In experimental PR head `955cd49403`, the three `cyclewaytag` entries are at
indices 1657, 1658, and 1659 in `data/types.txt`. Each index uses **two bytes**
as an unsigned varint. Thus, adding one such type to a feature that otherwise
keeps exactly the same types adds two bytes to its serialized type list; adding
two similarly indexed types adds four. This is a local serialization estimate,
not the change in a whole MWM: overwritten/dropped types, indexes, compression,
section overhead, feature counts, and changed routing data all affect totals.
If the feature has eight types already, this estimate does not apply unchanged.

For context, the checked-in `data/drules_cycling.bin` is 224,085 bytes at the
cycling-style base and 230,496 bytes at the experimental head, a difference of
6,411 bytes (about 2.86%). `drules_merged.bin` increases by 2,095 bytes. These
are **whole-branch artifact comparisons**, including unrelated style and rule
changes; they do not isolate the cost of any one encoding or selector and are
not MWM-size measurements.

No representative map-size, type-overflow, generation-time, renderer-time,
or routing benchmark has been run for this document. Do not infer a winner on
performance from the estimates above.

### Existing Vancouver MWM: decoded type counts

As a limited baseline, an existing local `Vancouver.mwm` was read with the
existing release `generator_tool --dump_types` and a local resource directory.
The tool and map's exact build provenance and mapping compatibility have not
been independently verified. This counts **decoded, already-generated features**, not OSM ways
before filtering or truncation. `highway` is a classifier-family proxy and can
include non-road geometries; `hwtag|yesbicycle` is not a definitive cycling
infrastructure label. The tool and mapping are from the older local checkout,
not a controlled build of either pinned comparison branch; map generation
provenance and source snapshot were not established. Results are illustrative
only, not an A/B comparison or representative regional estimate.

| Stored type count | All features | Features with a `highway` type | `highway` plus `hwtag|yesbicycle` |
| ---: | ---: | ---: | ---: |
| 1 | 1,573,640 | 194,731 | 0 |
| 2 | 178,552 | 145,359 | 3,519 |
| 3 | 60,230 | 56,546 | 16,107 |
| 4 | 29,727 | 28,822 | 14,253 |
| 5 | 11,430 | 11,090 | 5,133 |
| 6 | 1,496 | 1,400 | 1,003 |
| 7 | 176 | 145 | 74 |
| 8 | 29 | 6 | 6 |
| Total | 1,855,280 | 438,099 | 40,095 |

Of the `highway` proxy group, 151 (0.0345%) already have at least seven
stored types; among the `yesbicycle` subset, 80 (0.1995%) do. Seven matters
when considering **two additional** classifier types, eight when considering
**one**. These are not predicted overflow counts: existing type replacement,
different candidate coverage, and prior truncation all change the result.
Conversely, an eight-type result can already have discarded other types.

Reproduction, with the same local files and tool:

```sh
generator_tool --data_path=MAP_DIR --user_resource_path=RESOURCE_DIR \
  --output=Vancouver --dump_types > vancouver-types.txt
awk 'NF > 1 && $1 ~ /^[0-9]+$/ {
  n = NF - 1; highway = 0; bicycle = 0
  for (i = 2; i <= NF; i++) {
    if ($i ~ /^highway\|/) highway = 1
    if ($i == "hwtag|yesbicycle|") bicycle = 1
  }
  all[n] += $1
  if (highway) road[n] += $1
  if (highway && bicycle) bike[n] += $1
} END {
  for (n = 1; n <= 8; n++) print n, all[n]+0, road[n]+0, bike[n]+0
}' vancouver-types.txt
```

The inspected map SHA-256 is
`51e18ad39f64e70db8edb039fd5bc53425f9ba7e393bf8735a3624a7f08a7efb`;
the executable SHA-256 is
`084b8cef85e3bf635a5e98c1f7dcb8c05bd79ff66cd197397c0377738a506b07`.
The `types.txt` used by the tool has SHA-256
`4cf21ec26215e853f98baff14c60da685337845f53efd7eb6a21e786989c1741`,
and `classificator.txt` has SHA-256
`73433ada0af7ff1d88b30e26aa73c6466c723fd617b51d8a44ee977a7b3cc701`.
The dump reports zero named features; no name-related conclusions are drawn.

## Experiment before choosing a format

Use identical OSM snapshots, generator settings, style assets, and compiler
settings for all variants. Include at least an urban area with asymmetric and
protected lanes, a rural area with sparse infrastructure, and a region with
different mapping conventions. Compare current base, centerline tag type,
side-qualified types, and a deliberately minimal structured-record prototype.
Generate maps with each implementation; record exact commits, input checksums,
map versions and commands so the comparison can be reproduced.

1. Instrument before `FinishAddingTypesEx()` truncates: histogram total types
   per line feature; count affected cycling features at 7, 8, and >8 types;
   report every lost type family, especially access, direction and surface.
   Compare resulting features after filtering and truncation, not just source
   OSM ways. Report coverage and examples of lost information.
2. Measure total MWM bytes and relevant section bytes, feature count, generated
   rules and app assets, generation time and peak memory. Report absolute and
   percentage deltas. Separate a format's fixed overhead from per-feature cost.
3. Measure decoding and style selection for representative viewport traces,
   with cycling and normal styles, cold and warm caches, on a real phone.
   Report median and tail tile preparation/frame times, memory, and sample
   counts; repeat and keep hardware, zooms and locations fixed. Compare ordinary
   roads as well as cycling-dense roads so generalized selectors' cost is visible.
4. Check fixtures for asymmetric sides, `both`, direction and oneway, explicit
   `no` versus missing, conflicts, separated ways, geometry reversal, and
   feature splitting. Add end-to-end generator-to-style tests and visual
   comparisons across tile edges, zooms, and light/dark styles. Test that the
   normal map's draw rules and visibility do not regress.
5. Run bicycle-routing and access regression tests, including oneway and
   conditional restrictions, and verify any new attributes survive filtering
   without changing existing access behavior. Test pedestrian compatibility if
   the representation is intended to be shared.
6. Test new app with old maps and new maps, and old app with new maps, including
   mixed map versions, missing/unknown data and style fallback. Unknown type
   indices are currently converted to a stub by
   [FeatureType::ParseTypes](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/feature.cpp#L281);
   this alone does **not** prove full compatibility. Determine the release and
   downloader version policy and whether old readers can safely skip a proposed
   new section or must reject the map. A feature-header layout change is a
   separate format migration concern.

## Decisions for maintainers

* Is centerline classification sufficient for the first released cycling map,
  or are asymmetric sides and directions required now? What are the intended
  rendering and routing behaviors when source tags conflict or are missing?
* Which semantics must routing consume, and which are only visual? Should
  sidewalks share a general attribute representation or merely its framework?
* Is a constrained side-qualified type vocabulary acceptable under measured
  slot pressure, and how should important routing attributes be protected from
  truncation?
* Can the existing experimental runtime selector and MapCSS generation be
  generalized without unacceptable rule duplication or hot-path costs? What
  is the intended offset renderer and priority model?
* What MWM compatibility and release guarantees apply before introducing new
  types or a new section? Which prototype and benchmark results are sufficient
  to choose between the options?
