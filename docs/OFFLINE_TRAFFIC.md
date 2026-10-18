# Optional offline historical traffic (experimental MVP)

This implementation improves the ETA of an already selected driving route using
optional historical **running speeds**. It makes no network requests, records no
user activity, and requires no service account. It is disabled by default.
Only synthetic test/benchmark data is included. There is no claim of real-world
ETA accuracy until a licensed dataset has been independently evaluated.

**Production data blocker.** A complete merge still needs a dataset whose license
explicitly permits offline redistribution of derived speed profiles. Availability
of a provider API, an evaluation account or a downloaded batch is not a
redistribution right. This branch deliberately does not scrape, guess or relabel
inferred speeds as measurements. The package generator, matching manifest and
validation harness are ready for such a dataset; the country/coverage rollout and
held-out accuracy evaluation remain separate work.

## Repository research and implementation scope

Inspected `CONTRIBUTING.md`, `INSTALL.md`, `PR_GUIDE.md`, `CODE_STYLE_GUIDE.md`,
`routing/edge_estimator`, `routing/geometry`, `routing/index_router`,
`routing/index_graph{,_starter,_loader}`, `routing/single_vehicle_world_graph`,
`routing/traffic_stash`, `traffic/traffic_info`, `generator/traffic_generator`,
`platform/{mwm_version,local_country_file,country_defines}`, `coding/{traffic,blake3}`,
`storage/{storage,map_files_downloader,downloader_queue_universal}`, and `timezone`.

* `RoadGeometry::GetSpeed` supplies country/road-model and conditional speeds;
  `CarEstimator::CalcSegmentWeight` estimates running time. Graph layers add
  u-turn, ferry and other penalties. `IndexRouter::RedressRoute` accumulates ETAs.
* `Segment` identifies a **map-local feature, polyline segment index, direction**,
  plus a runtime `NumMwmId`. Neither runtime map numbers nor OSM way IDs are
  persistent identifiers. BEST_GEOMETRY road splitting must match the exact map.
* Existing live traffic uses `TrafficInfo::RoadSegmentId`, a map of coarse speed
  groups, `TrafficCache` and `TrafficStash`, plus a legacy congestion multiplier.
  Its 16-bit segment index and speed groups are unsuitable for weekly profiles.
  Historical packages reuse the stash lifetime and the existing car estimator;
  they do not create another route engine or revive legacy traffic downloads.
* `.mwm` is a tagged sections container. Optional sidecars avoid modifying map
  production/distribution, imposing traffic costs on everyone, and coupling
  traffic refreshes to map releases. Existing maps continue to work unchanged.
* Current timezone metadata has a compact generation-year/transition model.
  This format resolves IANA rules during preparation, with an explicit validity
  horizon and per-segment timezone index. It never uses the phone's timezone.

Implementation sequence: package reader and synthetic fixture; provider-neutral
preparation and segment export; fixed-route driving ETA and manual loading;
validation and storage/runtime benchmarks. Time-dependent route search and
mobile downloader UI are deliberately separate follow-ups.

