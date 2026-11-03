# Production Side-Offset Integration

The later author-approved [OM Test presentation promotion](quiet-style-promotion.md)
changes palette and clutter rules, but not the data/geometry contracts below.
This document's earlier visual-reference and validation records remain historical.

## Target

The current author-approved target is the installed topology-junction phone
prototype, not the earlier centerline appearance of #12692. The reference is
runtime commit `f3d173f12daf698a0a9a02011197b407f1dfc79f`, published on
`demo/cycling-topology-joins` with subsequent documentation.

#12692's code and `JaredTweed:master` remain read-only. Earlier #12692 comparison
results are historical evidence for the previous target, not evidence for this
new rendering design. Maintainer agreement and CI are still required.

## Review Boundaries

The existing selector, cycling types, optional metaline offsets, and continuous
dash-phase topics retain their existing code heads. Permissive motor access is
still an independent prerequisite. Three new draft topics precede the final
style integration:

5. **Side data:** tag interpretation, generator-only transport, optional sparse
   MWM section, bounded decoder, lazy runtime access, and round-trip tests.
6. **Junction data:** normal generator collector, OSM-node topology, country
   shards, grade/access/barrier checks, and an end-to-end generator fixture.
7. **Offset renderer:** fixed-pixel lateral geometry, bounded miters, clipping
   context, taper and arrow displacement primitives. Preserve newer upstream
   symbol-placement/cancellation behavior and triangle clipping fixes.
8. **Presentation:** normal highways plus attached track/lane indicators;
   shared-lane dots remain on the centerline. This is the existing style-preview
   PR with a new integration head, not an isolated style-only diff.

Parts 2-7 are cumulative against upstream master because fork-owned branches
cannot serve as upstream base refs. Their exact topic ranges must be listed in
the descriptions. Part 8 remains based on `ab/cycling-style`; it is not a
merge-as-is master integration.

## Data Contract

`cycling_infra` is an optional MWM section, independent of POI metadata and the
eight classifier-type slots. Old readers ignore the unknown section; new
readers return no side attributes for old, absent, or unknown-version sections.
Invalid index bounds and failed reads follow the repository's fail-fast policy;
the bounded payload decoder still rejects malformed payloads. Existing centerline
classification remains available as a fallback when optional data is absent.

The version-1 section contains an eight-byte header (uint32 version/count), a
sorted sparse index (uint32 feature ID, uint64 offset, uint32 length), and binary
payloads. Lookups use positional I/O and binary search rather than a region-wide
runtime hash table. Payload version 1 stores two kind/direction flag bytes and
two bounded coordinate lists. Counts, lengths, reserved bits, finite coordinates,
and trailing data are validated. The section does not grant routing access.

The generator transports these attributes in a private optional raw-feature
trailer. It does not populate `FMD_TEST_ID`, change metadata enums, or require
Python OSM preprocessing. Side interpretation follows stored feature direction;
reversal swaps sides and forward/backward directions.

## Junction Contract

Only shared OSM node IDs authorize a join. Coordinate coincidence is not enough.
The connector must be an accessible dedicated cycling way at the same layer and
level. Blocked nodes, restricted ways, nearly collinear approaches, contradictory
duplicate roads, and ambiguous self-crossings are rejected conservatively.
Only solid/dashed side facilities taper; shared-lane dots remain centered.

The collector spools worker output, partitions by country, caps simultaneously
open shard writers, and uses a file-backed sorted blocked-node index while
processing each country. Country processing still holds that country's relevant
roads/connectors in memory; planet-scale memory/performance has not been
certified. This is not a new routing graph or a claim of a marked crossing.

## Presentation Contract

- Exactly three categories: solid track, dashed lane, dotted shared lane.
- Equal nominal indicator widths at a given zoom: 2 logical pixels through
  zoom 16, 2.5 at zoom 17 and above.
- Shared-lane markings always use one centerline treatment.
- Explicit side tags determine offsets; unqualified aggregate categories do not
  invent left/right geometry. Modifier-only lane tags retain side rendering,
  but do not opt into extra junction tapers without a base side tag.
- Side one-way arrows follow the bike indicator, including reversed direction
  and taper displacement. Solid arrows retain thin color-matched outlines.
- The side gap is screen-space, not multiplied by fractional zoom.
- Offset distance follows the ordinary highway/casing width, excluding bridge
  and tunnel decorations, so those decorations do not introduce lateral jumps.
- Junction tapers require topology evidence and have a minimum eight-meter
  length, extended to a minimum screen-space length when necessary.
- Generic rendering controls added upstream are retained, not replaced by the
  prototype's older versions of shared files.

## Verification Boundary

