# Nonvisual Merge Preparation (2026-11-01)

The target remains the installed **OM Side Offsets** production integration,
not #12692's superseded centerline presentation. Do not change categories,
widths, colors, arrows, offsets, fractional-zoom gaps, or junction selection.
#12692's head and `JaredTweed:master` remain protected.

## Ownership Improvements

- Part 5 owns OSM interpretation in `generator/cycling_infrastructure.*`.
  The existing tag-policy body moved unchanged out of the runtime indexer
  header. Its regression tests now live with generator policy; codec and
  optional-section tests remain in indexer.
- Part 5 follows the repository's trusted-map/error policy: absent sections
  and unsupported versions remain compatible, but invalid section-index bounds
  and failed reads no longer silently discard cycling data. Release reads
  avoid decoding and allocating side vectors merely to throw them away;
  Debug assertions still validate writer invariants. The bounded payload
  decoder and wire format are unchanged.
- Part 7 accepts geometry padding from the selected style rather than
  reading and decoding feature metadata again in the geometry builder.
  Part 8 supplies exactly the previous 64-logical-pixel predicate. A matrix
  regression covers plain features, absent/present-empty sides, all three
  kinds, light/dark styles, and the zoom boundary.

No style assets, generated rules, shader assets, categorization policy, junction
algorithm, or geometry arithmetic changed. Invalid-data handling is deliberately
stricter; that is not a promise of equivalent recovery from corrupt files.

## Validation

Exact final head `ef743e813409c7b907ca5fe7b98aae2e7ac4157c` builds and passes
[556 native tests](nonvisual-native-results.json): 46 rendering, 209 geometry,
193 indexer, 81 focused generator, and 27 routing-common. The research suite
passes 77 tests, including 22 launcher tests and two new source-boundary guards.
Clang-format 23.1.3 accepts every C++ file changed by this revision.

The separate master-based part-7 head
`6aefec7e5a1ccafb3ba5eefb32003eb6c7135ea9` also builds and passes
[542 native tests](nonvisual-master-native-results.json): 25 rendering,
213 geometry, 193 indexer, 84 focused generator, and 27 routing-common.
These are separate exact-head runs, not an inference that every intermediate
branch was freshly rebuilt or that a future master rebase has been tested.

The [source audit](nonvisual-source-audit.json) verifies unchanged data/shader
assets and payload codec, the moved-verbatim OSM policy, and untouched junction
and offset algorithms. Fresh [normal generation](nonvisual-map-manifest.json)
from the same unannotated OSM produces a **byte-identical complete map** to the
installed production baseline: 2,668,110 bytes, SHA-256
`bf175108f165a39a21fe7c434f7f11ecbe55fcb1a03ce81bc268281d579874b7`.
The freshly built production reader also produces a byte-identical complete
export: all 82,785 features and 2,010 directed phase chains, including the same
173 active junction hints. See [the comparison](nonvisual-data-comparison.json).
No source or asset change is intended to alter valid-data rendering. This is
not a new pixel-exact GPU capture, full-country benchmark, or all-platform CI.

Build, tests and generation ran sequentially, with one build/generator worker,
a 1800 MiB memory cap and no additional swap allowance. Existing submodule drift
is recorded in the manifest rather than reset or called a clean submodule state.

## Split Decision

Keep eight cycling topics and one independent access fix:

1. Selector membership, without a road reclassification policy.
2. Centerline cycling classification and existing bicycle flags.
3. Optional directed metaline-phase storage/codec.
4. Renderer use of that phase.
5. Side-data interpretation, transport, storage and runtime access.
6. Topology-backed junction generation.
7. Generic offset, taper, clipping and arrow geometry.
8. Style selection and integration with `ab/cycling-style`.

`motor_vehicle=permissive` remains independent. No extra PR is needed for the
ownership cleanup; it belongs to parts 5 and 7, with the matching selection
change in part 8. Format and consuming renderer remain separate so maintainers
can review storage compatibility independently of appearance.

Public parts 2-7 are still cumulative against master, **not isolated stacked
GitHub diffs**. Exact topic compare links in the descriptions help review, but
do not solve that platform constraint. Maintainers must provide upstream base
branches, or merge/rebase the topics sequentially. Do not create artificial
merge-only PRs or duplicate upstream branches merely to inflate the count.

## Remaining Merge Gates

- **vng / model and storage maintainers:** agree the primary-highway plus
  additional infrastructure boundary, optional side-section schema and
  compatibility, and the distinction between rendering hints and routing.
  Future pedestrian reuse is a design concern, not implemented footway data.
- **Rendering maintainers:** review offset/arrow/clipping/taper primitives and
  the current dedicated-style selection. This revision does not change the
  author's approved appearance to speculate about an unapproved policy.
- **Generator maintainers:** review country memory and planet-scale cost.
  A single road-only Vancouver fixture is not a full-region/planet benchmark.
- **biodranik / routing maintainers:** approve the concrete permissive-access
  use case in independent #14054 and review access/direction changes. Local
  unit tests are not approval of routing policy.
- **Maintainers with workflow permission:** approve fork workflow runs; local
  tests do not replace Android, iOS, CMake and code-style CI on the actual heads.
- **Repository maintainers:** settle sequential/upstream stack bases and the
  unmerged `ab/cycling-style` foundation. Part 8 is not mergeable into master
  as-is; after the real rebase, regenerate matching assets and retest.
- **Reviewers:** no approving reviews have been obtained for these drafts.
  Keep drafts until the relevant discussion and CI gates are satisfied.

The code can be better prepared, but none of these decisions can honestly be
declared settled by the author or by local automated tests.

The [live GitHub snapshot](nonvisual-github-status.json) confirms that all nine
PRs remain drafts, with no approving reviews. The cycling workflow runs report
`action_required` on their actual heads; a passing DCO alone is not green CI.
Independent #14054 has successful CMake and code-style runs, but still requires
review. #12692's protected head remains
`955cd49403ed025c24beec09f5551e8d274a38ff`.
