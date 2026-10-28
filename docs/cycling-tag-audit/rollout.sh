#!/usr/bin/env bash
#
# Organic Maps cycling PR stack — single-file, fail-closed rollout.
#
# This script is the only publication entry point for the prepared cycling
# stack. It never touches PR #12692 and never force-pushes or rewrites a
# branch. It creates new DRAFT pull requests only; existing PRs are verified,
# not edited, unless UPDATE_PR_BODIES=YES is set for a PR it created itself.
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
#   1. selector  JaredTweed:prepare/cycling-selector -> organicmaps:master
#   2. data      prepare/cycling-tag-data  -> prepare/cycling-selector
#   3. dash      prepare/cycling-dash      -> prepare/cycling-tag-data
#   4. style     prepare/cycling-style     -> prepare/cycling-style-base
#
# Steps 2-4 are fork-only review PRs, chosen by the author because GitHub
# cannot stack PRs across forks and the author has read-only access upstream.
# Step 1 is the only upstream PR and is the proposed first reviewable piece.

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
readonly TAG_DATA_BRANCH=prepare/cycling-tag-data
readonly DASH_BRANCH=prepare/cycling-dash
readonly STYLE_BASE_BRANCH=prepare/cycling-style-base
readonly STYLE_BRANCH=prepare/cycling-style

readonly SELECTOR_BASE=303ef27fbc99d238965d7ced471c8920944110e6
readonly SELECTOR_HEAD=6f9330d5c002abd40fb7fb425ad6cbc33cf377db
readonly TAG_DATA_HEAD=8e641f3e90591e296a9d03b8d732100b6929f83b
readonly DASH_HEAD=352e040b4cc06499261dbe4d516afb872e37c86f
readonly STYLE_BASE_HEAD=7af82a316aeeacfc304e9f5c2610d20d563b21ae
readonly STYLE_HEAD=ca0586974cc376ce048faf9c4b5449d3d4756f23

readonly SELECTOR_TITLE='[indexer] Support drawing rules matching feature types (1/4)'
readonly TAG_DATA_TITLE='[generator] Classify cycling infrastructure (2/4)'
readonly DASH_TITLE='[drape] Keep a continuous dash phase across road features (3/4)'
readonly STYLE_TITLE='[styles] Apply cycleway infrastructure to the cycling style (4/4, preview)'

readonly STACK_URL_1=https://github.com/organicmaps/organicmaps/pull/14040
readonly STACK_URL_2=https://github.com/organicmaps/organicmaps/pull/14041
readonly STACK_URL_3=https://github.com/organicmaps/organicmaps/pull/14042
readonly STACK_URL_4=https://github.com/organicmaps/organicmaps/pull/14043

readonly GH=${GH:-gh}
readonly GIT=${GIT:-git}
readonly STEPS=(selector tag-data dash style)

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

check_no_overlap() { # base head
  local base=$1 head=$2 mb upstream_changed pr_changed f
  mb=$(merge_base "$base" "$head") || die "no merge base for $head"
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
    tag-data) printf '%s' "$TAG_DATA_BRANCH" ;;
    dash) printf '%s' "$DASH_BRANCH" ;;
    style) printf '%s' "$STYLE_BRANCH" ;;
    *) die "unknown step $1" ;;
  esac
}
step_head() {
  case "$1" in
    selector) printf '%s' "$SELECTOR_HEAD" ;;
    tag-data) printf '%s' "$TAG_DATA_HEAD" ;;
    dash) printf '%s' "$DASH_HEAD" ;;
    style) printf '%s' "$STYLE_HEAD" ;;
    *) die "unknown step $1" ;;
  esac
}
step_title() {
  case "$1" in
    selector) printf '%s' "$SELECTOR_TITLE" ;;
    tag-data) printf '%s' "$TAG_DATA_TITLE" ;;
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
    tag-data) printf '%s' master ;;
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
  local labels=(selector 'cycling types' 'dash phase' 'cycling style preview')
  local refs=('organicmaps#14040' 'organicmaps#14041' 'organicmaps#14042' 'organicmaps#14043')
  local urls=("$STACK_URL_1" "$STACK_URL_2" "$STACK_URL_3" "$STACK_URL_4")
  printf '\n## Stack\n\nPart %s of 4, in review order:\n\n' "$current"
  for i in 1 2 3 4; do
    if [[ "$i" == "$current" ]]; then
      printf '%s. **%s — %s (this PR)**\n' "$i" "${refs[$((i - 1))]}" "${labels[$((i - 1))]}"
    else
      printf '%s. [%s — %s](%s)\n' "$i" "${refs[$((i - 1))]}" "${labels[$((i - 1))]}" "${urls[$((i - 1))]}"
    fi
  done
}

