## Summary

Add runtime drawing-rule predicates for classifier types already attached to a
feature. This allows a rule associated with a main type to test an additional
type without introducing new feature types or changing the MWM format.

The selector supports equality and inequality, including parent-type matching.
Invalid operators and unknown or malformed type paths are rejected. Rules are
resolved against the classifier used to load them.

This is a standalone infrastructure proposal for discussion; it does not add
cycling attributes or change the existing cycling style. Related: #12692.

## Testing

- Focused `indexer_tests` selector and research tests passed on the existing
  research build with identical modified source files. A clean build and tests
  on this exact branch are still required before removing draft status.
- Generated-style integration, compatibility with existing drawing rules and
  the runtime cost of selectors require additional review.

LLM tools were used while developing and testing these changes.
