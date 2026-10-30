## Summary

Treats explicit `motor_vehicle=permissive` as positive motor access, alongside `yes` and `designated`, using the existing `hwtag|yescar` classification. This is an independent prerequisite, not another cycling display type.

It targets `master` directly and contains no selector, cycling classifier, renderer, shader or map-style changes. The five-part cycling stack retains its existing numbering; its types branch includes this exact commit as an independent prerequisite.

## Scope

- Adds one existing access-flag input; no new classifier entry or MWM section.
- Keeps the existing more-specific `motorcar=no` override.
- Affects pedestrian/sidewalk/cycleway classifications as well as roads. This is not a cycling-only or visual-only change: generated-map routing behavior and styles consuming `hwtag|yescar` may change.
- The cycling preview uses the result for shared-space styling. Extracting the fix does not silently remove that behavior from the complete preview.

## Testing And Review

- Adds a dedicated regression covering path, footway, pedestrian and cycleway features; `yes`, `designated`, `permissive`, `no`, `private`, and more-specific `motorcar=no` in both tag orders.
- The exact standalone branch `6daf0d8755` builds and passes the complete `OsmType` group with Debug assertions, one compiler worker and a 1800 MiB hard memory limit.
- Generated-route behavior and the intended access interpretation still require routing review. Classification tests are not end-to-end routing proof.
- Kept as a draft; do not infer approval from extraction or local tests.

## Related Cycling Stack

1. [#14040: selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [#14041: cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [#14048: optional metaline phases](https://github.com/organicmaps/organicmaps/pull/14048)
4. [#14042: renderer](https://github.com/organicmaps/organicmaps/pull/14042)
5. [#14043: style preview](https://github.com/organicmaps/organicmaps/pull/14043)
