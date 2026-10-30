# Ownership-only code-quality revision

The phone side-offset prototype is separate. This revision does not change
the split PRs' visuals or PR #12692's code.

## Changes

- Move the shared metaline codec from `drape_frontend` to `indexer`, under
  `feature::metalines`. The generator and renderer both use that data-layer
  definition; the generator no longer imports this format from the renderer.
- Remove the codec's transitive include from the renderer task's public header.
- Move serialization tests to `indexer_tests`, where the codec belongs, rather
  than requiring the renderer test target to exercise the format.
- Add signed-ID boundary fixtures for all three supported versions, preserving
  the existing zero-ID direction convention and widened negation behavior.
- Test every truncated optional-section prefix against an already populated
  model, proving failure leaves both geometry identities and prior phases intact.

The format commit is appended to part 3. Part 4 is replayed on that dependency;
the same ownership change is applied to the old-base style preview. Parts 1-2
and the independent access prerequisite do not need code changes.

## Preservation Checks

[Source comparison](code-quality-review.json) checks all three changed branches:
the codec body is identical after namespace substitution, and the writer and
reader differ only in ownership names, includes and formatting. All other
runtime sources, classification code, shaders and tracked assets are unchanged.
The binary layouts, emitted IDs/directions/offsets, grouping, phase calculations,
selector behavior and drawing rules are not redesigned in this revision.

Reproduce the immutable-pin source check with clang-format 23:

```bash
python3 docs/cycling-tag-audit/verify_code_quality.py --clang-format /path/to/clang-format
```

This is preservation of the existing split behavior, not a new claim of strict
pixel equivalence to #12692. The earlier comparison evidence and its limitations
remain recorded in `visual-validation.md`. No prototype offsets, zoom thresholds,
shared-lane placement changes or prototype arrow overrides enter these PRs.

## Review Limits

Do not turn this cleanup into classification or chain-grouping changes. The
known conflicting-tag precedence and hash-grouping fixes remain separate
behavioral follow-ups. Maintainer agreement, generated-route coverage, CI and
the eventual rebased integration's appearance checks remain merge gates.

Native builds and tests run sequentially with one compiler job, a hard
1800 MiB memory cap and no additional swap. Codex assisted this revision.

## Native Results

- Renderer `fdc131de53`: all 298 tests pass (188 indexer, 65 classification/
  metalines, 18 clipping/phase, 27 routing-common).
- Style `34a0624d67`: all 295 tests pass (188 indexer, 62 classification/
  metalines, 18 clipping/phase, 27 routing-common).
- The seven codec tests now belong to the indexer count, not the renderer count.
- Both revisions pass clang-format 23.1.3 checks on the affected C++ files.

Exact-head result records: [renderer](code-quality-renderer-native-results.json)
and [style](code-quality-style-native-results.json).