The current nonvisual ownership revision is documented separately in
[merge preparation](nonvisual-merge-readiness.md), with
[556 exact-head native checks](nonvisual-native-results.json) and
[the source/asset boundary audit](nonvisual-source-audit.json). Historical
results below retain their actual source pins. OSM policy now belongs to
generator; selected styles pass the same geometry padding to the renderer
instead of triggering a second metadata decode. Neither change alters the
approved presentation contract above.

The pre-hardening master-based renderer candidate `398c4ed223` builds with current upstream
merged. It passes 26 offset/clipping tests, 214 geometry tests, 194 indexer tests,
and 82 focused generator tests. Original side-data head `d71ce8c593` separately
passed 193 full indexer and 68 OsmType/FBuilder tests; original junction head
`d99d314c44` passed five tests,
including normal raw generation through the optional section to FeatureType.

The tested old-base style source `1a3b3df8f6` builds and passes 553 native tests
with Debug assertions: 45 rendering, 209 geometry, 194 indexer, 78 focused
generator and 27 routing-common. See [the exact-head report](production-offset-native-results.json).
Fresh generation from the original Vancouver OSM extract is a separate check.
The final shared decoder rejects non-finite IEEE wire values before floating
arithmetic, even under `-ffast-math`. Its header/test sources are identical in
the side-data and consuming branches. The normal-generator fixture also covers
modifier-only lane tags: side rendering is retained, but junction tapers opt in
only with an explicit `cycleway:left/right/both` key, matching the phone target.
The first real-map comparison exposed one extra Alberni Street taper before
this boundary was restored; that mismatch was not accepted as equivalent.

Compare complete
source-matched features and active side/category/direction/junction attributes
against the phone reference. Ignore only the prototype's debug transport, not
unrelated types, access flags, geometry, or metadata. Atlas bytes must match.
Data and native-test equivalence are not a claim of pixel-exact screenshots.

Final normal generation on `1a3b3df8f6` passes the
[complete matched-data comparison](production-offset-data-comparison.json):
all 82,785 features, side categories/directions, 2,010 directed phase chains,
and 173 active hints agree with the installed prototype. No unrelated geometry,
types, flags, names, or metadata differences were accepted. Only the prototype's
private transport and unused non-track/lane anchors are normalized away.
The maximum hint-coordinate difference is approximately 1e-7 degrees, within
the normal projected node cache's truncation precision, not a pixel tolerance.
The tracked style/rule/symbol asset paths are byte-identical to the prototype.

[Generation provenance](production-offset-map-manifest.json) records the
original unannotated input, generator/source/map hashes, one worker, and actual
submodule drift. The final map is 2,668,110 bytes versus 2,539,530 for the private
prototype map: 128,580 extra bytes (about 5.1%) on this road-only extract after
removing debug metadata. The sparse side section itself occupies 192,973 bytes.
This is a measured fixture cost, not a whole-region or planet-size estimate.

Published style head `badbc0753b` is byte-identical to that tested source:
both have Git tree `f1b7712f9e3f53a747e7dc6afb08b1961d72f181`.
The generated atlases were separated into `[styles] Regenerated cycling arrow
atlases` (`62b0752c3e`) without modifying any file. This one prepared draft's
commit organization was rewritten with an exact remote lease; parts 1-7,
independent access, and #12692 were not rewritten. The actual tested source is
preserved on `validation/cycling-offsets-1a3b3df8f6`; reports keep their true
native/generator source pin. All descriptions disclose Codex/LLM assistance.

Heavy jobs run sequentially with one worker, a 1800 MiB cgroup memory cap and
zero additional swap allowance. Existing submodule drift is recorded, not
silently reset or described as a clean checkout.

## Reproduction Tools

`generate_production_offset_map.py` requires the source root, matching CMake
build, original OSM input, output directory, and expected commit. It refuses a
different build-source directory or dirty tracked source, records submodule
state and hashes, and uses one generator worker. Run it inside the memory scope
above, only after the matching generator build has finished.

`build_mwm_audit.py --source production_mwm_feature_audit.cpp` builds a read-only
exporter against that host build's own compile/link recipe. The exporter reads
side attributes through `FeatureType::GetCyclingInfrastructure`, not a separate
ad-hoc MWM parser. Export the map together with its matching `.mwm.osm2ft` and
resource directory.

`production_offset_compare.py --reference PHONE_EXPORT --candidate NEW_EXPORT
--report REPORT_JSON` compares complete feature fingerprints, decoded side
patterns/directions, active track/lane anchors, and directed chains. It reports
anchor-coordinate precision differences explicitly. No pixel tolerance is used
to convert data agreement into a screenshot-equivalence claim.
