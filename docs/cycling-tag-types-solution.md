# Cycling tag types: recommended solution

Companion to
[`docs/cycling-tag-types-research.md`](cycling-tag-types-research.md).
That document collects the evidence and caveats. This one answers the design
question directly for
[PR #12692](https://github.com/organicmaps/organicmaps/pull/12692) and
[the maintainer's request](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6400762580):
which types should become tag-types, whether a broad tag system is justified,
and what should be built first.

This is a design recommendation, not a map-format proposal and not a completed
benchmark. It is scoped to the pinned revisions used by the companion document:
upstream master `936c7834fb`, cycling-style base `7af82a316a`, and experimental
head `955cd49403`.

## Short answer

Adopt tag-types, but as a **narrow, derived-attribute mechanism**, not as a
general decomposition of OSM key/value pairs.

* Keep the road's primary type, for example `highway|tertiary`.
* For the first cycling release add **one** normalized attribute type per
  feature: `cyclewaytag|track`, `cyclewaytag|lane`, or
  `cyclewaytag|shared_lane`.
* Do **not** add `left-*`, `right-*`, direction, access, or protection types.
  Two or more extra type slots are not justified by the current data, and they
  still do not preserve the relational side information correctly.
* If side-aware rendering becomes a product requirement, use a compact,
  versioned per-feature side record. Do not encode sides as several classifier
  types.
* As a separate pilot, decompose the two existing combined cycling types
  `highway|path|bicycle` and `highway|footway|bicycle` into their road/path
  class plus a bicycle-designation tag-type. That is the cleanest existing
  example of where the mechanism pays for itself.
* Fix the type-ID collision and the truncation priority before any generated
  map is distributed.

The rest of this document explains why, gives the concrete data contract, and
separates the low-risk first step from the larger side-aware work.

## What changed after the latest evidence

The earlier draft left the choice between one derived type and side-qualified
attributes open. The newer evidence makes the first step much clearer.

1. **A single extra type is effectively free in the measured sample, provided
   dedicated facilities are skipped.** The reproduced Vancouver type-count
   table is in the companion document. Of 438,099 features with a `highway`
   type, only 6 have eight stored types. Five of those six are already
   bicycle-designated `path` features with a bridge/tunnel subtype. The
   experimental skip only covers `highway|cycleway`; the recommended rule must
   also skip `highway|path|bicycle` and `highway|footway|bicycle`. With that
   widened rule, the sample leaves one residential feature where the new type
   could compete for a slot. This is not a global guarantee, but it is strong
   evidence that one derived type does not require a format change or a
   type-budget expansion.
2. **Two or more extra types start to cost real information.** 151 road-type
   features are at seven or more types. They are concentrated in residential,
   tertiary, trunk, service, and path/footway classes, including roads where
   cycling infrastructure matters. Adding two types on top would put many of
   them over the limit; adding three or four is a data-loss policy, not a
   storage optimization.
3. **The experimental branch's type IDs collide with upstream master.** The
   collision is described precisely below. It is a blocker for distributing
   experimental maps and a reminder that manually appended types are unsafe.
4. **The renderer work in the PR is dash-phase continuity, not side-offset
   lane drawing.** It is valuable and mostly orthogonal to the data decision.
   It does not make side-qualified type combinations cheaper to render.

The resulting opinion is:

> Use one derived cycling attribute now. Keep the road class as the primary
> type. Decompose the two existing path/footway bicycle combinations as a
> pilot. Treat side-aware rendering as a separate product decision backed by a
> side-record design, not by more classifier types.

## What "tag-type" should mean

A tag-type is an additional classifier type that represents a normalized
attribute of a feature. It is not a raw OSM key/value pair and it does not
replace the primary type.

Properties of a tag-type:

* It lives in a small, stable namespace below a known first-level type, for
  example `hwtag|yesbicycle`, `psurface|paved_good`, or
  `cyclewaytag|track`.
* It is stored as an ordinary classifier type in the feature's type list.
* It is retained for line features even when it has no drawing rule of its
  own, in the same way `hwtag` and `psurface` are retained today.
* It is excluded from primary-type selection, search categories, POI captions,
  and other code paths that expect one primary type.
* It can be tested by a style rule at runtime through the type selector
  currently called `extra_tag`.
* It has a defined retention priority so that the eight-type limit does not
  silently discard it.

Existing examples already follow this pattern:

| Namespace | Examples | Role |
| --- | --- | --- |
| `hwtag` | `yesbicycle`, `nobicycle`, `oneway`, `bidir_bicycle` | Access, direction, and routing-relevant road facts |
| `psurface` | `paved_good`, `paved_bad` | Surface quality used by routing |
| `cyclewaytag` (proposed) | `track`, `lane`, `shared_lane` | Normalized cycling facility for display |

Non-goals:

* Do not create one type per OSM key, for example `cycleway:left=lane`.
* Do not create a type for every combination of road class, side, facility,
  direction, and access.
* Do not make a tag-type carry legal access semantics that belong in the
  existing routing/access policy.
* Do not replace `hwtag` or `psurface`; they are already the de facto tag-type
  mechanism. Formalize the pattern instead of inventing a second one.

## Recommended first version: one normalized cycling type

### Type paths

Add exactly three values under one namespace:

```text
cyclewaytag|track
cyclewaytag|lane
cyclewaytag|shared_lane
```

No type means “no positive cycling-facility information was available for the
centerline,” not “bicycles are forbidden.” Explicit `cycleway=no` is not
represented as a separate type in this version; it affects routing and may
affect nothing visually. That distinction is deliberate: do not turn absence
or prohibition into a facility overlay.

### Meaning

| Type | Intended meaning |
| --- | --- |
| `track` | Physically separated or protected cycling facility: cycle track, protected lane, or a lane promoted to track because separation from motor traffic is positively tagged. |
| `lane` | Painted or buffered on-road cycle lane without confirmed protection from adjacent motor traffic. |
| `shared_lane` | Shared lane, shared busway, shoulder, bicycle road, or cyclestreet where bicycles share space with other traffic. |

These are rendering categories, not safety ratings and not legal access
classes. A painted lane is not “safer” than a shared lane in every country and
context, and a protected facility does not imply that every cyclist may use it.
Keep routing's existing access, oneway, and conditional rules authoritative.

### Generator contract

Normalize once, in `generator/osm2type.cpp`, after the existing access and
oneway processing:

1. Read `cycleway`, `cycleway:both`, `cycleway:left`, `cycleway:right`,
   `cycleway:forward`, `cycleway:backward`, and the corresponding `:lane`
   values.
2. Map the positive facility values:
   * `track`, `opposite_track`, `protected_lane` → `track`
   * `lane`, `opposite_lane`, `buffered_lane` → `lane`
   * `shared_lane`, `share_busway`, `opposite_share_busway`, `shoulder` →
     `shared_lane`
   * `:lane=exclusive` → `lane`
   * `:lane=advisory`, `:lane=pictogram` → `shared_lane`
3. A `lane` becomes `track` only when positive separation or protection from
   adjacent motor traffic is confirmed on the relevant side. The experimental
   code's `separation`, `barrier`, and `traffic_mode` checks are a reasonable
   starting point; keep them conservative and test them.
4. `bicycle_road=*` and `cyclestreet=*` map to `shared_lane` unless a more
   specific cycling facility is tagged.
5. Do not add `cyclewaytag` to features whose primary type already expresses a
   dedicated facility, for example `highway|cycleway`,
   `highway|path|bicycle`, or `highway|footway|bicycle`. The primary type is
   already the facility. Note that the experimental
   `IsBicycleDesignatedHighway()` check only covers `highway|cycleway`: it
   truncates to the two-level highway class, so `highway|path` and
   `highway|footway` do not match. Widen that check or add explicit
   path/footway-bicycle cases before relying on it.
6. When sides differ, choose the least-protected explicitly tagged facility for
   the centerline summary. Document this as a lossy visual rule. Do not claim
   it describes the left or right side.
7. When tags conflict, apply a documented precedence: specific side over
   `cycleway:both` over generic `cycleway`; explicit negative values suppress
   a positive facility; unknown is not the same as `no`. Keep `opposite_*`
   values as bidirectional routing information, not as a separate visual type.
8. Do not infer bicycle access from a painted or protected facility. Continue
   to let `hwtag`, `oneway:bicycle`, access tags, and conditional restrictions
   drive routing.

The exact precedence table needs generator tests with the following cases:

* left track, right lane;
* left lane, right track;
* `cycleway:both` with a side-specific override;
* explicit `no` on one side, unspecified on the other;
* `opposite_lane` and `opposite_track` on a oneway road;
* protected lane with and without an adjacent `traffic_mode`;
* `bicycle_road` and `cyclestreet`;
* a dedicated `highway=cycleway` that also has `cycleway=*` tags;
* conflicting positive and negative tags.

### Why one type, not side-qualified types

A side qualifier needs one additional type per side, so two for a road with
facilities on both sides, and often more:

* `cyclewaytag|left_track`, `cyclewaytag|right_lane` already consume two
  slots.
* Direction restrictions need another relation or combined values such as
  `left_track_forward`.
* Protection, access, and conditional restrictions add more dimensions.
* The feature type list is a set: it has no slot that means “left” or “right.”
  The association between a side, a facility, and a direction is relational.
  A flat set of types preserves the values but not the relationship.
* The renderer still has to draw two parallel geometry lines. The type data
  alone does not solve offset placement at curves, intersections, bridges,
  clipping, or tile boundaries.

One type plus the primary type is a better first version because it fits the
existing budget, keeps the style simple, and can be shipped without a map
format change. It is intentionally lossy; that is acceptable for a
centerline-only cycling style.

### Style duplication does not replace the data model

Generating duplicated style rules, with an LLM or otherwise, can reduce
authoring effort, but it is not an argument against a tag-type layer:

* Duplicated rules multiply generated rule count and binary size.
* Fallback and priority become harder to reason about when every combination
  has its own rule.
* Duplication does not solve the eight-type budget, the left/right association,
  the direction relation, or offset rendering.
* Changing one semantic rule then requires regenerating and auditing every
  duplicate.

Use generation for mechanical variants after the data model is fixed. Do not
use it as a substitute for deciding what information the map stores.

## Existing combined types: the best decomposition pilot

There are two existing combined cycling types in `data/types.txt`:

```text
highway|path|bicycle
highway|footway|bicycle
```

They are a clean one-dimensional combination of a path class and a bicycle
designation. They are the best candidates for the maintainer's proposed tag
system because they demonstrate the mechanism without sides or direction.

Recommended pilot:

```text
highway|path|bicycle     -> highway|path     + bicycletag|designated
highway|footway|bicycle  -> highway|footway  + bicycletag|designated
```

The exact namespace name is a maintainer decision; `bicycletag`,
`hwtag|bicycle_designated`, or a documented extension of `hwtag` would all
work. What matters is the shape: one primary class plus one attribute type,
matched by the style selector.

Why this pilot is useful:

* It directly answers “which existing types should become tag-types?”
* It removes two combined types instead of adding more.
* It proves the selector and visibility plumbing with a small, auditable
  surface.
* It does not touch the eight-type budget for the common case; it replaces a
  three-level combined type with a two-level primary type plus one attribute.

Costs to audit before doing it:

* All styles that match `[highway=path][bicycle=designated]` or the combined
  type, especially default, outdoors, and the new cycling style.
* Search, categories, and any code that treats the combined type as a primary
  type.
* Routing and access generation that may assume the combined type.
* The old app/new map and new app/old map behavior if the pilot ever ships.

Do this as a separate follow-up after the one-type cycling change. It is not a
prerequisite for the cycling style.

Do not convert `hwtag` or `psurface`; they already are tag-types. Do not
convert city-specific types such as the Suzhou railway types; those are
subclasses, not independent attributes.

## Type budget and truncation

`feature::kMaxTypesCount` is 8. `FeatureParams::FinishAddingTypesEx()` sorts
types with `UselessTypesChecker` and truncates the list when it is longer than
8. The experimental branch adds `cyclewaytag` to the same “low priority” group
as `hwtag` and `psurface`.

That is not a guarantee that `cyclewaytag` survives. The sorting is stable
after types are sorted by ID, and `cyclewaytag` is appended after the older
namespaces. Under pressure it can be the first score-2 type dropped. For a
display attribute that is supposed to be the point of the change, that is the
wrong default.

Recommended policy:

* Formalize an `AttributeType` classification in code, rather than scattering
  string checks. It should cover `hwtag`, `psurface`, and `cyclewaytag`.
* Give the primary type and routing/access types a protected retention rank.
  Give the selected cycling display type a rank above purely decorative
  display types.
* Add a unit fixture with eight types including `cyclewaytag` and assert that
  the cycling type survives, or document exactly which type is dropped.
* Do not rely on append order or on the experimental placement in the
  “useless” list.
* Do not expand `kMaxTypesCount` for this change. It is a feature-header format
  change with compatibility cost and is not needed for one extra type.

The Vancouver data gives the scale of the problem, not a guarantee for every
region:

| Stored types | All highway features | With `hwtag|yesbicycle` |
| ---: | ---: | ---: |
| 7 | 145 | 74 |
| 8 | 6 | 6 |

The class breakdown from the reproduced dump is more useful than the totals:

* Of the 151 features at 7+ types, 53 are `service|parking_aisle` and are not
  meaningful cycling infrastructure. The rest include 59 residential, 7
  tertiary, 4 trunk, 6 service (one with a bridge/driveway subtype), 1
  motorway link, and path/footway/bridge/tunnel combinations.
* Of the 6 features at 8 types, 5 are bicycle-designated path features with a
  bridge/tunnel subtype. The experimental skip does not cover those; the
  recommended widened skip rule does, because the primary type already
  expresses the facility. The remaining feature is residential.
* Therefore, with the widened skip rule, the one-type proposal would overflow
  at most one eligible feature in this sample. Without the widened rule, up to
  six features could compete for a slot if they carry cycling tags. A two-type
  proposal would affect a meaningful subset of residential, tertiary, and
  trunk roads.

Treat this as a reason to measure before choosing two or more types, not as a
license to ignore truncation.

## Selector and style pipeline

The experimental branch revives a type selector under the existing dynamic tag
name `extra_tag`:

```text
extra_tag=cyclewaytag=track
extra_tag!=cyclewaytag=lane
```

The C++ parser resolves the value by splitting on `=`, so the type path
components are separated by `=`, not by `:`. This is important: there is no
need to put colons in tag-type names, and no parser change is needed for
side-qualified names beyond appending more type paths.

The selector currently matches any type on the feature, not only an “extra”
type. That is useful: a style can test the primary type too, for example
`extra_tag=highway=tertiary`. The name is historical; the mechanism is a
general type predicate.

Recommended implementation:

* Enable `extra_tag` in `libs/indexer/drules_selector.cpp` with parser and
  selector tests. The type lookup should be resolved once when rules are
  loaded, not on every feature test.
* Keep the generated rule syntax stable. Kothic already emits
  `extra_tag=...`; do not invent a second selector syntax.
* Add tests for equality, inequality, a nested type path, an unknown type, and
  a feature with eight types.
* Verify that enabling the selector does not activate unrelated existing rules.
  Search generated drules for `extra_tag` before enabling it in a release.
* Keep the style non-combinatorial. One base layer per facility class plus
  conditions on road class and access is enough. Do not generate a rule for
  every road/facility combination; that is exactly the duplication the tag
  approach is meant to avoid.
* Measure the generated rule count and `drules_*.bin` size before and after.
  The current experimental `drules_cycling.bin` whole-branch delta is about
  2.86%, but it includes unrelated style and renderer changes. It is not a
  measurement of this data change.

The selector does not solve rendering. It only decides which rules apply. If a
style needs a different line width for a track on a tertiary road, the rule can
test both the facility type and the primary road type; it still draws one
centerline.

## If side-aware rendering is required

Side-aware rendering is a legitimate future product feature. It is not a
reason to add side-qualified classifier types now.

The requirements are:

* left and right are relative to the OSM way direction;
* reversing geometry must swap left/right and invert forward/backward;
* `both`, generic `cycleway`, conflicting tags, and missing values need an
  explicit precedence policy;
* unknown is not `no`;
* the renderer must place offset geometry correctly at curves, intersections,
  clipping, bridges, tunnels, and tile boundaries;
* arrows and direction indicators must agree with the side and direction;
* separate OSM cycleway geometries must not be double-counted as attached
  lanes;
* routing keeps its existing graph and access rules.

A small, versioned side record is the best fit for those requirements:

* one record per feature, indexed by the final feature ID in the MWM;
* two side entries, each with a bounded facility value, a direction value, and
  a protection/unknown value;
* compact bit-packed fields, with a section-local version and defined unknown
  values;
* bounds checks and an explicit fallback for missing or unsupported versions;
* written after feature sorting, against final feature IDs;
* measured for sparse-index overhead, per-record bytes, and lookup/cache cost.

A separate section avoids consuming two to four classifier slots and preserves
the left/right association that a flat type set cannot. It is a larger change:
new generator, storage, reader API, renderer, tests, and migration policy. Do
not start it until the product requirement and the offset renderer are
approved.

The alternative of one type per side is only worth considering if:

* the side is the only extra dimension;
* two type slots are acceptable under measured pressure;
* the renderer supports offset geometry; and
* direction and access are not needed per side.

Even then, it should be a stopgap, not the general representation.

## Compatibility and migration

### Type IDs

There are two numbering conventions, and they differ by one:

* the mapping CSV's last column is a **one-based type id** (the file header
  calls it “type id, sequential starting from 1”);
* the app loads `types.txt` in order and assigns **zero-based stored indices**.

Always state which convention is being used. The companion draft's “1657 and
1658” are stored indices; the corresponding CSV ids are 1658 and 1659.

Experimental head:

```text
CSV id 1658  types.txt line 1658  stored index 1657  cyclewaytag|track
CSV id 1659  types.txt line 1659  stored index 1658  cyclewaytag|lane
CSV id 1660  types.txt line 1660  stored index 1659  cyclewaytag|shared_lane
```

Upstream master at the pinned revision:

```text
CSV id 1658  types.txt line 1658  stored index 1657  railway|station|subway|suzhou
CSV id 1659  types.txt line 1659  stored index 1658  railway|subway_entrance|suzhou
```

Track and lane therefore collide with valid upstream types at stored indices
1657 and 1658 (CSV ids 1658 and 1659). `shared_lane` occupies stored index
1659 (CSV id 1660), which is append-only on the pinned upstream revision. A map
generated with one mapping and read with the other can resolve a valid index to
the wrong type; the unknown-index-to-stub fallback does not catch a valid
collision. This is branch divergence, not evidence that released production
maps are corrupt, but it is a release blocker for any experimental map.

Before shipping anything:

1. Rebase the experimental branch onto current upstream master.
2. Do not hand-edit `types.txt`. Rebuild it from the mapping with
   `tools/unix/generate_drules.sh`, which regenerates `types.txt`,
   `classificator.txt`, and `visibility.txt`.
3. Append the new types after all upstream entries, and verify that every new
   index is unused on the target master and any release branch that may share
   maps.
4. Discard or migrate any experimental maps already generated. Reassigning an
   experimental ID can require migration if maps escaped.
5. Test new app with old map, old app with new map, and both directions of the
   type list. `FeatureType::ParseTypes` converts unknown indices to a stub;
   that is not by itself a compatibility guarantee.

### V1 format

The one-type change is additive:

* The primary road type is unchanged, so old clients still have a road to
  render.
* Old clients may not know `cyclewaytag`; they will lose the cycling overlay
  but should still render the road.
* New clients on old maps see no cycling type and fall back to the base style.
* Truncation can still drop the new type on either side; test it explicitly.

No feature-header change and no new MWM section are required for v1.

### Future side record

A new section needs:

* a section version;
* a defined unknown value and bounds checks;
* a read path that old clients can skip;
* a download policy that does not silently mix incompatible map and app
  versions;
* tests for missing, truncated, and future-version sections.

## Acceptance criteria

For the one-type v1:

* Mapping is regenerated from source; new IDs are append-only and do not
  collide; generated `types.txt` and `classificator.txt` are committed
  together.
* Generator tests cover the precedence and side cases listed above.
* A feature with eight types that receives `cyclewaytag` keeps it, or the
  dropped type is explicitly documented and is not routing-critical.
* The cycling style renders track, lane, and shared lane distinctly at the
  intended zooms, with no effect on the normal style.
* Old app/new map and new app/old map tests pass; the primary road remains
  visible and the fallback is sane.
* Map size, generation time, `drules_*.bin` size, and tile/frame time are
  measured against the base with identical inputs and reported as absolute and
  percentage deltas.
* No experimental map is distributed before the ID audit.

For the side-record future:

* A product requirement and approved renderer design exist.
* The record round-trips asymmetric sides, direction, `both`, `no`, and
  unknown.
* Geometry reversal swaps sides and directions correctly.
* The offset renderer passes visual tests at curves, intersections, tile
  edges, bridges, tunnels, and multiple zooms.
* Routing regression tests show no change to access, oneway, or conditional
  behavior.
* The section adds measurable but acceptable size and lookup cost versus the
  one-type baseline.

## Suggested implementation order

1. **Unblock the data.** Rebase, regenerate the mapping, fix the type IDs, and
   add the collision regression test. Do not mix this with style changes.
2. **Enable the selector.** Land `extra_tag` C++ support and tests as a
   separate, style-neutral change.
3. **Land one type.** Add the generator normalization, the visibility entry,
   the retention protection, and the centerline style. Measure.
4. **Measure and review.** Use the acceptance criteria before considering more
   attributes.
5. **Pilot decomposition.** Convert `highway|path|bicycle` and
   `highway|footway|bicycle` to primary class plus bicycle-designation
   tag-type, with style and routing audits.
6. **Only then consider sides.** If the product needs asymmetric rendering,
   design the side record and offset renderer as their own project.

Keep these steps separate. The current experimental branch mixes a data model,
a selector, a style, dash-phase rendering, metalines, and shader changes. That
makes it hard to attribute size, performance, or correctness results to the
type design.

## Appendix: reproduction notes

The Vancouver type-count table in the companion document was reproduced with
the local release `generator_tool`:

```sh
generator_tool --data_path=MAP_DIR --user_resource_path=RESOURCE_DIR \
  --output=Vancouver --dump_types > vancouver-types.txt
```

The inspected map SHA-256 is
`51e18ad39f64e70db8edb039fd5bc53425f9ba7e393bf8735a3624a7f08a7efb`.
The `types.txt` and `classificator.txt` hashes match the companion document.
The executable hash in this reproduction was
`3d61cbee77dabf9f0e570a176d3f7dd28a51733232dd642f0bc06b8ec683e09f`,
which differs from the hash recorded earlier. The map and resource hashes
match and the aggregate table is identical, but the tool identity is not
pinned; treat the class breakdown as indicative, not as a controlled A/B
measurement.

The class breakdown was produced by grouping the same dump by stored type
count and by the first `highway|...` type. It counts decoded features, not OSM
ways before filtering or truncation. An eight-type result may already have
discarded other types. It is a pressure indicator, not a prediction for a
different region or a different generator revision.

## Open decisions for maintainers

* Is the centerline summary sufficient for the first cycling release, or is
  asymmetric side rendering required now?
* Should the bicycle-designation pilot use a new `bicycletag` namespace or an
  existing `hwtag` value?
* Which attribute types must be protected from truncation, and which display
  types may be dropped first?
* Is the `extra_tag` name acceptable for the general type selector, or should
  it be renamed in a future drules format version?
* What map compatibility policy applies to experimental maps, and when may a
  new per-feature section be introduced?
