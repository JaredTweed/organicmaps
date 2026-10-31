#!/usr/bin/env bash
#
# Organic Maps cycling PR stack — single-file, fail-closed rollout.
#
# This script is the only publication entry point for the prepared cycling
# stack. It never touches PR #12692 and never force-pushes or rewrites a
# branch. It creates new DRAFT pull requests only; existing PRs are verified,
# not edited, unless UPDATE_PR_BODIES=YES or UPDATE_PR_TITLES=YES is set for
# the matching pinned draft.
#
# Usage:
#   ./rollout.sh --check              read-only preflight (default)
#   ./rollout.sh --plan               print the pinned plan, no network
#   PUBLISH_CYCLING_STACK=YES ./rollout.sh --publish
#   ./rollout.sh --verify             verify the published drafts
#   ROLLBACK_CYCLING_STACK=YES ./rollout.sh --rollback   close own drafts
#   ./rollout.sh --dump-bodies DIR    write the embedded PR bodies
#
# Exit codes: 0 ok, 1 blocked/failed, 2 usage.
#
# The stack:
#   1. selector   JaredTweed:prepare/cycling-selector  -> organicmaps:master
#   2. types      JaredTweed:prepare/cycling-tag-data  -> organicmaps:master
#   3. metalines  JaredTweed:prepare/cycling-metalines -> organicmaps:master
#   4. renderer   JaredTweed:prepare/cycling-dash      -> organicmaps:master
#   5. style      JaredTweed:prepare/cycling-style     -> organicmaps:ab/cycling-style
#
# The five-part cycling stack also has an independent motor-access prerequisite.
# All six are published as drafts; exact pins and validation are recorded in
# stack-readiness.md. Maintainer agreement is still pending.
# Parts 2-4 are cumulative; part 5 targets the maintainer
# style branch. The independent access PR targets master without the selector.

set -Eeuo pipefail
IFS=$'\n\t'

