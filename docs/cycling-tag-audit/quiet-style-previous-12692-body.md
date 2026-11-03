> **Status: experimental follow-up.** The backward-compatible subset has been split into #13463 on top of the latest `ab/cycling-style`. This full implementation is preserved for design work with @vng and should not be released until the long-term renderer and map-data representation are agreed.

## Summary

Distinguish cycling infrastructure by safety level in the Cycling map style:

- Dedicated/off-road (`highway=cycleway`, and designated bicycle paths/footways): **solid**
- Protected/separated road-attached infrastructure (`cyclewaytag=track`): **solid**
- Painted lanes (`cyclewaytag=lane`): **dashed**
- Shared-lane markings, bicycle roads, and cycle streets (`cyclewaytag=shared_lane`): **dotted**

Ordinary roads with only `bicycle=designated` do not receive a cycling overlay. A designated bicycle way with motor traffic forbidden is treated as solid infrastructure.

All three categories use continuous contrasting casings. Solid draws above dashed, which draws above dotted. Direction arrows use a contrasting road-arrow color so they remain visible over both the casing and the cycling stroke.

## Compatibility-sensitive changes

- Adds `cyclewaytag` classifier types and detailed parsing of `cycleway=*` side/direction variants.
- Changes generator classification used by bicycle routing.
- Upgrades the serialized metalines section to support continuous dash phases across adjacent features.
- Adds renderer and shader support for the detailed solid/dashed/dotted presentation.

These changes are deliberately excluded from #13463 so a temporary representation is not released and then carried as a legacy format.

## Testing performed on this implementation

- `generator_tests --filter=OsmType`
- Drape and indexer unit tests
- Style, symbol, and shader regeneration
- Vancouver map generation and Android testing in light and dark themes

The full head is also preserved on the fork branch `pr12692-full-experimental`.

Generated with LLM assistance.
