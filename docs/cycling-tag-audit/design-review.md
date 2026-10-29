# Cycling stack design review

## Protected original

Do not push `JaredTweed:master`, the head of upstream PR #12692. Its recorded
head before this work is `955cd49403ed025c24beec09f5551e8d274a38ff`.
Changes belong only on the split preparation branches and research branch.

## Decisions for this revision

- Keep selector, generator, stored phase data and renderer as distinct review
  units. The format PR must read its output without needing the renderer PR.
- Keep the five existing drafts rather than renumbering before maintainer review.
  Official parts 2-4 are cumulative against master, not isolated GitHub diffs.
  Review commit ranges; rebase each onto master after its predecessors land.
- Keep the style PR explicitly a non-merge preview. Identical style assets do
  not prove identical output: classifier mapping, feature retention and geometry
  all participate in rendering.
- Preserve centerline categories, colors, widths, casings, arrows and phase
  behavior. No side-aware rendering or type-retention reprioritization here.
- Keep access changes visible in the generator review. The independent
  `motor_vehicle=permissive` change is a candidate for extraction, not something
  to drop silently from the final preview. Routing reviewers must accept its
  boundary and semantics before merge.

## Concrete defects addressed

- Accepting v2 without reading its interleaved floats desynchronizes the
  metalines stream. Explicit v1/v2/v3 decoding and multi-chain fixtures guard
  version widths, feature IDs, reversal and truncated-offset handling.
- Fixed unnamed-chain integers can collide with named-road hashes. Use an
  ordered `(kind, name, ref)` tuple. No platform-dependent hash or reserved
  numeric value participates in equality. Collector temporary files change
  format and must be regenerated together.

## Required evidence before merge

- Match generated features by OSM identity and segment geometry, not just
  aggregate type counts. Measure whether retaining cycling displaces access,
  direction or surface attributes. Equal combination counts can conceal swaps.
- Record exact app commit, generator commit, map hash and app/map classifier
  mappings for every visual fixture. A mapping mismatch already caused missing
  cycling treatments in an earlier preview.
- Compare fixed coordinates and zooms for track, lane, shared lane and mixed
  sides; include light/dark, clipped tiles, reversed chains, intersections and
  each supported graphics backend. Record diffs rather than inferring equality
  from style-source hashes.
- Exercise generated bicycle routes for forward/reverse access, contraflow,
  positive-side versus whole-road-negative tags, permissive motor access and
  pedestrian/sidewalk cases. Classification unit tests alone are insufficient.
- Version-1-only clients reject v3 metalines. Maintainers must explicitly accept
  merged-label/shield degradation or choose a tested additive section. A
  trailing extension is not automatically backward-compatible. Run historical
  readers on the chosen format before claiming forward compatibility.

These are merge gates, not claims that the stack is perfect or approved.

## Checks for the concrete fixes

- Built `generator_tests` and `drape_frontend_tests` with Debug assertions,
  one compiler job, reduced local unity batching, and a hard 1800 MiB cgroup
  memory cap with additional swap disabled. Some library debug symbols were
  disabled locally to reduce compiler memory; no tracked build flags changed.
- All 10 `Metalines` generator tests pass, including grouping namespaces and
  the actual collector serialization/merge round trip.
- All 3 `MetalineData` tests pass, including multi-chain v1/v2/v3 fixtures,
  reverse flags, unknown versions and truncated offset payloads.
- The complete `OsmType` group passes. This is classification evidence, not
  generated-route correctness evidence.
- Rebuilt the renderer branch `3d77a89925` against the updated format branch;
  all 16 clipping tests, both dash-phase tests and all 3 reader tests pass.
- Research/launcher tests cover a misconfigured `master` publication ref and
  reject it before any fetch, push or PR mutation.
- Style-preview copies of the new parser, reader and grouping source match
  the master-based versions. This is not an exact-branch style build or visual
  regression result; its older test CMake list required a source-list-only
  cherry-pick resolution.

## Resource limits

Run heavy tasks sequentially with one compiler job. On this machine, swap was
already full during the audit. Use a cgroup hard memory limit and no additional
swap use; never increase parallelism or the limit to force a build through.
If a unity translation unit exceeds the cap, reduce its batching or run narrower
targets instead of risking the desktop.
