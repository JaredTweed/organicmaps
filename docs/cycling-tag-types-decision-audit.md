# Cycling tag types: decision audit

For the latest executed checks and the remaining release work, read
[validation status](cycling-tag-types-status.md). The later validation adds a
real compiler/binary-decoder comparison and native C++ parser execution; it
does not supply mobile or regenerated-map benchmarks.

## Status and conclusion

The previous solution is **not proven completely correct**. Its implementation
order is a reasonable hypothesis, but several supporting claims were wrong or
too strong. This audit supersedes those claims, not the underlying source facts
in [the research](cycling-tag-types-research.md). The
[solution](cycling-tag-types-solution.md) has corresponding corrections.

The best next step is a **narrow, measured comparison**, not a general tag-system
rewrite or a premature format commitment:

1. Preserve existing road types and routing/access behavior.
2. If centerline-only display is accepted, evaluate at most one derived positive
   facility type per applicable road, using the experimental vocabulary as a
   candidate rather than a final safety classification.
3. Compare it against a constrained generated-combination baseline. A small
   combination vocabulary can win on runtime cost and maintenance; its defeat
   has not been measured. An LLM is not required for deterministic generation.
4. If side/direction fidelity is required, compare side-qualified types,
   existing metadata, and a compact dedicated record behind the same normalized
   reader contract. Do not prescribe a new section before this comparison.
5. Leave existing designated path/footway types intact for now. Their
   decomposition is an optional experiment with additional slot and legacy
   costs, not an automatic follow-up to land.

This branch contains research and read-only audit code, not a production
implementation. It does not establish map-size, speed, routing, visual quality,
or old-client compatibility. Those remaining experiments are explicit below.
The maintainer still owns the product scope and release decision.

## Maintainer request coverage

The October 23 comment was re-read through GitHub's read-only API. Its
[three points](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6367355787)
and [October 25 research request](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6400762580)
require more than choosing a storage enum:

| Request | Research response | Evidence still required |
| --- | --- | --- |
| Which existing/new types become tag-types? | Keep primary road class; retain existing `hwtag`/`psurface`; evaluate one derived cycling type. Defer existing designation decomposition. Compare richer representations only for actual consumers. | Candidate frequency, pre-truncation losses, consumer audit and compatibility matrix. |
| Could duplicated styles avoid a tag system? | Yes, potentially for a small bounded vocabulary. Generate mechanically and compare the same semantics, zooms and assets. Do not reject based only on worst-case combinatorics. | Isolated rule count/bytes, total assets/MWM bytes, generation and runtime measurements. |
| Renderer implications of type versus combination? | Attribute-owned additive strokes and primary-owned conditional strokes are different designs; neither automatically supplies geometry offsets. Define priorities, labels, indexing, clipping, merge behavior and directional transforms. | End-to-end generated-rule tests, controlled viewport traces and screenshots on supported backends. |
| Super-clean cyclist-focused style? | Define a separate style-only experiment and explicit clutter hierarchy, described below. | Same-place/zoom comparisons and planning/navigation usability tests, including phone daylight/night use. |

No comments, PRs, or PR branch changes are needed to conduct these experiments.

## Corrections that affect the decision

### Stored slots are not hierarchy depth

`highway|path|bicycle` is one stored type. Replacing it with `highway|path`
and `bicycletag|designated` normally produces two stored types. That adds a
slot even though both paths are shallower. Keeping a legacy combined type
during transition can add still more duplication.