[Issue #10062](https://github.com/organicmaps/organicmaps/issues/10062) establishes
the need for typical offline traffic patterns; [#1160](https://github.com/organicmaps/organicmaps/issues/1160)
discusses traffic integration. These do not establish availability or redistribution
rights for a production dataset.

For upstream review, the [PR guide](PR_GUIDE.md) asks for small focused changes,
compilable commits, tests, and disclosure of AI assistance. Maintainer discussion
in [#13280](https://github.com/organicmaps/organicmaps/pull/13280) emphasizes the
user problem, justification, and simplicity; [#13083 review comments](https://github.com/organicmaps/organicmaps/pull/13083#discussion_r)
illustrate scrutiny of defaults and failure paths. This is evidence for keeping
the first UI-free core small, not a guarantee of maintainer acceptance. This work
was developed with Codex assistance and needs human review before submission.

## Try the reproducible sample

Python 3.9+ with an installed IANA tzdata database is sufficient. No pip packages,
API keys or online requests are needed. The synthetic manifest identifies its
source/license and uses deliberately fictitious map identity values.

```sh
python3 tools/traffic/generate.py tools/traffic/sample/manifest.json \
  tools/traffic/sample/observations.csv /tmp/Synthetic.mwm.traffic
python3 -m unittest discover -s tools/traffic -v
cmake --preset debug-no-unity -DSKIP_QT_GUI=ON
cmake --build --preset debug-no-unity --target historical_traffic_tests -j 1
ctest --test-dir build/debug-no-unity -R '^historical_traffic_' --output-on-failure
```

The committed C++ byte fixture is generated from those inputs; Python tests
verify byte-for-byte reproducibility. To regenerate that header, add
`--cpp-fixture libs/traffic/traffic_tests/historical_traffic_fixture.hpp` to the
sample generator command and apply clang-format. Record/pin the installed IANA tzdata
release in `source.tzdb` for real generation. Rule changes require regeneration.
The sample uses America/Chicago plus UTC, tests spring-forward, repeated fall
hours, midnight/week boundaries and a clearly synthetic July 1 adjustment.

## Preparation and provider matching

Export candidates from the **final, immutable** map, after all map generation
stages (including optional sections):

```sh
cmake --build --preset debug-no-unity --target generator_tool -j 1
build/debug-no-unity/generator_tool --data_path=/path/to/maps --output=Region \
  --export_historical_traffic_segments=/tmp/Region-segments.csv
```

The read-only export contains map build epoch, map size, the existing truncated
BLAKE3 map digest, feature ID, segment index, forward boolean, and ordered WGS84
endpoints. It uses the road eligibility and geometry convention of the legacy
traffic-key extractor. Reverse geometry runs in the reverse travel direction.
It is a candidate inventory, not a general-purpose map matcher. Filter ferry/
shuttle and other unsuitable modes during preparation; runtime ignores them.

Offline geospatial/provider adapters must match licensed observations to these
candidates, considering direction, topology, split geometry, parallel roads,
coverage and confidence. Reject ambiguous matches. A provider segment spanning
multiple OM segments must be split/allocated by covered distance and travel time;
do not copy junction delay into each split. OSM way identifiers, when supplied,
are only matching hints. Re-match after **every** map rebuild. Check local edits
and validate candidate eligibility for the country car model before release.

The manifest is JSON; see the complete sample for required fields:

* `region`: exact map basename without `.mwm`; `map_build`: map version epoch
  seconds (not YYMMDD directory version); `map_size`: final byte count;
  `map_hash`: the export's 12-character BLAKE3 digest.
* `valid_from`, `valid_until`: UTC ISO timestamps, half-open interval within
  2000–2099; the generator limits the prediction horizon to five years.
* `source`: name, license identifier/rights reference, explicit `synthetic`
  boolean and pinned `tzdb` release. Additional provenance/observation dates,
  quality, provider and license-attribution fields are preserved as JSON.
  The generator adds the effective `profile_cluster_tolerance_kmh` and
  `profiles_before_clustering` to this metadata.
* `segments`: unique `id` per matched directed OM segment, `feature_id`,
  `segment_idx`, `forward` (boolean), `timezone` (IANA name), optional `factor`.
  A matching adapter may use any provider identifiers for these IDs; they are
  not included in the runtime package. Split at timezone boundaries during map
  generation where possible; otherwise assign a documented representative zone.
* `minimum_samples`: positive sample threshold (default 5).
* Optional `cluster_tolerance_kmh`: integer 0–25 (default 1). The generator
  quantizes each hourly speed to a grid of width `2 * tolerance`, so every
  retained representative is within `tolerance` km/h of the prepared aggregate.
  More than 65,535 clusters is an error: partition the region or explicitly
  choose another tolerance. The generator never silently increases this accuracy
  budget. Use 0 for exact deduplication. Missing buckets remain missing.
  This grid clustering is deterministic and linear in the number of hourly
  values; nearby profiles across grid boundaries can remain separate.
* Optional `date_adjustments`: IANA zone -> local ISO date -> multiplicative
  speed factor. Include only supported adjustments from adequately sampled
  holiday/seasonal data. Named holiday inference is not performed. Factor range
  is 0.25–255/128. Dates apply across the whole zone in this region.

Observation CSV columns:

```csv
id,weekday,hour,speed_kmh,samples
provider-match-1,0,8,25,100
```

Weekday is Monday=0 through Sunday=6. Each row represents equal-distance speed
samples or a harmonic mean of such samples, with a positive sample count.
Adapters must normalize units and statistics before producing CSV. Inputs may
come from multiple providers after deduplication and quality normalization.
Generation combines rows by sample-weighted harmonic mean, rounds to 1 km/h,
and deterministically clusters similar 168-hour profiles within the configured
speed tolerance. It rejects invalid/unmatched
observations and duplicate matches. Input order is canonicalized. Speeds must
be finite and in [1,200] km/h. Missing/low-confidence buckets are encoded as 0;
segments with no supported buckets are omitted entirely. It does not invent
measured speeds for uncovered roads.

For missing buckets the existing road/country/conditional-speed estimator is the
fallback. Additional signals, land use, school/employment/residential density,
and junction features could feed a separate calibrated preparation-time model.
No such unvalidated model is implemented. Label inferred profiles and evaluate
them separately before introducing them; do not mix provenance invisibly.

## Format v1

All integers are little endian, unaligned; no C++ struct layout is serialized.
The parser rejects unsupported flags/version, CRC failure, incompatible map,
invalid sizes/counts/indices/speeds/calendars and trailing bytes. Maximum package
size is 128 MiB. CRC32 detects corruption, not authenticity.

| Field | Encoding |
| --- | --- |
| Magic, version, flags | `OMHT`, u16=1, u16=0 |
| Map build epoch, map byte size | u64, u64 |
| Valid UTC interval | i64 from, i64 until (exclusive) |
| Region, map hash, source metadata | three strings, each u16 byte length + UTF-8 bytes |
| Profile count, timezone count, segment count | u16, u16 (1–256), u32 |
| Dictionary | profile count × 168 u8 hourly speeds in km/h, Monday 00:00 first |
| Timezone tables | timezone count tables described below |
| Sorted segment records | segment count records described below |
| Integrity | u32 CRC32 of all preceding bytes, same polynomial as zlib |

A timezone table starts with u16 transition count, u16 date-adjustment count.
Each transition is i64 UTC second + i32 UTC offset seconds (bounded ±14 hours).
The first is exactly `valid_from`; subsequent instants strictly increase and
are less than `valid_until`. Each date adjustment is i32 local civil day since
1970-01-01 + u8 factor/128, sorted with unique dates. Factor must be at least 32.
There is no rule lookup or holiday database at runtime. At an offset transition,
the new offset applies at the exact UTC instant. Repeated wall hours share a
weekly bucket; spring-forward skips the absent hour.

A key is `(uint64(feature_id) << 32) | (segment_idx << 1) | direction`, where
forward=0, reverse=1 and segment index is below 2^31. Each record stores ULEB128
key delta + u16 profile ID + u8 timezone ID + u8 factor/128. At every 64th record,
the key is absolute. Keys strictly increase, including across block boundaries.
The parser constructs a small checkpoint vector while validating the stream.
Binary search selects a block, then at most 64 deltas are decoded. No per-edge
hash table or decompressed segment array is constructed.

Raw bytes remain compressed by dictionary reuse and key deltas in memory.
Profiles are copied into a compact dictionary for fast access (the original
bytes also retain the serialized dictionary). Maximum speed quantization error
before factors is 0.5 km/h plus at most `cluster_tolerance_kmh` from preparation;
relative error at very low speeds can be significant. The v1 dictionary stores
the already-clustered representatives, so the runtime needs no lossy clustering.
If the chosen clustering tolerance leaves more than 65,535 representatives, the
generator asks for partitioning or a reviewed format extension. Gzip/xz can
reduce transport size but are **not** accepted as sidecars: downloads
must decompress to the validated raw package before atomic installation.

Lookup converts UTC using the segment zone, computes local weekday/hour, then
linearly interpolates current and next hourly speed, including the week wrap.
If either endpoint is missing it returns no prediction. Segment and date
factors are applied, then speed is clamped to [1,200] km/h. Date factors switch
at local midnight; there is no unsupported holiday extrapolation. Outside the
calendar validity window the caller falls back normally.

## Routing, loading and independent lifecycle

`IndexRouter::RedressRoute` installs an ETA-only speed callback for driving,
freezes one departure UTC instant, and advances it using accumulated segment
travel time and existing penalties. The car router creates a historical-only
`TrafficStash`. It does not copy the legacy live cache, preserving upstream's
existing decision to disable live traffic costs during route search.
The context also covers real edges behind partial/fake endpoint segments, without
changing their geometry handling.
`CarEstimator` uses historical distance/speed when live traffic is unknown.
When used independently with a live-enabled stash, legacy live traffic, including temporary closures, takes precedence;
congestion factors are never multiplied together. Turn/u-turn/ferry/border penalties remain owned by the graph;
observations must exclude those delays to avoid counting them twice. The speed
sample is taken at the segment entrance before the graph adds that junction's
penalty; sub-junction time refinement remains future work. Ferries/shuttles
retain their normal estimator. No other mode consults the callback.

The optional setting is `routing::kOfflineHistoricalTrafficEnabled`:

```cpp
settings::Set(routing::kOfflineHistoricalTrafficEnabled, true);
```

For developer testing, with the app closed, add
`OfflineHistoricalTrafficEnabled=true` to its existing `settings.ini`, then
restart. There is intentionally no new Android/iOS UI in this MVP. Use a package
for a real matching map; the synthetic package cannot match real map identities.

Install as `<actual map path>.traffic`, e.g. `/maps/261001/Region.mwm.traffic`.
`TrafficStash` lazily loads at most once per region per route calculation,
including negative caching; its existing guard releases snapshots afterward.
It checks the map's region, build timestamp, size, and existing 72-bit BLAKE3
identity. Package replacement is atomic via temporary file + rename. The
snapshot owns its bytes, so removal/replacement does not invalidate an active
calculation. Changes take effect on the next calculation. Set the option false
to disable, replace the sidecar to update, or remove it independently of the map.
Map updates with another path have no sidecar until explicitly installed; a
sidecar at the old path or with an incompatible identity cannot affect the new
map. Old sidecars are not automatically garbage-collected in this MVP.

Cold package loading validates all records and compares the package identity
with the actual map content. Its streaming BLAKE3 digest is cached for the lifetime
of the registered map, using a weak reference to its `MwmInfo`. A replacement or
re-registration creates a new identity and is hashed again, even if its path,
size and modification time match. Catalog hashes alone are not treated as proof
of the local bytes. As with routing itself, registered map files must remain
immutable until deregistration. The cache retains at most 64 digests and never
pins map handles. The microbenchmark below excludes cold disk I/O, graph
reconstruction and whole-route search.

The existing downloader handles `MapFileType::Map` and `Diff`, download queues,
country manifests, integrity checking and atomic installation. Adding a traffic
enum alone would leave sizes, URLs, update/delete behavior and mobile observers
inconsistent. A production follow-up should extend the existing region manifest
with optional traffic metadata (compatible map hash/build, format, raw/transport
sizes, package hash, observation/update dates, source/attribution/license), reuse
its queue/integrity/install mechanism, and add independent opt-in controls to
Android/iOS. Nothing fetches packages or pretends that these controls work today.

## Why route selection is unchanged

Current bidirectional A*, cross-map leap weights, cached weights and reverse
search assume static costs. Feeding departure-dependent speeds into that path
would silently violate assumptions. Even linear speed interpolation sampled at
entry can violate FIFO for a long segment; arbitrary date factors and DST
changes add discontinuities. Keeping it in fixed-route ETA prevents this from
creating routing loops or invalid heuristics. It does not prove FIFO for future
route search, nor model within-segment changes on very long edges.

A separate PR needs forward time-dependent search with absolute arrival labels,
FIFO travel-time functions obtained by integrating speed over traversal or
monotone arrival envelopes, admissible upper-speed heuristics, boundary and
access-condition handling, and time-dependent cross-region shortcuts or no
shortcuts. Establish correctness and measure representative devices before
using these costs for selection. Re-ranking static alternative routes by their
historical ETA is a smaller possible intermediate experiment.

## Tests and benchmarks

```sh
cmake --build --preset debug-no-unity --target routing_tests -j 1
build/debug-no-unity/routing_tests --filter=HistoricalTraffic
cmake --build --preset debug-no-unity --target historical_traffic_eta_benchmark -j 1
python3 tools/traffic/benchmark.py /tmp/Benchmark.mwm.traffic
build/debug-no-unity/historical_traffic_eta_benchmark /tmp/Benchmark.mwm.traffic
# Separate optimized microbenchmark from the Debug correctness build:
c++ -std=c++23 -O3 -DNDEBUG -Ilibs tools/traffic/benchmark.cpp \
  libs/traffic/historical_traffic.cpp -o /tmp/historical_traffic_benchmark
/tmp/historical_traffic_benchmark /tmp/Benchmark.mwm.traffic
python3 tools/traffic/benchmark.py /tmp/Benchmark-mixed.mwm.traffic --mixed
/tmp/historical_traffic_benchmark /tmp/Benchmark-mixed.mwm.traffic --mixed
```

`historical_traffic_benchmark` is also a normal CMake target when testing is on.
`historical_traffic_eta_benchmark` runs the actual `CarEstimator` on 100,000
synthetic segments with accumulated arrival times; its build mode must be
reported separately. Neither benchmark exercises route search.
The native package suite covers the cross-language fixture, interpolation,
directions, local zones, weekdays, DST, holidays, weekly wrap, missing buckets,
expiry, map mismatch, every truncated prefix, single-bit corruption, 512 seeded repaired-CRC mutations and structural mutations. Python tests cover generation, dictionary reuse,
canonical serialization, gzip round-trip and invalid/missing input. The routing
test checks car ETA change, disabled/missing/invalid fallback, unchanged selection
weights/turn penalty, live traffic/closure precedence, and pedestrian/bicycle/transit isolation.
A generated-map test covers lazy loading, negative caching, active snapshots,
removal between calculations, incompatible map hashes and read-only direction export.
A full generated-OSM route calculation checks that an installed sidecar changes
the driving ETA and a missing/disabled sidecar restores the baseline ETA without
changing the ordered route. A changing hourly profile also checks that later
segments use the accumulated arrival time. Registration tests replace a map with
different bytes at the same size and timestamp, rejecting stale packages and
unverified catalog hashes. The simple native benchmark verifies a million
known random-access lookups across block boundaries.

Initial optimized measurements on this laptop (single runs, synthetic):

| Million directed segments | 2 repeated profiles | 4,096 random profiles |
| --- | ---: | ---: |
| Flat key64/value32 reference | 12.00 MB | 12.00 MB |
| Raw blocked-delta sidecar | 7.04 MB | 7.73 MB |
| Gzip transport | 0.060 MB | 3.08 MB |
| Xz transport | 0.011 MB | 2.33 MB |
| Accounted package memory | 8.65 MB | 9.34 MB |
| Validate and build checkpoints | 31.7 ms | 39.5 ms |
| Baseline million divisions | 1.53 ms | 1.91 ms |
| Million random lookups + divisions | 419 ms | 455 ms |

MB means 1,000,000 bytes. Memory is owned container capacity accounting, not
process RSS; it excludes allocator overhead and map/graph caches. The simple
fixture compresses exceptionally well because it repeats; it is not a realistic
bandwidth forecast. The random dictionary is deliberately high entropy, not a
traffic distribution. Gzip preparation took ~0.04/0.93 s; xz ~0.56/5.18 s. These
measurements favor raw delta checkpoints for direct access, with optional gzip
transport, rather than runtime whole-file decompression or mandatory xz. They
meet the initial 2–10 MB raw size target **for these datasets only**.

The lookup overhead is about 0.4 microseconds/segment in this workload, or ~4 ms
for 10,000 edges excluding cold loading. This is an extrapolation, not a measured
end-to-end navigation latency. Benchmark matched real map builds and licensed
coverage, map hashing/cold I/O, devices, route lengths and ETA error against held-
out journeys before release. Compare bias/MAE by direction, hour, coverage,
weekday, holiday and map age. A 60 -> 20 km/h synthetic road triples running time;
this tests arithmetic, not actual accuracy or congestion calibration.

## Data rights and future TomTom adapter

All included observations are synthetic CC0 test data. Source code follows the
repository license. The generator preserves source/rights metadata but cannot
determine whether a dataset is lawfully redistributable. Obtain explicit rights
for offline redistribution of derived profiles, attribution, retention, territory,
updates and combinations with OSM-derived mapping before publishing packages.
A subscription, evaluation dataset or ability to download data is not permission
to redistribute it. No proprietary data or credentials are included.

[TomTom's Batch introduction](https://docs.tomtom.com/traffic-stats/documentation/batch/introduction)
describes hourly directed-segment aggregates, linked road-network and statistics
Avro files wrapped in gzip, and speeds in meters/hour. A future separately
licensed adapter would locally read both schemas, join by `dsegId`, convert units,
respect geometry/direction/network version and quality/sample counts, map-match
to the exported OM inventory, remove/allocate junction delay consistently, and
produce the neutral CSV and provenance manifest. Do not treat `dsegId` as an OM
feature ID. Aggregation semantics must be checked against the licensed schema;
the CSV expects harmonic equal-distance statistics. Other providers use the same
boundary without changes to routing. Procurement/legal review and real data
validation remain prerequisites; this document makes no legal-rights assertion.

## Suggested follow-up PRs

1. Review package contract/preparation and add fuzzing plus representative licensed
   validation datasets, country eligibility and map-matching quality reports.
2. Review the car ETA hook and add full route reconstruction/rerouting fixtures,
   live-traffic precedence cases, partial endpoints and penalties across regions.
3. Bound multi-region package memory and
   measure cold I/O, real routes, ARM hardware and long-edge speed integration.
4. Add manifest/downloader support and package lifecycle tests, then independent
   Android/iOS opt-in, sizes, dates, updates/removal and attribution.
5. Evaluate time-dependent route selection under the correctness conditions above.
6. Calibrate optional inferred fallback and finer holiday/seasonal profiles, with
   explicit provenance and held-out accuracy measurements.

This is a working experimental core, not a production worldwide traffic service.
No mobile UI, hosting, real provider importer, general map matcher, learned OSM
fallback, automatic stale-file cleanup or time-dependent route selection is
implemented. The validation commands above are the checks for this branch; any
figures in this document must be reproduced on the target map build and hardware.
