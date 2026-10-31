## Summary

Treats explicit `motor_vehicle=permissive` as positive motor access, alongside `yes` and `designated`, using the existing `hwtag|yescar` classification. This is an independent prerequisite, not another cycling display type.

It targets `master` directly and contains no selector, cycling classifier, renderer, shader or map-style changes. The five-part cycling stack retains its existing numbering; its types branch includes this exact commit as an independent prerequisite.

## Scope

- Adds one existing access-flag input; no new classifier entry or MWM section.
- Keeps the existing more-specific `motorcar=no` override.
- Affects pedestrian/sidewalk/cycleway classifications as well as roads. This is not a cycling-only or visual-only change: generated-map routing behavior and styles consuming `hwtag|yescar` may change.
- The cycling preview uses the result for shared-space styling. Extracting the fix does not silently remove that behavior from the complete preview.

## Testing And Review

- Concrete mapped use case: [Fairview Crescent, way 391455011](https://www.openstreetmap.org/way/391455011), checked at version 4, has `highway=pedestrian` and `motor_vehicle=permissive`. The access collector already recognizes permissive permission; the missing classifier flag can still exclude such a way from the car graph. This is a tag observation, not verification of signage or a recommendation to drive there.
- Adds a dedicated regression covering path, footway, pedestrian and cycleway features; `yes`, `designated`, `permissive`, `no`, `private`, and more-specific `motorcar=no` in both tag orders.
- The exact standalone branch `6daf0d8755` builds and passes the complete `OsmType` group with Debug assertions, one compiler worker and a 1800 MiB hard memory limit.
- A separate research probe on this exact standalone head passes 68 route checks through actual OSM-to-map/routing/access generation and the production router. The identical probe fails on the pre-change `303ef27fbc` baseline at the pedestrian/permissive shortcut case (it uses the detour); the runner is fail-fast, so this is not a claim that every baseline case was evaluated. Fixed-head checks cover both directions and the more-specific `motorcar=no` override in both tag orders.
- The research probe is not hidden inside normal PR CI and does not reproduce the full real-world street network. The intended access interpretation still requires routing review. The cycling preview's solid/dotted policy is separate: permissive access does not establish physical protection or traffic volume.
- Additional validation was prepared with Codex assistance; production code is unchanged from the reviewed standalone head.
- Kept as a draft; do not infer approval from extraction or local tests.

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Related Cycling Stack

1. [#14040: selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [#14041: cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [#14048: optional metaline phases](https://github.com/organicmaps/organicmaps/pull/14048)
4. [#14042: renderer](https://github.com/organicmaps/organicmaps/pull/14042)
5. [#14043: style preview](https://github.com/organicmaps/organicmaps/pull/14043)
