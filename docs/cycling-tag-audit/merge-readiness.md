# Cycling stack: remaining merge decisions

This is a preparation checklist, not maintainer approval. The split visuals
remain unchanged. PR #12692's code and the phone offset prototype are protected.

## Author-side preparation

- Correct clang-format violations in parts 2 and 4 and propagate those exact
  formatter outputs through the dependent branches. No algorithm, type-priority,
  style, shader or geometry changes are included. See the immutable
  [format audit](merge-readiness-format-audit.json) and
  [changed-file formatting checks](merge-readiness-style-results.json).
- Run the existing native regression groups against the actual candidate heads.
- Add a reproducible, separate research routing probe using the existing
  `TestRawGenerator`, routing/access/cross-MWM builders and production
  `IndexRouter`, rather than inferring routes from classification counts.
- Check real `motor_vehicle=permissive` examples against the live OSM API:
  [Fairview Crescent](https://www.openstreetmap.org/way/391455011) and
  [a footway/sidewalk](https://www.openstreetmap.org/way/960925913).
  [Archived tags and versions](permissive-real-examples.json) are observations,
  not confirmation of current physical access signage or advice to drive there.
- Preserve the standalone access PR's existing head and green CI. New routing
  evidence is a research probe, not a claim that those tests were added to its CI.
- Replace the earlier aggregate-only retention argument with a narrow matched
  feature comparison. In the earlier map pair, all 1,858 cycling features retain
  their complete type lists. Sixteen unrelated identity groups differ and have
  the generated mini-roundabout signature; do not call the maps identical.
  Original generator build pins for that earlier pair were not archived, so this
  is not a fresh exact-head regeneration or an all-regions result.

## Exact comments / responses needed

### #14040: vng, plus a maintainer able to approve CI

The existing discussion is
[here](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6523827420).
The model response and offset prototype comparison have already been posted.

Suggested focused follow-up:

> Can the selector merge independently of the offset-rendering proposal? It
> only tests classifier membership with `=` / `!=`; it does not create a second
> primary highway type or choose centerline/offset geometry. The cycling split
> retains the existing centerline appearance while the separate prototype is
> discussed. Are those constraints sufficient for reviewing this first PR?

Do not expand or rewrite the selector while waiting for that answer. A maintainer
also needs to approve the pending fork-workflow runs on the current head.

### #14054: biodranik / routing-data review

His question is
[the concrete use case](https://github.com/organicmaps/organicmaps/pull/14054#issuecomment-6526440788).

The response should distinguish three things:

- The access collector already accepts `permissive`; a default-excluded highway
  can still be missing from the car graph unless its classifier has `yescar`.
- Fairview Crescent supplies a real mapped tag example; generated shortcut/
  detour fixtures test the routing effect and more-specific `motorcar=no`.
- Physical protection/traffic volume is a different styling decision. Supporting
  access does not by itself justify a particular solid/dotted appearance.

Decision requested:

> Is interpreting explicit `motor_vehicle=permissive` as positive car eligibility,
> with `motorcar=no` still taking precedence, the intended OM behavior for ways
> otherwise excluded by their highway class?

### #14041: vng and data/style reviewers

> Can this first iteration retain the existing one-category centerline summary
> and eight-type priority policy, with per-side data and any retention-priority
> change handled separately? Do the generated bicycle access/direction fixtures
> cover the immediate routing concerns sufficiently, and which country-specific
> or conflicting-tag cases would you require before merge?

The known order-dependent conflicting-tag behavior is preserved from #12692,
not silently fixed here. A better policy would change generated output and needs
an explicit behavioral follow-up, not a claim of visual equivalence.

### #14048: rendering/format reviewers

> Is keeping the authoritative version-1 `metalines` section and placing phase
> data in an optional, atomically validated section acceptable? The emitted
> legacy records and resolved offsets are audited, with about 1.1% extra map
> size on this extract. Is a particular historical-client smoke test required
> beyond that format-level evidence?

The codec belongs to `indexer` and has seven serialization regressions. An old
reader's format contract is not a blanket claim about every historical app.

### #14042: rendering reviewers

> Please review the isolated phase implementation after the types/format
> prerequisites: clipping offsets, reversed geometry, float precision and the
> GL/Metal/Vulkan shader paths. Is the cycling-only activation scope acceptable?

The map-style colors, widths, pattern categories and arrows are not redesigned.
The earlier fixed-camera comparison remains evidence with its recorded repeat
variability, not a new strict pixel-equality certificate for each revision.

### #14043: styles reviewers / base-branch maintainer

> Should the final style integration target `ab/cycling-style`, or wait until
> that work is on `master`? Once the target is agreed and prerequisites land,
> can we rebase, regenerate against the actual classifier and repeat the matched
> data/camera checks there, keeping the current centerline appearance?

This remains a preview, not a merge candidate as-is. The actual integration
rebase/regeneration/appearance run is work still to do, not merely a missing reply.

## Who is actually waiting?

No formal reviewer assignments were present when this checklist was prepared.
The named people above are the authors of the open questions, not a claim that
GitHub has assigned them. Relevant CODEOWNERS teams are `@organicmaps/data`,
`@organicmaps/rendering`, `@organicmaps/styles`, and the default mergers team.
The [live GitHub snapshot](merge-readiness-github.json) records exact heads,
workflow conclusions, reviews, reviewer requests, counterparty comments and
current permissions. All six PRs remain drafts and no approving reviews were
present. The access PR's CMake/style workflows pass; the five numbered heads'
applicable workflows require maintainer approval.

The five numbered heads have fork workflows awaiting maintainer approval.
Any maintainer authorized to approve those runs can unblock CI; it is not a
response only one particular person can give. Local tests do not replace CI.
The current account has read-only upstream permissions (`push`, `maintain`,
`admin` and `triage` are false), so it cannot approve the blocked workflow runs
or create upstream preparation branches to isolate the stacked public diffs.

## Merge order and work after replies

1. Resolve the selector model boundary and access use case; review and merge
   #14040 and #14054 independently once approved CI is green.
2. Rebase #14041 onto actual master, regenerate classifier assets if necessary,
   retest and request review. Its current public diff is cumulative.
3. Do the same for #14048, then #14042, so their public diffs become isolated.
4. Integrate #14043 only against the agreed final base. Regenerate the map/rules
   with matching type IDs and repeat appearance validation on that integration.

Do not mark the whole stack ready based on local tests or author preparation.

## Current evidence

| Source head | Native checks | Generated routing checks |
| --- | --- | --- |
| Renderer `c1f68d2aad` | 298 pass | 88 pass / 44 fixture maps |
| Style `5eb0952ef3` | 295 pass | 88 pass / 44 fixture maps |
| Standalone access `6daf0d8755` | Prior complete OsmType pass; reported CI green | 68 pass / 34 fixture maps |
| Pre-access `303ef27fbc` | Not a new full-suite run | Expected regression at the first pedestrian/permissive case; pedestrian control passes |

The baseline regression is fail-fast. It proves a specific missing-permission
case, not that all 68 baseline routes were evaluated. Its route uses ways
10/30/40 (the detour), whereas the fixed head uses way 20 (the shortcut).
This before/after comparison uses identical probe source, not a manually
modified generator or inferred routing behavior.

Exact records:
[renderer native](merge-readiness-renderer-native.json),
[renderer routes](merge-readiness-renderer-routes.json),
[style native](merge-readiness-style-native.json),
[style routes](merge-readiness-style-routes.json),
[standalone access](merge-readiness-access-routes.json), and
[expected baseline regression](merge-readiness-before-access-routes.json).
The route records bind source revisions, probe source/binary hashes, commands
and raw-log hashes. Raw logs remain in the corresponding `/tmp/cycling-readiness-*`
directories on this machine; synthetic files and maps are scoped test fixtures.

## Reproduce the research probe

Use an existing host build of the source head being tested. This adds a local
test target through a CMake top-level include; it does not edit the source
checkout's production CMake or become a hidden part of the published PR diff.
The probe uses synthetic geometry in a real country, not downloaded region maps.

```bash
systemd-run --user --scope -p MemoryMax=1800M -p MemorySwapMax=0 \
  cmake -S /path/to/source -B /path/to/build \
  -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=/path/to/research/docs/cycling-tag-audit/routing-readiness-probe.cmake
systemd-run --user --scope -p MemoryMax=1800M -p MemorySwapMax=0 \
  cmake --build /path/to/build --target cycling_readiness_probe -j1
systemd-run --user --scope -p MemoryMax=1800M -p MemorySwapMax=0 \
  python3 docs/cycling-tag-audit/run_routing_readiness.py \
  --source /path/to/source --binary /path/to/build/cycling_readiness_probe \
  --output /path/to/new-results
```

`map` and `kml` use smaller unity batches and omit local debug symbols to stay
under the memory limit. Debug assertions remain enabled. These local test-build
settings do not modify tracked production flags. Use the access/pedestrian
filter when testing the independent access head or its pre-change baseline;
the bicycle-direction feature assertions belong to the complete cycling stack.

To remove the local extra target afterwards, reconfigure the build with
`-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=`.
