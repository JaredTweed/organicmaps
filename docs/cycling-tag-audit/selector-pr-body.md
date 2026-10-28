## Summary

Lets a drawing rule test whether a feature also carries a given classifier type, using the existing runtime selector syntax `extra_tag=<type>=<path>` and `extra_tag!=<type>=<path>`.

This is the first, self-contained step extracted from the cycling infrastructure work. It adds no new map types and does not change the MWM format, so it can be reviewed and merged on its own.

## Details

- `ParseSelector` now receives the `Classificator`, so selectors can resolve type paths.
- A feature type matches when it equals the selector type after truncation to that type's depth, so a parent type matches its nested children.
- Invalid operators, empty values, and malformed paths are rejected instead of asserting.

## Testing

- Full `indexer_tests` suite passes on a clean debug build of this branch.
- New tests cover equality, inequality, nested types, multiple types, and invalid selectors.

Related: #12692 (read-only reference; this PR does not modify it).
