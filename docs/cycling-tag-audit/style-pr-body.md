## Preview Only: Not for Merge As-Is

Integrate parts 1-7 with the cycling style, targeting the installed side-offset/junction phone prototype. The author explicitly approved this new target; it intentionally differs from #12692's older centerline rendering. #12692's code/head are not changed.

This cumulative upstream draft targets `ab/cycling-style`. It includes the selector, types, phase, side-data, junction-data, and offset-renderer dependencies plus the independent permissive-motor-access prerequisite. It is not an isolated style-only GitHub diff and does not certify a future rebased master integration.

## Presentation

- Keep the highway's normal core and casing. Explicitly sided attached tracks and lanes use small side indicators; dedicated cycleways remain core lines. Unqualified aggregate tags retain their fallback rather than inventing a side.
- Exactly three categories: solid track, dashed lane, dotted shared lane. All indicators have the same nominal width at a given zoom: 2 logical pixels through z16, 2.5 at z17+.
- Shared-lane dots always stay on one centerline; they do not imply a separate roadside facility.
- One-way arrows follow the bike line, including reverse direction and junction tapers. Solid arrows have the tested thin color-matched outline.
- Keep the road/indicator gap fixed during smooth zoom. Bridge/tunnel decoration does not change ordinary highway-relative offset distance.
- Taper only at topology-confirmed connections supplied by the normal generator. Do not snap disconnected, restricted, grade-separated, or ambiguous features by proximity, and do not imply a marked crossing.
- Side-data transport uses an optional `cycling_infra` section, never the prototype's debug metadata or Python OSM annotations. Old maps retain the existing centerline fallback.

## Validation and Review

The pre-hardening master-based part-7 head `398c4ed223` passes 26 offset/clipping tests, 214 geometry tests, 194 indexer tests, and 82 focused generator tests. Tested style source `1a3b3df8f6` builds and passes 553 native tests with Debug assertions: 45 rendering, 209 geometry, 194 indexer, 78 focused generator, and 27 routing-common. This includes raw-bit non-finite coordinate rejection and the explicit-side junction boundary. The shared decoder and junction sources are identical across their consuming topics. See [exact-head native results](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/production-offset-native-results.json) and the [production integration design](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/production-offset-design.md). These results are not pixel-exact screenshot evidence.

Fresh normal generation from the original Vancouver OSM input matches all 82,785 complete features, side categories/directions, 2,010 directed phase chains, and 173 active junction hints against the installed prototype. Hint-coordinate differences are within the repository's 1e-7-degree projected node-cache precision; this is not a pixel tolerance. Style/rule/symbol assets match the prototype byte-for-byte. See [matched-data results](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/production-offset-data-comparison.json) and [generation provenance](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/production-offset-map-manifest.json). The sparse side section is 192,973 bytes; net map growth is about 5.1% on this road-only fixture, not a whole-region estimate.

The previous published head `badbc0753b` has the exact same Git tree as tested source `1a3b3df8f6`, archived on `validation/cycling-offsets-1a3b3df8f6`; generated atlases have their own `[styles] Regenerated` commit. Current head `ef743e8134` adds nonvisual ownership/error-policy cleanup and passes 556 native checks: 46 rendering, 209 geometry, 193 indexer, 81 focused generator, and 27 routing-common. OSM policy moved verbatim to generator, the payload codec is unchanged, geometry receives the same style padding without a second decode, and all data/style/shader assets are byte-identical. See the [current preparation and merge gates](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/nonvisual-merge-readiness.md). Historical reports retain their actual tested source pins.

Fresh normal generation on `ef743e8134` produces a byte-identical complete map to the installed production baseline. The new production-reader export is also byte-identical (82,785 features, 2,010 directed phase chains, and the same 173 active hints). See [the exact comparison](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/nonvisual-data-comparison.json). The research suite passes 77 tests. This is valid-data/source evidence, not a new pixel-exact GPU test or full-region performance certification.

Earlier #12692 comparisons apply to the superseded centerline candidate, not this revision. They remain archived in the research branch rather than being relabeled as proof of side-offset equivalence. Classifier mappings remain branch-relative; generate maps using this branch's matching classifier, not the master-based part-2 resources.

Review the remaining model/format decisions with vng, renderer geometry and arrow behavior with rendering maintainers, generator scale/performance, fallback behavior, and the eventual style-base integration. This work was prepared with Codex assistance. CI and maintainer agreement are still required; all parts remain drafts.

## Stack

Part 8 of 8, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [side-aware data](https://github.com/organicmaps/organicmaps/pull/14074)
6. [topology-backed junctions](https://github.com/organicmaps/organicmaps/pull/14075)
7. [fixed-pixel offset renderer](https://github.com/organicmaps/organicmaps/pull/14076)
8. **cycling style integration preview (this PR)**

Prepared with Codex (LLM) assistance; original commit authorship is retained.
