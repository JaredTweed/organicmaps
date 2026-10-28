# Cycling tag research: validation status

## Read this first

The research package is checked and reproducible locally. **The production
design and release validation are not complete.** Nothing in this branch
certifies a final encoding or proves phone usability. The earlier confident
recommendation was corrected, not validated by assertion.

Recommended reading order:

1. [Decision audit](cycling-tag-types-decision-audit.md): conclusions, corrections,
   all three maintainer requests, alternatives and release gates.
2. [Research](cycling-tag-types-research.md): pinned architecture, compatibility,
   source links and Vancouver dump provenance.
3. [Solution](cycling-tag-types-solution.md): candidate design, with audit caveats.
4. [Validation results](cycling-tag-audit/validation-results.json): executed checks,
   tool/source hashes, compiler outputs and explicit omissions.

All changes stay on `research/cycling-tag-types`. The PR, its branches and
comments are untouched. No production map, app asset, classifier mapping or
routing implementation has been changed. Subsequent work adds an opt-in Android
application ID, a research type-selector implementation and native tests; see
[Pixel 8 Pro preparation](cycling-tag-types-phone.md). These changes are not
release certification.

## Prepared review stack

The maintainer feedback led to a four-PR stack split from #12692. It is
prepared but **not published**: [stack readiness](cycling-tag-audit/stack-readiness.md)
lists the branches, pins, evidence and open questions, and the single
[`rollout.sh`](cycling-tag-audit/rollout.sh) launcher creates all four draft PRs
after an explicit opt-in. No command in that kit touches #12692.

## Additional source evidence

[Source results](cycling-tag-audit/source-results.json) inspect a separate
48,603,847-byte road-only OSM extract dated August 17, 2026 (hash recorded).
Of 74,727 highway ways, 10,799 carry one of the inspected facility keys;
1,799 carry a recognized positive category, 1,400 have explicitly differing
left/right values, 107 have multiple positive categories and 775 mix positive
values with negative or separately mapped values. These counts do not resolve
precedence, imply legal access or predict retained feature types. They are not
an A/B map benchmark and are not proven to correspond to the older stored dump.
They reinforce the need to state what information a centerline summary loses.

## Executed checks

| Check | Result | What it establishes |
| --- | --- | --- |
| Research/tool unit tests | 26 passed | Mapping numbering, slot arithmetic, source parsing, fixture construction, style derivation, and guarded phone-runner behavior. |
| Pinned-source audit | Passed | Confirms cycling-specific index conflicts and distinguishes persistent indices from internal classifier values. |
| Existing Vancouver dump audit | Completed | Reproduces the stored count table; hypothetical designation split adds a slot on 10,965 stored highway-feature sets. Not regenerated-map coverage. |
| Native C++ parser build | Passed, GCC 16.2.1, C++23, RELEASE | Compiles the repository's unmodified `drules_selector_parser.cpp` with the research probe, rather than mocking that parser. |
| Native parser fixtures | 8 passed | Equality, inequality, nested type values, colon inside a value, and rejected malformed/direct-colon-key cases. |
| Real Kothic compilation | Four fixtures compiled | Uses pinned `c5546e4f70128a301fc2f08b391baeafe29e5ee9`; generates real binary drawing rules and decodes them with that compiler's reader. |
| Equivalent fixture cases | 88 passed | Expected single stroke width/color/priority matches across both representations, absent/track/lane/shared categories and zooms 14/15. Selection uses a restricted Python evaluator, not C++ Stylist. |
| Generated predicate syntax | 132 accepted by native parser | Real compiler-generated expressions pass C++ lexical parsing; does not prove runtime type resolution. |
| C++ selector and rules loader | Three focused tests passed | Type and hierarchy predicates, unknown-selector rejection, rules loaded against their own classifier, and a nine-input/eight-retained feature serialized to and read from a test MWM. This is not a regional A/B map. |
| Native regression suites | Indexer, generator, routing and routing-common passed | CTest against the research build; renderer tests without GPU passed separately. The GPU test could not create a host OpenGL context. |
| Pixel 8 Pro functional screenshots | Five nine-viewport traces passed | Baseline and clean Outdoors surrogate in light and dark on OpenGL ES 3, plus clean/light on Vulkan. Screenshots were inspected at one matched zoom-18 location. Debug traces are not an encoding or release-performance benchmark. |
| Imported track | One Vulkan/light view inspected | A synthetic KML track was imported into the research app and appeared distinct from nearby blue bicycle-route context. Computed routes, dark-mode track overlap and real-world usability remain untested. |
| Whitespace checks | Passed | `git diff --check`. |

