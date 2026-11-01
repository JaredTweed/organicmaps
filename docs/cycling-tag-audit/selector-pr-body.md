## Summary

Lets a drawing rule test whether a feature also carries a given classifier type, using the existing runtime selector syntax `extra_tag=<type>=<path>` and `extra_tag!=<type>=<path>`.

The parser and the `extra_tag` syntax already exist; the runtime implementation was left disabled behind a commented-out block. This PR activates it, passes the rules' own `Classificator` in, and adds tests. No generated rule on the pinned baseline uses `extra_tag`, so no existing rendering change is intended. It adds no new map types and does not change the MWM format, so it can be reviewed on its own, subject to CI and review.

## Details

- `ParseSelector` now receives the `Classificator`, so selectors can resolve type paths.
- A feature type matches when it equals the selector type after truncation to that type's depth, so a parent type matches its nested children.
- Invalid operators, empty values, and malformed paths return no selector instead of being accepted.

## Road-model boundary under discussion

- A road keeps its primary `highway=*` type. Attached infrastructure belongs in additional types such as `cyclewaytag=*` or a future `footwaytag=*`, not a second primary road category. Shared footway/cycleway features are the proposed exception.
- `extra_tag` only tests classifier membership with `=` or `!=`; it neither creates types nor decides the primary highway. For example, a secondary road can test `extra_tag=cyclewaytag=lane` without also becoming a `highway=cycleway`.
- This PR does not add side-aware data or offset rendering. Those are separate parts 5-8; their new author-approved target is the phone side-offset prototype, pending maintainer agreement on side/direction semantics.
- Existing legacy modifiers, notably `highway|ford`, need explicit clarification before a global one-highway assertion or migration. They are not silently removed by this selector change.

See [vng's constraints](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6523827420) and [the proposed boundary](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6524260599). The author subsequently authorized integrating the tested side-offset prototype in additional focused drafts; that is not maintainer agreement on the model. This selector's code remains unchanged.

## Testing

- Full `indexer_tests` suite passes on a clean debug build of this branch.
- New tests cover equality, inequality, nested types, multiple types, and invalid selectors.

Related: #12692 (read-only reference; this PR does not modify it).

## Review questions

Answers to @vng's questions are in the 2/8 PR and in [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Stack

Part 1 of 8, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. **selector (this PR)**
2. [cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [side-aware data](https://github.com/organicmaps/organicmaps/pull/14074)
6. [topology-backed junctions](https://github.com/organicmaps/organicmaps/pull/14075)
7. [fixed-pixel offset renderer](https://github.com/organicmaps/organicmaps/pull/14076)
8. [cycling style integration preview](https://github.com/organicmaps/organicmaps/pull/14043)

Prepared with Codex (LLM) assistance; original commit authorship is retained.