body_selector() {
  cat <<'EOF'
## Summary

Lets a drawing rule test whether a feature also carries a given classifier type, using the existing runtime selector syntax `extra_tag=<type>=<path>` and `extra_tag!=<type>=<path>`.

The parser and the `extra_tag` syntax already exist; the runtime implementation was left disabled behind a commented-out block. This PR activates it, passes the rules' own `Classificator` in, and adds tests. No existing generated rule uses `extra_tag`, so current rendering cannot change. It adds no new map types and does not change the MWM format, so it can be reviewed and merged on its own.

## Details

- `ParseSelector` now receives the `Classificator`, so selectors can resolve type paths.
- A feature type matches when it equals the selector type after truncation to that type's depth, so a parent type matches its nested children.
- Invalid operators, empty values, and malformed paths return no selector instead of being accepted.

## Testing

- Full `indexer_tests` suite passes on a clean debug build of this branch.
- New tests cover equality, inequality, nested types, multiple types, and invalid selectors.

Related: #12692 (read-only reference; this PR does not modify it).
EOF
  stack_block 1
}

body_tag_data() {
  cat <<'EOF'
## Summary

Adds `cyclewaytag|track`, `cyclewaytag|lane`, and `cyclewaytag|shared_lane` as additional types while keeping the road's main `highway` type. Styles can then distinguish cycling infrastructure without replacing the road classification.

Draft: the access and direction changes in this PR affect bicycle routing and need review.

This upstream PR is cumulative because the clean stack bases are fork-only: it also contains part 1 (the selector). Review the `[generator]` commits, or use the isolated fork draft for the clean 2/4 diff: https://github.com/JaredTweed/organicmaps/pull/1.

## What changes

- The generator classifies `cycleway*` tags into one additional type, with `track` > `lane` > `shared_lane` precedence and side/forward/backward handling.
- `cycleway=no` combined with a positive side-specific value now resolves independently of OSM tag order; a regression test reproduces the previous bug.
- Bicycle direction and access flags are refined in the same classification pass.

## Compatibility

- New types are appended after the existing classifier IDs; no MWM section format change.
- Old maps remain readable, and old readers ignore unknown types.

## Testing

- `generator_tests --filter=OsmType` passes on a clean debug build.
- Full `routing_common_tests` suite passes.
- On a road-only Vancouver extract, both builds retained 82,785 features; the MWM grew by 3,760 bytes (0.16%), with 787 lane, 963 shared-lane, and 108 track occurrences.
- The new order-invariance regression fails before the fix and passes after it.

## Review notes

- The cycling style uses `hwtag=yescar` to render ways where motor vehicles are allowed as shared space. This PR now treats `motor_vehicle=permissive` like `yes`, so two additional `hwtag|yescar` combinations appeared on the test extract: one pedestrian way and one sidewalk. The intent is cycling-related, but the pedestrian/sidewalk side effect deserves review.
- `cyclewaytag` is registered in `UselessTypesChecker`, so it can be dropped when a feature exceeds the eight-type limit. That ordering decides whether a type-heavy road keeps its lane rendering and should be reviewed deliberately.
- Aggregate counts are not matched features; individual routing correctness still needs route-graph tests.
EOF
  stack_block 2
}

body_dash() {
  cat <<'EOF'
## Summary

Keeps the dash phase continuous across adjacent road features instead of restarting it per feature. This removes the visible phase break where a dashed road is split into several OSM ways.

Stacked on the cycling-types PR because the phase is currently applied to patterned cycling infrastructure (`cyclewaytag=lane` and `cyclewaytag=shared_lane`).

This upstream PR is cumulative: it also contains parts 1-2. Review the `[drape]` commit, or use the isolated fork draft for the clean 3/4 diff: https://github.com/JaredTweed/organicmaps/pull/2.

## Changes

- The MWM metalines section version goes from 1 to 3 and stores one double dash-phase offset per feature. The reader accepts versions 1-3; version 2 was only an intermediate development format and is never written.
- The renderer combines the stored offset with the geometry direction.
- Shader sources are updated and the Vulkan shader pack is regenerated.

## Compatibility

- Older maps (version 1, and the intermediate version 2) still load; without offsets the renderer falls back to a running chain offset.
- New maps are readable by older clients, but a version-1 reader rejects the whole version-3 section, so merged-line labels and shields fall back to per-feature placement on every new map, not only cycling ways. This is graceful visual degradation, not a crash, but it is the main cost of the format change.
- An append-only alternative (keep version 1 and add a trailing offset block that old readers ignore) would avoid that regression. It is the main design choice to settle before merging this PR.

## Testing

- Clean debug build of `generator_tests` and `drape_frontend_tests`.
- Metalines and clip-splines tests pass.
- Device visual check is still required at all zoom levels and in both themes before this leaves draft.
EOF
  stack_block 3
}