### Controlled compiler fixture results

Each fixture specifies the same class-dependent width and facility-dependent
color. The combined representation encodes a facility in a subclass; the tag
representation attaches one independent type and selects conditional road
rules. This compares *conditional road styling*, not every possible additive
overlay or generalized attribute renderer.

| Road classes | Representation | Type entries | Line rules | Runtime predicates | Binary bytes |
| ---: | --- | ---: | ---: | ---: | ---: |
| 3 | Combined | 12 | 24 | 0 | 689 |
| 3 | Tag predicates | 6 | 24 | 36 | 660 |
| 8 | Combined | 32 | 64 | 0 | 1,768 |
| 8 | Tag predicates | 11 | 64 | 96 | 1,381 |

This supplies a real counterexample to treating a smaller type vocabulary as
an automatic reduction in line rules. Here tags reduce vocabulary and binary
bytes but do not reduce rule count and do introduce predicates. Combined types
remain a credible baseline. These small synthetic artifacts are **not** estimates
of total app/MWM savings or evidence of a renderer-performance winner.
Single-run compiler times are recorded only for traceability, not ranked.

## Reproduce locally

Requirements: Python 3.10+, Git with the pinned OM commits, a C++23 compiler,
and a clean Kothic checkout at the exact commit above. No Python packages,
phone, app build or generator binary are needed for the synthetic fixtures.

```sh
python3 -B docs/cycling-tag-audit/run_validation.py \
  --kothic /path/to/pinned/kothic \
  --output-dir /tmp/cycling-validation
```

Add `--dump /path/to/vancouver-types.txt` to repeat the optional stored-map
analysis. Its input hash is recorded, and original map/resource provenance is
in the research. The executable's output is JSON; redirect it to a disposable
file when comparing runs. Generated fixture inputs, binaries, compiler logs,
unit-test logs and native parser executable stay under the disposable output
directory. The runner refuses output inside the research worktree.

The runner exits unsuccessfully on failed unit tests, C++ compilation, fixture
compilation, binary decoding, expected stroke mismatches, predicate parsing,
dirty/wrong-version compiler sources or whitespace errors.

## Not complete: release validation

| Remaining item | Why the local checks do not replace it | Required next evidence |
| --- | --- | --- |
| Controlled real-map A/B generation | Existing dump has no raw candidate tags or pre-truncation history. Synthetic styles do not run the map generator. | Identical source snapshots and runnable candidate generator/storage implementations; retained/lost semantics, total/section bytes, generation time and memory. |
| Full generator-to-style candidate execution | The new native tests exercise the selector, rule loader, one saturated MWM fixture and existing regression suites; the Kothic fixture evaluator is still not C++ Stylist. | Test generated candidate maps and their rules end to end, including routing/access/direction/conditional behavior. |
| Old/new app-map compatibility | Pinned mapping comparison detects conflicts but does not run old clients or download policy. | Matching old/new app builds and generated maps in all version directions, mixed regions and fallback cases. |
| GPU/backend and phone performance | Debug OpenGL phone traces and the headless CPU renderer tests do not establish release performance; the host GPU context test could not start. | Matched optimized candidate builds, repeated cold/warm traces, and supported-backend testing. |
| Cyclist-focused usability | Initial same-place, light/dark screenshots exist for an Outdoors surrogate, not the dedicated cycling mode. | Active route, imported track, position, POIs and overlays; daylight/night planning/navigation tests and participant feedback. |
| Product and release decisions | No benchmark can decide required side fidelity or acceptable display loss for maintainers. | Agreement on centerline versus sides, priority/loss policy, scope and performance budgets. |

These are genuine remaining tasks, not completed checkboxes. The current
source/data analysis and compiler fixtures do not justify an unreviewed
production format rewrite. Keep the narrowly scoped centerline candidate,
generated-combination baseline, metadata reuse and richer side records open
until the applicable gates are executed. Do not announce the maintainer's
whole request as complete merely because the research branch is clean.