readonly SCRIPT_NAME=${0##*/}
readonly UPSTREAM=organicmaps/organicmaps
readonly FORK=JaredTweed/organicmaps
readonly FORK_OWNER=JaredTweed
readonly UPSTREAM_REMOTE=upstream
readonly FORK_REMOTE=origin
readonly FORBIDDEN_PR=12692

# Pins verified by --check. Update only after the matching tests pass.
readonly SELECTOR_BRANCH=prepare/cycling-selector
readonly ACCESS_BRANCH=prepare/motor-vehicle-permissive
readonly TAG_DATA_BRANCH=prepare/cycling-tag-data
readonly METALINES_BRANCH=prepare/cycling-metalines
readonly DASH_BRANCH=prepare/cycling-dash
readonly STYLE_BASE_BRANCH=prepare/cycling-style-base
readonly STYLE_BRANCH=prepare/cycling-style

readonly SELECTOR_BASE=303ef27fbc99d238965d7ced471c8920944110e6
readonly SELECTOR_HEAD=c24dc38dfe5e258837855cb84683c6ad0083adc7
readonly ACCESS_HEAD=6daf0d87550ccfcf8ee199b3b8173a53245990cb
readonly TAG_DATA_HEAD=750c72f0623dd4b93b97f205e1269866c8282b48
readonly METALINES_HEAD=1f4e588b3f1b02a905dcf23c6453457710ac12ed
readonly DASH_HEAD=c1f68d2aadc5383a85ffc9aa9754a0c871ecd957
readonly STYLE_BASE_HEAD=7af82a316aeeacfc304e9f5c2610d20d563b21ae
readonly STYLE_HEAD=5eb0952ef3bada1fc66b195131afb385f0a62692

readonly SELECTOR_TITLE='[indexer] Support drawing rules matching feature types (1/5)'
readonly ACCESS_TITLE='[generator] Recognize permissive motor vehicle access'
readonly TAG_DATA_TITLE='[generator] Classify cycling infrastructure (2/5)'
readonly METALINES_TITLE='[drape] Store optional metaline phase offsets (3/5)'
readonly DASH_TITLE='[drape] Keep a continuous dash phase across road features (4/5)'
readonly STYLE_TITLE='[styles] Apply cycleway infrastructure to the cycling style (5/5, preview)'

readonly STACK_URL_1=https://github.com/organicmaps/organicmaps/pull/14040
readonly STACK_URL_2=https://github.com/organicmaps/organicmaps/pull/14041
readonly STACK_URL_3=https://github.com/organicmaps/organicmaps/pull/14048
readonly STACK_URL_4=https://github.com/organicmaps/organicmaps/pull/14042
readonly STACK_URL_5=https://github.com/organicmaps/organicmaps/pull/14043

readonly GH=${GH:-gh}
readonly GIT=${GIT:-git}
readonly STEPS=(selector access tag-data metalines dash style)

die() { printf 'rollout: %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*"; }
usage() { sed -n '3,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }

urlenc() { printf '%s' "$1" | sed 's|/|%2F|g'; }

branch_head() { "$GIT" rev-parse --verify --quiet "refs/heads/$1"; }
merge_base() { "$GIT" merge-base "$1" "$2"; }

signed_off() {
  local sha=$1
  "$GIT" log -1 --format=%B "$sha" | grep -qE '^Signed-off-by: .+ <.+>$'
}

check_dco() { # base head label
  local sha commits
  commits=$("$GIT" rev-list --no-merges "$1..$2") || die "cannot list commits for $3"
  while IFS= read -r sha; do
    [[ -n "$sha" ]] || continue
    signed_off "$sha" || die "$3: commit $sha lacks a DCO Signed-off-by line"
  done <<< "$commits"
}

# Files whose upstream movement never invalidates a focused PR.
overlap_ignored() {
  case "$1" in
    .github/*|docs/*|*.md|iphone/metadata/*|android/app/src/*/play/*|data/strings/*) return 0 ;;
    *) return 1 ;;
  esac
}

check_no_overlap() { # base head (base kept for call-site readability)
  local head=$2 mb upstream_changed pr_changed f
  mb=$(merge_base "$head" "$UPSTREAM_REMOTE/master") || die "no merge base for $head"
  upstream_changed=$("$GIT" diff --name-only "$mb" "$UPSTREAM_REMOTE/master" | sort -u)
  pr_changed=$("$GIT" diff --name-only "$mb" "$head" | sort -u)
  local overlap
  overlap=$(comm -12 <(printf '%s\n' "$upstream_changed") <(printf '%s\n' "$pr_changed") || true)
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    overlap_ignored "$f" && continue
    die "upstream changed a file this PR edits: $f — rebase and retest before publishing"
  done <<< "$overlap"
}

state_file() {
  printf '%s' "${ROLLOUT_STATE_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/organicmaps-cycling-rollout/state.tsv}"
}

step_branch() {
  case "$1" in
    selector) printf '%s' "$SELECTOR_BRANCH" ;;
    access) printf '%s' "$ACCESS_BRANCH" ;;
    tag-data) printf '%s' "$TAG_DATA_BRANCH" ;;
    metalines) printf '%s' "$METALINES_BRANCH" ;;
    dash) printf '%s' "$DASH_BRANCH" ;;
    style) printf '%s' "$STYLE_BRANCH" ;;
    *) die "unknown step $1" ;;
  esac
}
step_head() {
  case "$1" in
    selector) printf '%s' "$SELECTOR_HEAD" ;;
    access) printf '%s' "$ACCESS_HEAD" ;;
    tag-data) printf '%s' "$TAG_DATA_HEAD" ;;
    metalines) printf '%s' "$METALINES_HEAD" ;;
    dash) printf '%s' "$DASH_HEAD" ;;
    style) printf '%s' "$STYLE_HEAD" ;;
    *) die "unknown step $1" ;;
  esac
}
step_title() {
  case "$1" in
    selector) printf '%s' "$SELECTOR_TITLE" ;;
    access) printf '%s' "$ACCESS_TITLE" ;;
    tag-data) printf '%s' "$TAG_DATA_TITLE" ;;
    metalines) printf '%s' "$METALINES_TITLE" ;;
    dash) printf '%s' "$DASH_TITLE" ;;
    style) printf '%s' "$STYLE_TITLE" ;;
    *) die "unknown step $1" ;;
  esac
}
step_repo() {
  printf '%s' "$UPSTREAM"
}
step_base() {
  case "$1" in
    selector) printf '%s' master ;;
    access) printf '%s' master ;;
    tag-data) printf '%s' master ;;
    metalines) printf '%s' master ;;
    dash) printf '%s' master ;;
    style) printf '%s' ab/cycling-style ;;
    *) die "unknown step $1" ;;
  esac
}
# Head filter form accepted by the GitHub pulls API. Every head lives on the fork.
step_head_filter() {
  printf '%s' "$(urlenc "$FORK_OWNER")%3A$(urlenc "$(step_branch "$1")")"
}

# Shared "Stack" section, identical in every PR except the bolded current part.
stack_block() { # current part number
  local current=$1 i
  local labels=(selector 'cycling types' 'metalines offsets' 'continuous dash phase' 'cycling style preview')
  local refs=('organicmaps#14040' 'organicmaps#14041' 'organicmaps#14048' 'organicmaps#14042' 'organicmaps#14043')
  local urls=("$STACK_URL_1" "$STACK_URL_2" "$STACK_URL_3" "$STACK_URL_4" "$STACK_URL_5")
  printf '\n## Stack\n\nPart %s of 5, in review order:\n\n' "$current"
  for i in 1 2 3 4 5; do
    if [[ "$i" == "$current" ]]; then
      printf '%s. **%s — %s (this PR)**\n' "$i" "${refs[$((i - 1))]}" "${labels[$((i - 1))]}"
    else
      printf '%s. [%s — %s](%s)\n' "$i" "${refs[$((i - 1))]}" "${labels[$((i - 1))]}" "${urls[$((i - 1))]}"
    fi
  done
}

body_selector() {
  cat <<'BODY'
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
- This PR does not add side-aware data or offset rendering. The #12692 comparison preview remains the existing appearance; left/right offset rendering is a separate proposal/prototype, pending agreement on side/direction semantics.
- Existing legacy modifiers, notably `highway|ford`, need explicit clarification before a global one-highway assertion or migration. They are not silently removed by this selector change.

See [vng's constraints](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6523827420) and [the proposed boundary](https://github.com/organicmaps/organicmaps/pull/14040#issuecomment-6524260599). The author subsequently authorized draft-only split updates preserving #12692's appearance; that is not maintainer agreement on the model. This selector's code remains unchanged.

## Testing

- Full `indexer_tests` suite passes on a clean debug build of this branch.
- New tests cover equality, inequality, nested types, multiple types, and invalid selectors.

Related: #12692 (read-only reference; this PR does not modify it).

## Review questions

Answers to @vng's questions are in the 2/5 PR and in [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Stack

Part 1 of 5, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054). It is not part of this selector diff.

1. **organicmaps#14040 — selector (this PR)**
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
BODY
}

body_access() {
  cat <<'BODY'
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
BODY
}

body_tag_data() {
  cat <<'BODY'
## Summary

Adds `cyclewaytag|track`, `cyclewaytag|lane`, and `cyclewaytag|shared_lane` as additional types while keeping the road's main `highway` type. Styles can then distinguish cycling infrastructure without replacing the road classification.

Draft: the access and direction changes in this PR affect bicycle routing and need review.

This upstream PR is cumulative: it contains part 1 (the selector) and an independent motor-access prerequisite. The prerequisite is merged as its own exact commit before the incremental cycling-classification commits; it is not hidden inside the display-type diff.

## What changes

- The generator classifies `cycleway*` tags into one additional centerline type. Where explicitly tagged sides/directions differ, the least-protected category wins: `shared_lane`, then `lane`, then `track`. Side-specific information is not retained.
- Keeps #12692's existing conflicting-tag precedence. An order-invariance fix for `cycleway=no` plus a positive side-specific value is a separate follow-up, because it can change classification and appearance.
- Bicycle direction and access flags are refined in the same classification pass.
- Owns the lane/shared-lane `ftypes` checkers used by the renderer, so the format PR no longer introduces classifier APIs. Baseline generator grouping remains #12692's implementation.
- Includes the generated classifier assets in the first commit consuming the new types, so intermediate commits do not depend on a later regeneration commit to load them.
- Formatting-only CI preparation uses clang-format 23; classification and rendering behavior are unchanged. This preparation was assisted by Codex.

## Compatibility

- New types are appended after the existing classifier IDs; no MWM section format change.
- No existing classifier entry is intentionally renumbered on this base. Old maps remain readable by this implementation. Historical-client handling of newly written type indices still needs a matched-map compatibility test; app and generator classifier mappings must match.

## Testing

- `generator_tests --filter=OsmType` passes on a clean debug build.
- Full `routing_common_tests` suite passes.
- On a road-only Vancouver extract, both builds retained 82,785 features; the MWM grew by 3,760 bytes (0.16%), with 787 lane, 963 shared-lane, and 108 track occurrences.
- The order-invariance regression belongs to the separate behavioral follow-up, not this equivalence baseline.

## Review notes

- The cycling style uses `hwtag=yescar` for shared-space treatment. The independent `prepare/motor-vehicle-permissive` prerequisite owns that access change and its dedicated tests, including pedestrian/sidewalk implications. The complete preview retains the behavior rather than silently removing it during extraction.
- `cyclewaytag` is registered in `UselessTypesChecker`, so it can be dropped when a feature exceeds the eight-type limit. That ordering decides whether a type-heavy road keeps its lane rendering and should be reviewed deliberately.
- Aggregate counts are not matched features. The separate research probe now exercises generated routing/access sections and the production router on controlled fixtures; this is not a broad country-specific routing audit.

## Review questions

Answers to @vng's questions in [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067):

- The stack keeps the road's main type and adds one centerline `cyclewaytag`; per-side rendering and per-side directions are deferred.
- Eight-type cap: a per-feature follow-up on the earlier retention-map pair finds unchanged complete type lists on all 1,858 cycling features. The whole maps are not certified equal (generated roundabout identities differ), and the earlier generator build pins were not archived. This is bounded evidence, not an all-regions or exact-current-head result; keep the current priority policy pending review.
- Routing: this PR still changes bicycle access/direction flags as well as display classification. Motor access is an independent prerequisite. Generated-map fixtures now cover bicycle access, ordinary/explicit/reversed one-way directions and contraflow; conflicting-tag and country-specific policy review remains. No general claim of routing/visual independence is made.
- Pedestrian reuse is a follow-up, not part of this stack.

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Stack

Part 2 of 5, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. **organicmaps#14041 — cycling types (this PR)**
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
BODY
}

body_metalines() {
  cat <<'BODY'
## Summary

Stores optional dash-phase offsets while retaining the legacy version-1 metalines section. This is the data-format half; the renderer use is part 4.

This upstream PR is cumulative: it also contains parts 1-2 and the independent motor-access prerequisite. The lane checkers now belong to the classifier/types PR, not this format PR.

## Changes

- Keeps `metalines` at version 1. A separate `metalines_offsets` section uses the already-supported version-3 layout, including feature IDs/directions and double offsets.
- Unnamed painted lane and shared-lane ways are added to metalines in separate chains.
- Preserves #12692's chain grouping and temporary collector layout. Collision-free tagged keys are a separate follow-up: fixing collisions can change chain membership, direction, offsets and rendered dash phase.
- Reads v1 (no offsets), experimental v2 (float offsets), and v3 (double offsets) explicitly. Consuming v2 offsets is essential to keep subsequent feature records aligned.
- Applies optional offsets only when every chain's feature list, reversal flags and offset count match the authoritative section. Damaged, stale or trailing optional data leaves the legacy model untouched; validation is all-or-nothing.
- The shared codec and serialization tests live in `indexer`, not `drape_frontend`; the generator no longer imports this file-format definition from the renderer. This ownership-only refactor preserves the codec body, binary layouts and rendering behavior.

## Compatibility

- Older maps (version 1) still load; without offsets the renderer falls back to a running chain offset.
- Version-1 readers still receive a version-1 section with the same signed-feature layout; they can ignore the additional tag rather than losing all metalines. No backwards-safe trailer is assumed.
- This is a metalines-format compatibility argument, not a claim that every historical app/map-classifier combination has been tested.

## Testing

- `generator_tests --filter=Metalines` passes.
- Regression fixtures cover versioned decoding, reversal, unknown versions, truncated/trailing optional sections and stale feature/direction/count mismatches. Tagged-key fixtures belong to the separate grouping follow-up.
- Codec tests now run in `indexer_tests`, including signed-ID limits and atomic preservation of existing phases for every truncated optional-data prefix. Exact consuming-head results are recorded in parts 4-5.
- `drape_frontend_tests --filter=ClipSplines` passes.
- Exact original/candidate generators match all 82,785 Vancouver features and 2,010 directed chains/offsets. The optional section validates completely; preserving the legacy section costs 27,209 bytes (about 1.1%) on this map.
- Completed Pixel audit covers 60 saved-camera views across themes and OpenGL/Vulkan, with repeated cold starts. Eleven cross-build pairs are exact; no pair stable in both builds differs. Maximum difference is 289/1,219,096 map pixels. Repeat variability prevents strict certification; no tolerance or universal equivalence claim is made.

## Scope

- This revision was refined with Codex assistance.
- Stores offsets only; the renderer use is 4/5.
- One centerline chain per road pattern; no side-specific data.
- Additive phase metadata preserves the authoritative legacy section. Emitted legacy records and resolved offsets are included in the matched-map audit; historical-client coverage is reported separately.
- Answers to @vng's questions: [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Stack

Part 3 of 5, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. **organicmaps#14048 — metalines offsets (this PR)**
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
BODY
}

body_dash() {
  cat <<'BODY'
## Summary

Keeps the dash phase continuous across adjacent road features instead of restarting it per feature. This is the renderer half; part 3 stores the offsets.

This upstream PR is cumulative: it also contains parts 1-3.

## Changes

- Uses the stored metaline offset and geometry direction to advance the dash phase.
- Updates line geometry, clipping, line helpers, and shaders; the Vulkan shader pack is regenerated.
- Applies the phase only to patterned cycling infrastructure, using the shared lane checkers.
- Uses the shared `indexer` metaline codec from part 3. Its ownership-only relocation does not change any phase calculation, classification, shader or style asset.

## Compatibility

- Older maps without offsets still load and fall back to a running chain offset.
- No color, width, or style change; only the phase across way boundaries.

## Testing

- Clean debug build of `drape_frontend_tests`.
- Clip-splines and reversed-metaline phase tests pass.
- Exact head `c1f68d2aad` passes 298 native tests: 65 classification/metalines, 18 clipping/phase, 188 indexer (including 7 codec tests) and 27 routing-common tests, all with Debug assertions.
- A separate research probe on this exact head passes 88 actual route checks across 44 synthetic OSM networks, through map/routing/access generation and the production router. It covers motor-access overrides, bicycle direction/access and pedestrian access. This is not a downloaded-region routing audit or a claim that the probe is in normal PR CI.
- Clang-format checks pass on all C++ files changed by this review unit. The final formatting-only revision changes no shader, classifier, phase calculation or style asset.
- Complete style-preview Pixel audit covers 60 saved-camera views on OpenGL/Vulkan with repeated cold starts. Eleven pairs are exact; no pair stable in both builds differs. Maximum difference is 289/1,219,096 map pixels. Repeat variability prevents strict pixel certification; this is not an exact-head screenshot test of this master-based branch.
- Earlier phone spot checks showed Cambie lane dashes, shared-lane dots, and solid tracks. This is not exhaustive visual-equivalence evidence; fixed-coordinate checks across zooms, themes, clipping, direction reversal and graphics backends remain required.

## Scope

- This revision was refined with Codex assistance.
- Continuous phase on the centerline; no per-side rendering or per-side arrows.
- Uses the stored offsets; no color, width, or style change.
- Answers to @vng's questions: [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Stack

Part 4 of 5, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. **organicmaps#14042 — continuous dash phase (this PR)**
5. [organicmaps#14043 — cycling style preview](https://github.com/organicmaps/organicmaps/pull/14043)
BODY
}

body_style() {
  cat <<'BODY'
## Preview only — not for merge as-is.

Applies the cycling style to the new `cyclewaytag` types, with preservation of #12692's solid, dashed, and dotted presentation as the validation objective.

This draft exists so the appearance can be reviewed against the intended data model. It is based on `ab/cycling-style` plus parts 1-4.

This upstream PR targets `ab/cycling-style` and also contains parts 1-4 plus the independent permissive-motor-access prerequisite. Review the `[styles]` commits; this is not an isolated style-only GitHub diff.

## What to review

- Same roads at the same zoom levels and themes should keep the same solid/dashed/dotted appearance as #12692.
- Direction arrows and shared-lane dots should follow the additional types rather than replacing the road type.
- The diff against this base includes parts 1-4 because the preview depends on them; review the `[styles]` commits and the screenshots.
- Earlier `indexer_tests` passed on the preview; new revisions need their own applicable checks before merge.
- Exact baseline/candidate Android native builds succeed. The complete tracked `data/` trees match. Separately generated Vancouver maps match all 82,785 features (including stored type order and metadata) and all 2,010 directed chains/offsets using isolated, explicitly verified classifiers. Aggregate type counts are not used as the proof.
- On exact candidate `5eb0952ef3`, 295 native tests pass with Debug assertions: 62 classification/metalines tests, 18 clipping/phase tests, 188 indexer tests (including 7 codec tests) and 27 routing-common tests. This is not pixel-equivalence evidence.
- A separate research integration probe on this exact head passes 88 route checks across 44 generated synthetic OSM networks using the production router. It is bounded routing evidence, not a whole-region audit or a claim that this probe runs in normal PR CI.
- The earlier Qt/OpenGL audit had a stable-pair discrepancy of 17 grayscale road-edge pixels; it remains archived, not erased by the new phone result.
- Completed Pixel OpenGL/Vulkan audit: 60 saved-camera views, both themes and repeated cold starts. Eleven cross-build pairs are exact; the reference repeats exactly in 10 views and the candidate in 11. No pair stable in both builds differs cross-build. Maximum difference is 289/1,219,096 map pixels (about 0.024%). Strict pixel equivalence remains unverified; no tolerance was introduced. One volume-panel-contaminated case was recaptured in full with identical settings and explicit provenance, preserving the raw evidence.
- Generate preview maps from this branch with its matching classifier and renderer format. On these pinned branches, the cycling entries occupy lines 1658-1660 of `types.txt` here (stored indices 1657-1659), versus lines 1660-1662 on the master-based types branch (stored indices 1659-1661). Mismatched app/map mappings already caused incorrect lane/track/shared rendering in a preview. The base branch alone does not supply the added types.

## Open questions

- When to add side-specific rendering as a follow-up.
- Whether individual roads lose `cyclewaytag` at the eight-type cap; aggregate Vancouver dumps do not resolve this.

Do not merge as-is: the base is the maintainer's `ab/cycling-style` branch, dependencies remain cumulative, and the visual checklist above is not complete.

## Scope

- This revision was refined with Codex assistance. The shared metaline codec/tests moved into `indexer`; the codec body and the writer/reader logic are unchanged after ownership-name and formatting normalization. All other runtime sources and tracked assets are unchanged from the previous split preview.
- Centerline style only; side-specific facilities are deferred.
- Conflicting-tag order and collision-free chain grouping are separate behavioral follow-ups, excluded to preserve #12692's classification and grouping logic.
- This old-base preview does not certify the eventual merged-master integration. Rebase/regenerate and repeat the comparison on that actual integration before claiming final equivalence; do not silently revert unrelated upstream work to match an older baseline.
- A per-feature follow-up on the earlier retention-map pair finds unchanged complete type lists on all 1,858 cycling features. The maps are not globally certified equal (generated roundabout identities differ), and those earlier generator build pins were not archived. The current ranking stays pending review; no all-regions or exact-current-head retention claim is made.
- Answers to @vng's questions: [#12692](https://github.com/organicmaps/organicmaps/pull/12692#issuecomment-6506449067).

Preparation evidence and remaining decisions: [merge-readiness checklist](https://github.com/JaredTweed/organicmaps/blob/research/cycling-tag-types/docs/cycling-tag-audit/merge-readiness.md).

## Stack

Part 5 of 5, in review order:

Independent motor-access prerequisite: [#14054](https://github.com/organicmaps/organicmaps/pull/14054).

1. [organicmaps#14040 — selector](https://github.com/organicmaps/organicmaps/pull/14040)
2. [organicmaps#14041 — cycling types](https://github.com/organicmaps/organicmaps/pull/14041)
3. [organicmaps#14048 — metalines offsets](https://github.com/organicmaps/organicmaps/pull/14048)
4. [organicmaps#14042 — continuous dash phase](https://github.com/organicmaps/organicmaps/pull/14042)
5. **organicmaps#14043 — cycling style preview (this PR)**
BODY
}

dump_body() {
  case "$1" in
    selector) body_selector ;;
    access) body_access ;;
    tag-data) body_tag_data ;;
    metalines) body_metalines ;;
    dash) body_dash ;;
    style) body_style ;;
    *) die "unknown body $1" ;;
  esac
}

body_file_name() {
  case "$1" in
    selector) printf 'selector-pr-body.md' ;;
    access) printf 'access-pr-body.md' ;;
    tag-data) printf 'tag-data-pr-body.md' ;;
    metalines) printf 'metalines-pr-body.md' ;;
    dash) printf 'dash-pr-body.md' ;;
    style) printf 'style-pr-body.md' ;;
  esac
}

dump_bodies() {
  local dir=$1
  mkdir -p "$dir"
  local step
  for step in "${STEPS[@]}"; do
    dump_body "$step" > "$dir/$(body_file_name "$step")"
  done
  note "Wrote PR bodies to $dir"
}

# ---------------------------------------------------------------- local check

check_publish_branch() {
  [[ "$1" == prepare/* ]] || die "protected branch: refusing non-prepare ref $1"
  "$GIT" check-ref-format "refs/heads/$1" >/dev/null || die "invalid branch $1"
}

check_publish_branches() {
  local protected_ref
  for protected_ref in "$SELECTOR_BRANCH" "$ACCESS_BRANCH" "$TAG_DATA_BRANCH" "$METALINES_BRANCH" \
    "$DASH_BRANCH" "$STYLE_BRANCH" "$STYLE_BASE_BRANCH"; do
    check_publish_branch "$protected_ref"
  done
}

check_local() {
  check_publish_branches
  "$GIT" rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository"

  local url
  url=$("$GIT" remote get-url "$FORK_REMOTE") || die "missing remote $FORK_REMOTE"
  [[ "$url" == *"$FORK"* ]] || die "remote $FORK_REMOTE does not point at $FORK"
  url=$("$GIT" remote get-url "$UPSTREAM_REMOTE") || die "missing remote $UPSTREAM_REMOTE"
  [[ "$url" == *"$UPSTREAM"* ]] || die "remote $UPSTREAM_REMOTE does not point at $UPSTREAM"

  local step branch expected actual
  for step in "${STEPS[@]}" selector-base; do
    if [[ "$step" == selector-base ]]; then
      branch=$STYLE_BASE_BRANCH; expected=$STYLE_BASE_HEAD
    else
      branch=$(step_branch "$step"); expected=$(step_head "$step")
    fi
    actual=$(branch_head "$branch") || die "missing local branch $branch (fetch it from $FORK_REMOTE first)"
    [[ "$actual" == "$expected" ]] || die "$branch is at $actual, expected $expected"
  done

  check_dco "$SELECTOR_BASE" "$SELECTOR_HEAD" selector
  check_dco "$SELECTOR_BASE" "$ACCESS_HEAD" access
  check_dco "$SELECTOR_HEAD" "$TAG_DATA_HEAD" tag-data
  check_dco "$TAG_DATA_HEAD" "$METALINES_HEAD" metalines
  check_dco "$METALINES_HEAD" "$DASH_HEAD" dash
  check_dco "$STYLE_BASE_HEAD" "$STYLE_HEAD" style

  [[ "$(merge_base "$SELECTOR_BRANCH" "$UPSTREAM_REMOTE/master")" == "$SELECTOR_BASE" ]] \
    || die "selector branch is not based on the reviewed upstream commit $SELECTOR_BASE"
  "$GIT" merge-base --is-ancestor "$SELECTOR_BASE" "$UPSTREAM_REMOTE/master" \
    || die "selector base $SELECTOR_BASE is no longer in upstream master (force-push?)"
  [[ "$(merge_base "$TAG_DATA_BRANCH" "$SELECTOR_BRANCH")" == "$SELECTOR_HEAD" ]] \
    || die "tag-data branch is not stacked on the selector head"
  [[ "$(merge_base "$ACCESS_BRANCH" "$UPSTREAM_REMOTE/master")" == "$SELECTOR_BASE" ]] \
    || die "independent access branch is not based on the reviewed upstream commit"
  [[ "$(merge_base "$TAG_DATA_BRANCH" "$ACCESS_BRANCH")" == "$ACCESS_HEAD" ]] \
    || die "tag-data branch does not contain the independently reviewed access fix"
  [[ "$(merge_base "$METALINES_BRANCH" "$TAG_DATA_BRANCH")" == "$TAG_DATA_HEAD" ]] \
    || die "metalines branch is not stacked on the tag-data head"
  [[ "$(merge_base "$DASH_BRANCH" "$METALINES_BRANCH")" == "$METALINES_HEAD" ]] \
    || die "dash branch is not stacked on the metalines head"
  [[ "$(merge_base "$STYLE_BRANCH" "$STYLE_BASE_BRANCH")" == "$STYLE_BASE_HEAD" ]] \
    || die "style branch is not based on the style-base head"

  local pair
  for pair in "$SELECTOR_BASE:$SELECTOR_HEAD" "$SELECTOR_BASE:$ACCESS_HEAD" "$SELECTOR_HEAD:$TAG_DATA_HEAD" \
              "$TAG_DATA_HEAD:$METALINES_HEAD" "$METALINES_HEAD:$DASH_HEAD" \
              "$STYLE_BASE_HEAD:$STYLE_HEAD"; do
    "$GIT" diff --check "${pair%%:*}" "${pair##*:}" >/dev/null || die "whitespace error in ${pair}"
  done

  # The style preview may include unrelated upstream churn, but the three
  # stackable branches must never overlap current master in source files.
  check_no_overlap "$SELECTOR_BASE" "$SELECTOR_HEAD"
  check_no_overlap "$SELECTOR_BASE" "$ACCESS_HEAD"
  check_no_overlap "$SELECTOR_HEAD" "$TAG_DATA_HEAD"
  check_no_overlap "$TAG_DATA_HEAD" "$METALINES_HEAD"
  check_no_overlap "$METALINES_HEAD" "$DASH_HEAD"
}

# --------------------------------------------------------------- remote check

remote_branch_sha() { # repo branch
  local out
  # GraphQL represents a missing ref as null, while transport/auth errors fail.
  # REST's nonzero exit must not be mistaken for a missing branch.
  out=$("$GH" api graphql \
    -f 'query=query($owner:String!,$name:String!,$ref:String!){repository(owner:$owner,name:$name){ref(qualifiedName:$ref){target{oid}}}}' \
    -f "owner=${1%/*}" -f "name=${1#*/}" -f "ref=refs/heads/$2" \
    --jq '.data.repository.ref.target.oid // empty') || die "cannot query $1:$2"
  [[ -z "$out" || "$out" =~ ^[0-9a-f]{40}$ ]] || die "invalid branch response for $1:$2"
  printf '%s' "$out"
}

pr_number() { # step
  local step=$1 out
  out=$("$GH" api "repos/$(step_repo "$step")/pulls?state=all&head=$(step_head_filter "$step")&base=$(urlenc "$(step_base "$step")")&per_page=100" \
    --jq 'if length == 0 then "" elif length == 1 then .[0].number else error("multiple matching PRs") end') \
    || die "cannot uniquely resolve PR for $step"
  [[ -z "$out" || "$out" =~ ^[0-9]+$ ]] || die "invalid PR response for $step"
  printf '%s' "$out"
}

pr_field() { # repo number jq
  local out
  out=$("$GH" api "repos/$1/pulls/$2" --jq "$3") || die "cannot query PR #$2"
  printf '%s' "$out"
}

check_remote() {
  "$GH" auth status >/dev/null 2>&1 || die "gh is not authenticated"

  local upstream_base upstream_style
  upstream_base=$(remote_branch_sha "$UPSTREAM" master)
  [[ -n "$upstream_base" ]] || die "cannot resolve upstream master"
  upstream_style=$(remote_branch_sha "$UPSTREAM" ab/cycling-style)
  [[ "$upstream_style" == "$STYLE_BASE_HEAD" ]] \
    || die "ab/cycling-style moved to ${upstream_style:-<missing>}; re-integrate and re-pin"

  local remote
  remote=$(remote_branch_sha "$FORK" "$STYLE_BASE_BRANCH")
  if [[ -n "$remote" && "$remote" != "$STYLE_BASE_HEAD" ]]; then
    die "$STYLE_BASE_BRANCH on the fork is at $remote, expected $STYLE_BASE_HEAD"
  fi

  local step branch head n
  for step in "${STEPS[@]}"; do
    branch=$(step_branch "$step")
    head=$(step_head "$step")
    remote=$(remote_branch_sha "$FORK" "$branch")
    if [[ -n "$remote" && "$remote" != "$head" ]]; then
      die "$branch on the fork is at $remote, expected $head; refusing to overwrite"
    fi

    n=$(pr_number "$step")
    if [[ -n "$n" ]]; then
      [[ "$n" != "$FORBIDDEN_PR" ]] || die "refusing to operate on PR #$FORBIDDEN_PR"
      local state draft base_ref head_sha
      state=$(pr_field "$(step_repo "$step")" "$n" .state)
      draft=$(pr_field "$(step_repo "$step")" "$n" .draft)
      base_ref=$(pr_field "$(step_repo "$step")" "$n" .base.ref)
      head_sha=$(pr_field "$(step_repo "$step")" "$n" .head.sha)
      [[ "$state" == open ]] || die "PR #$n is $state; close or retarget it first"
      [[ "$draft" == true ]] || die "PR #$n is no longer a draft; refusing to touch it"
      [[ "$base_ref" == "$(step_base "$step")" ]] || die "PR #$n base moved to $base_ref"
      [[ "$head_sha" == "$head" ]] || die "PR #$n head moved to $head_sha"
      note "PR #$n already exists for $branch (draft)"
    fi
  done

  note "Upstream master: $upstream_base (selector base: $SELECTOR_BASE)"
}

# --------------------------------------------------------------------- modes

check() {
  check_publish_branches
  "$GIT" fetch --quiet "$UPSTREAM_REMOTE" master || die "cannot fetch upstream master"
  check_local
  check_remote
  note ""
  note "Preflight passed. Nothing was changed."
  note "Run PUBLISH_CYCLING_STACK=YES $SCRIPT_NAME --publish to create the cycling drafts and independent access draft."
}

print_plan() {
  local step
  for step in "${STEPS[@]}"; do
    printf '%-9s %s:%s\n          -> %s:%s\n          %s\n' \
      "$step" "$FORK" "$(step_branch "$step")" "$(step_repo "$step")" "$(step_base "$step")" "$(step_head "$step")"
  done
  printf 'style-base mirror: %s at %s\n' "$STYLE_BASE_BRANCH" "$STYLE_BASE_HEAD"
}

push_branch() { # branch head
  local branch=$1 head=$2 remote
  check_publish_branch "$branch"
  remote=$(remote_branch_sha "$FORK" "$branch")
  if [[ -z "$remote" ]]; then
    note "Pushing $branch"
    "$GIT" push "$FORK_REMOTE" "refs/heads/$branch:refs/heads/$branch"
  elif [[ "$remote" == "$head" ]]; then
    note "Remote $branch already at $head"
  else
    die "refusing to overwrite $branch (remote $remote, expected $head)"
  fi
}

record_pr() { # step repo number url
  local file
  file=$(state_file)
  mkdir -p "$(dirname "$file")"
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$file"
}

publish() {
  [[ "${PUBLISH_CYCLING_STACK:-}" == YES ]] \
    || die "set PUBLISH_CYCLING_STACK=YES to explicitly create the drafts"

  check

  push_branch "$STYLE_BASE_BRANCH" "$STYLE_BASE_HEAD"
  local step branch repo base title body n url
  for step in "${STEPS[@]}"; do
    branch=$(step_branch "$step")
    push_branch "$branch" "$(step_head "$step")"
  done

  local head_ref state_file_path
  state_file_path=$(state_file)
  mkdir -p "$(dirname "$state_file_path")"
  : > "$state_file_path.tmp"
  mv "$state_file_path.tmp" "$state_file_path"
  for step in "${STEPS[@]}"; do
    branch=$(step_branch "$step")
    repo=$(step_repo "$step")
    base=$(step_base "$step")
    title=$(step_title "$step")
    body=$(dump_body "$step")
    head_ref="$FORK_OWNER:$branch"
    n=$(pr_number "$step")
    if [[ -n "$n" ]]; then
      [[ "$n" != "$FORBIDDEN_PR" ]] || die "refusing to operate on PR #$FORBIDDEN_PR"
      if [[ "${UPDATE_PR_TITLES:-}" == YES ]]; then
        "$GH" pr edit "$n" --repo "$repo" --title "$title"
        note "Updated title of PR #$n"
      fi
      if [[ "${UPDATE_PR_BODIES:-}" == YES ]]; then
        printf '%s\n' "$body" | "$GH" pr edit "$n" --repo "$repo" --body-file -
        note "Updated body of PR #$n"
      fi
      url=$("$GH" pr view "$n" --repo "$repo" --json url --jq .url)
    else
      url=$(printf '%s\n' "$body" | "$GH" pr create \
        --repo "$repo" --base "$base" --head "$head_ref" \
        --draft --title "$title" --body-file -)
      n=${url##*/}
      [[ "$n" =~ ^[0-9]+$ ]] || die "could not parse PR number from $url"
      note "Created draft PR: $url"
    fi
    record_pr "$step" "$repo" "$n" "$url"
  done

  note ""
  note "All ${#STEPS[@]} drafts are in place. Run $SCRIPT_NAME --verify to re-check them."
}

verify() {
  check_remote
  local step n
  for step in "${STEPS[@]}"; do
    n=$(pr_number "$step")
    [[ -n "$n" ]] || die "no PR exists for $step"
    note "$step: PR #$n OK"
  done
  note "Verification passed."
}

rollback() {
  [[ "${ROLLBACK_CYCLING_STACK:-}" == YES ]] \
    || die "set ROLLBACK_CYCLING_STACK=YES to close the drafts this kit created"

  local file
  file=$(state_file)
  [[ -s "$file" ]] || die "no rollout state at $file"
  local step repo n url state draft
  while IFS=$'\t' read -r step repo n url; do
    [[ "$n" =~ ^[0-9]+$ ]] || continue
    [[ "$n" != "$FORBIDDEN_PR" ]] || die "refusing to operate on PR #$FORBIDDEN_PR"
    state=$(pr_field "$repo" "$n" .state)
    draft=$(pr_field "$repo" "$n" .draft)
    [[ "$state" == open && "$draft" == true ]] || die "PR #$n is not an open draft; refusing to close"
    "$GH" pr close "$n" --repo "$repo" --delete-branch=false
    note "Closed draft PR #$n ($url)"
  done < "$file"
  rm -f "$file"
  note "Rollback complete. Branches were not deleted."
}

main() {
  local mode=${1:---check}
  [[ $# -le 2 ]] || usage
  case "$mode" in
    --check) check ;;
    --plan) print_plan ;;
    --publish) publish ;;
    --verify) verify ;;
    --rollback) rollback ;;
    --dump-bodies)
      [[ $# -eq 2 ]] || usage
      dump_bodies "$2"
      ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
}

main "$@"