The audit's simple set replacement adds one slot on 10,965 highway-feature sets
in the existing Vancouver dump. That is not a predicted generator delta:
`LeaveLongestTypes`, preprocessing, visibility filtering, normalization, and
legacy policy can change the result. It is enough to reject the earlier claim
that this decomposition has no type-budget impact. See
[matching/filtering](https://github.com/organicmaps/organicmaps/blob/936c7834fb/generator/osm2type.cpp#L349).

An old mapping replacement maps an index to one classifier path. It cannot
magically expand a legacy combined type into two independent types. A future
decomposition needs legacy rule support or a deliberate reader normalization
layer, including the fixed eight-entry `TypesHolder` constraint.

### Designation is not physical separation

The helper `IsBicycleDesignatedHighway()` tests the road-class search rank;
`GetSearchRank()` truncates to two components. Thus the experimental skip
covers `highway|cycleway`, not designated `path`/`footway` subclasses.
See [helper](https://github.com/organicmaps/organicmaps/blob/936c7834fb/generator/osm2type.cpp#L1030)
and [rank lookup](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/ftypes_matcher.cpp#L284).

This observation does not justify widening the skip indiscriminately. A path
designated for bicycles can be shared; designation is not a separation or
exclusive-access measurement. The experimental style explicitly distinguishes
designated paths with `hwtag|yescar`. A blanket skip can hide explicit facility
detail. Changing the shared helper can also change `ApplyFlag()` access output,
including `yesbicycle`, independently of drawing. A future display redundancy
predicate must examine all relevant feature types and use its own contract.

### Vancouver is not an encoding benchmark

The dump reproduces 438,099 features with highway types: 145 with seven types,
six with eight. Five saturated features contain designated path plus
bridge/tunnel types; one is residential. It contains no original OSM tags and
no pre-truncation type lists. Tool/map build and mapping provenance remain
unverified as documented in the research.

Therefore neither "effectively free" nor "at most one eligible overflow"
is an established result of a regenerated map. Excluding five stored features
under an unvalidated skip policy is only a counterfactual. Larger type sets
may already have lost information. Slot pressure, total bytes and renderer
work are different quantities and must be reported separately.

### Persistent indices do not order truncation

`FinishAddingTypesEx()` sorts internal classifier values, then stable-sorts by
usefulness before retaining eight. Internal values encode positions in a
sorted classifier tree; they are not append-only `types.txt` indices.
See [classifier encoding](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/classificator.cpp#L138)
and [truncation](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/feature_data.cpp#L464).

For example, the pinned experimental mapping stores `cyclewaytag|lane` at
index 1658 but its internal value is 16398; `hwtag|yesbicycle` has stored
index 1114 and internal value 17815. Appending a mapping ID does not imply
being discarded before older attribute types. Changing priority to guarantee
display retention could instead discard access/direction/surface information.
Test nine and larger pre-truncation sets and assert *all* surviving semantics.
Eight total types never exercises the overflow branch.

### Qualified types can preserve association

`{left, right, track, lane}` is ambiguous; `{left_track, right_lane}` is not.
Qualified direction/protection values or fully composite per-side types can
also preserve association. Their problem is vocabulary/slot growth and
consumer complexity, not an inherent inability of sets to represent relations.
A dedicated record is a strong richer-data candidate, not the only possible
correct design. A structured record must also retain road-level/unspecified
facts rather than force every generic facility onto both sides.

### Metadata is a viable baseline, not POI-only storage

`feature_sorter.cpp` stores nonempty metadata against final feature IDs without
a POI-only condition. `FeatureType::GetMetadata()` uses the existing lazy
metadata reader. See
[writer](https://github.com/organicmaps/organicmaps/blob/936c7834fb/generator/feature_sorter.cpp#L296),
[metadata types](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/feature_meta.hpp#L57)
and [reader](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/indexer/feature.cpp#L890).

An append-only metadata key with a versioned normalized value may avoid
classifier slots and new section/index machinery. String/dictionary lookup,
allocation, cold reads, platform enum integration and editor behavior may cost
more than a dedicated section; these are measurable disadvantages, not proof
of unsuitability. Benchmark ordinary roads with no value as well as dense
cycling roads. Verify old-reader handling of new keys, rather than assuming it.

## Fair alternatives and selection gates

| Candidate | When it could be better | Reject or revise when |
| --- | --- | --- |
| Existing types/style-only | Immediate clutter and contrast improvements without map regeneration. | Required facility distinctions cannot be recovered from old maps. |
| One derived classifier type | A lossy centerline summary is sufficient and losses/fallbacks are acceptable. | Any routing-critical type is displaced; asymmetric/directional detail is required. |
| Generated combined types | Small stable vocabulary, fewer runtime predicates, simpler drawing dispatch. One composite can represent several correlated fields in one slot. | Mapping/rule/assets grow unacceptably, fallback loses road semantics, or classifier depth/child limits are exceeded. |
| Side-qualified classifier types | Few fields, existing type infrastructure, measured spare slots. | Required fields exceed budget or combinations create unmanageable vocabulary. |
| Existing metadata key | Sparse normalized records and acceptable measured read latency; reuses infrastructure. | Renderer lookup/allocation or editor/compatibility costs outweigh reuse. |
| Dedicated compact section | Rich side-scoped data with bounded hot-path decoding and worthwhile size/runtime improvements. | Sparse index overhead, lifecycle and reader complexity exceed the measured benefit. |

The internal tree has four path levels and seven bits per child index (0--127).
Adding all dimensions as hierarchy components can exceed depth, but naming a
bounded tuple as one component is possible. Do not equate a toy Cartesian
upper bound with actual map size. Similarly, compiled rule deduplication can
reduce duplicated source-rule cost. Measure final output for every candidate.

For the narrow prototype, positive facility categories may be `track`, `lane`,
and `shared_lane`, but confirm their exact meanings before release. Resolve
per-side overrides before summarizing; a negative left value must not erase a
positive right value. Missing is not `no`; unknown protection is not protected.
`bicycle_road=no` must not become a positive facility. Legacy `opposite_*`,
`oneway:bicycle=-1`, `separate`, `use_sidepath`, conditional restrictions and
explicit access conflicts need dedicated normalization fixtures. Do not infer
legal access or whole-road bidirectionality from a visual aggregate.

## Renderer contract

An attribute-owned stroke (`[cyclewaytag=lane]`) adds drawing rules alongside
the road's own rules. A primary-road-owned rule with a runtime type predicate
can instead choose a conditional treatment for that road. They must agree on
whether the road base remains, casing/bridge/tunnel order, label ownership,
arrows and min-zoom. `Stylist` chooses a main overlay type before filtering
runtime rules; a new attribute with overlay priority can change label ownership.
See [Stylist](https://github.com/organicmaps/organicmaps/blob/936c7834fb/libs/drape_frontend/stylist.cpp#L213).

The experimental `extra_tag` resolves classifier paths when rules load and
tests feature types at runtime. Multiple predicates are ANDed. Missing type
with `!=` is not proof of physical absence. An unknown path must not silently
turn into an unconditional rule. At the pinned upstream loader an unparseable
selector causes that drawing rule to be omitted. Audit both generated output
and runtime behavior; parser smoke tests alone do not prove the style pipeline.

The parser validates the outer key `extra_tag`; colons inside its value are not
rejected by the outer-key check. That is different from a direct runtime key
`cycleway:left`. Synthetic naming restrictions should not be invented from
the wrong parser stage. The actual compiler/submodule revision must be pinned.

The PR's dash-phase/metaline work is not a lateral lane-offset implementation.
For sides, transform left/right and forward/backward exactly once when geometry
reverses (including `oneway=-1`), preserve it through splitting and merging,
then validate joins, intersections, clipping, tiles, bridges and arrows. Reject
metaline merges across incompatible normalized attributes. Do not create a
second routed cycleway geometry merely to draw a parallel stroke.

## Cyclist-focused style experiment

This is an independent experiment, not a reason to block safe style work on
the format decision. Start with a style-only variant of the cycling base:

* Retain orientation: street names at useful zooms, junction context, water,
  crossings, access barriers and necessary road hierarchy. De-emphasize major
  car roads without hiding crossings or their connectivity.
* Prioritize repair, drinking water, bicycle parking and other cycling services
  at appropriate zooms. Reduce unrelated commercial POIs and optional labels;
  retain search results and selected destinations when explicitly requested.
* Make infrastructure, computed route, imported track and current position
  distinguishable using more than hue. Keep contrast readable in sunlight and
  avoid overly bright night rendering. Inspect dark/night, light/day and terrain
  or cycling-relation overlays together.
* Compare planning and navigation first using one style with zoom-dependent
  density. Split styles only if navigation clutter and planning context cannot
  both be served; do not multiply modes without usability evidence.

Use identical viewports at overview, neighborhood and junction zooms for a
dense city, mixed shared paths, a rural network and asymmetric lanes. Compare
base, clean-style-only and clean-style-plus-facilities in rows, light and dark.
Include an active route, an imported track, position marker and selected POI.
Record text collisions, obscured junctions, missed service discovery, route
legibility and frame/tile preparation times. Screenshots and phone testing
have **not** been produced for this audit; no usability winner is claimed.

## Reproduction and release gate

Read-only tool and tests are in `docs/cycling-tag-audit/`:

```sh
python3 -B -m unittest discover -s docs/cycling-tag-audit -v
python3 -B docs/cycling-tag-audit/audit.py
python3 -B docs/cycling-tag-audit/audit.py --dump /tmp/opencode/vancouver-types.txt
```

The committed `results.json` records this run, pinned full commits, dump hash,
mapping differences, internal-value examples, and the hypothetical split.
Not every mapping difference is a new collision: historical aliases and
deprecations need classification. The two unrelated Suzhou/cycling meanings
at indices 1657/1658 are the confirmed cycling-specific conflicts. Persistent
indices are zero-based; CSV IDs are one-based (full-format ID field, or the
second field in short rows, not necessarily the last CSV column).

Unit tests cover the audit functions and counterexamples, not the C++ generator,
renderer or routing. The existing dump is optional and is not bundled; original
map/tool/resource hashes and provenance caveats are in the companion research.
Validation for the initial audit update: all nine audit tests passed, the optional Vancouver
dump audit completed, and `git diff --check` passed. No app build, C++ test run,
map regeneration or mobile test was performed in that initial update. Subsequent
native parser and compiler-fixture checks are recorded in the status document.

Before selecting a release encoding, generate identical OSM snapshots with the
same normalized semantics under all relevant candidates. Record compiler,
commits/submodules, commands, resource/input hashes and map versions. Require:

1. Pre-filter and pre-truncation candidate counts, all lost/retained types,
   no newly lost routing/access/direction semantics, and explicit visual losses.
2. Total and per-section MWM bytes, classifier/rule/asset bytes, rule counts,
   generation wall time and peak memory. Separate encoding from unrelated
   shader, dash-phase and style changes.
3. Matched cold/warm viewport traces on actual mobile hardware; median and tail
   tile/frame times, memory, repeated runs and normal-style regressions. A
   desktop predicate microbenchmark cannot substitute for this.
4. Generator-to-style fixtures for all normalization cases above; asymmetric
   sides, reversals, bridge/tunnel transitions and merges; visual comparisons.
5. Bicycle/access/direction/conditional regression tests, plus old/new app and
   old/new map combinations, mixed neighboring maps, missing attributes and
   future/unknown values. Reconcile mapping conflicts before sharing any map.
6. Maintainer-approved budgets and product semantics, including whether one
   side's facility can justify a centerline summary. Do not invent a universal
   percentage threshold or accept rare legal-access regressions as harmless.

**Remaining work:** controlled regenerated-map comparisons, runtime C++ tests,
phone/backend rendering and screenshots, compatibility execution, and maintainer
scope/budget decisions. Research coverage is not evidence that these gates have
passed. Production implementation before those decisions risks doing extensive
work on the wrong representation; this audit deliberately does not do that.