body_style() {
  cat <<'EOF'
## Preview only — not for merge as-is.

Applies the cycling style to the new `cyclewaytag` types while preserving the current solid, dashed, and dotted presentation.

This draft exists so the appearance can be reviewed against the intended data model. It is based on `ab/cycling-style` plus the selector, cycling-types, and dash-phase PRs, because the cycling style itself is not on `master` yet.

This upstream PR targets `ab/cycling-style` and also contains parts 1-3. Review the `[styles]` commits, or use the isolated fork draft for the clean 4/4 diff: https://github.com/JaredTweed/organicmaps/pull/3.

## What to review

- Same roads at the same zoom levels and themes should keep the same solid/dashed/dotted appearance as #12692.
- Direction arrows and shared-lane dots should follow the additional types rather than replacing the road type.
- The diff against this base includes the selector, cycling-types, and dash-phase work because the preview depends on them. Those commits are identical to the separate PRs above; review the `[styles]` commits and the screenshots.
- The selector and generator changes pass the full `indexer_tests` suite on this branch.
- Generate the preview map from this branch or its `ab/cycling-style` base, not from `master`. `cyclewaytag` is allocated as 1658-1660 here and 1660-1662 on current `master`; a master-generated map makes these rules match the wrong types, so lane/track/shared styling looks inconsistent.

## Open questions

- Whether the final style PR should target `ab/cycling-style` directly after the generator work lands.
- Whether side-specific facilities need separate rendering before this is merged.
- How the classifier-type limit should be handled when a road already carries many types.

Do not merge: the base branch is a maintainer branch mirror and the visual checklist above is not complete.
EOF
  stack_block 4
}

dump_body() {
  case "$1" in
    selector) body_selector ;;
    tag-data) body_tag_data ;;
    dash) body_dash ;;
    style) body_style ;;
    *) die "unknown body $1" ;;
  esac
}

body_file_name() {
  case "$1" in
    selector) printf 'selector-pr-body.md' ;;
    tag-data) printf 'tag-data-pr-body.md' ;;
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

check_local() {
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
  check_dco "$SELECTOR_HEAD" "$TAG_DATA_HEAD" tag-data
  check_dco "$TAG_DATA_HEAD" "$DASH_HEAD" dash
  check_dco "$STYLE_BASE_HEAD" "$STYLE_HEAD" style

  [[ "$(merge_base "$SELECTOR_BRANCH" "$UPSTREAM_REMOTE/master")" == "$SELECTOR_BASE" ]] \
    || die "selector branch is not based on the reviewed upstream commit $SELECTOR_BASE"
  "$GIT" merge-base --is-ancestor "$SELECTOR_BASE" "$UPSTREAM_REMOTE/master" \
    || die "selector base $SELECTOR_BASE is no longer in upstream master (force-push?)"
  [[ "$(merge_base "$TAG_DATA_BRANCH" "$SELECTOR_BRANCH")" == "$SELECTOR_HEAD" ]] \
    || die "tag-data branch is not stacked on the selector head"
  [[ "$(merge_base "$DASH_BRANCH" "$TAG_DATA_BRANCH")" == "$TAG_DATA_HEAD" ]] \
    || die "dash branch is not stacked on the tag-data head"
  [[ "$(merge_base "$STYLE_BRANCH" "$STYLE_BASE_BRANCH")" == "$STYLE_BASE_HEAD" ]] \
    || die "style branch is not based on the style-base head"

  local pair
  for pair in "$SELECTOR_BASE:$SELECTOR_HEAD" "$SELECTOR_HEAD:$TAG_DATA_HEAD" \
              "$TAG_DATA_HEAD:$DASH_HEAD" "$STYLE_BASE_HEAD:$STYLE_HEAD"; do
    "$GIT" diff --check "${pair%%:*}" "${pair##*:}" >/dev/null || die "whitespace error in ${pair}"
  done

  # The style preview may include unrelated upstream churn, but the three
  # stackable branches must never overlap current master in source files.
  check_no_overlap "$SELECTOR_BASE" "$SELECTOR_HEAD"
  check_no_overlap "$SELECTOR_HEAD" "$TAG_DATA_HEAD"
  check_no_overlap "$TAG_DATA_HEAD" "$DASH_HEAD"
}

# --------------------------------------------------------------- remote check

remote_branch_sha() { # repo branch
  local out
  out=$("$GH" api "repos/$1/branches/$(urlenc "$2")" --jq .commit.sha 2>/dev/null) || return 0
  [[ "$out" =~ ^[0-9a-f]{40}$ ]] && printf '%s' "$out"
  return 0
}

pr_number() { # step
  local step=$1 out
  out=$("$GH" api "repos/$(step_repo "$step")/pulls?state=all&head=$(step_head_filter "$step")&base=$(urlenc "$(step_base "$step")")&per_page=1" \
    --jq '.[0].number // empty' 2>/dev/null) || return 0
  [[ "$out" =~ ^[0-9]+$ ]] && printf '%s' "$out"
  return 0
}

pr_field() { # repo number jq
  local out
  out=$("$GH" api "repos/$1/pulls/$2" --jq "$3" 2>/dev/null) || return 0
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
  "$GIT" fetch --quiet "$UPSTREAM_REMOTE" master || die "cannot fetch upstream master"
  check_local
  check_remote
  note ""
  note "Preflight passed. Nothing was changed."
  note "Run PUBLISH_CYCLING_STACK=YES $SCRIPT_NAME --publish to create the four drafts."
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
  note "All four drafts are in place. Run $SCRIPT_NAME --verify to re-check them."
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
