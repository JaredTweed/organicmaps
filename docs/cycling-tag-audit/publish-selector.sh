#!/usr/bin/env bash
# Deliberately publishes only the reviewed selector draft, never PR #12692.
set -euo pipefail

mode=${1:---check}
if [[ $# -gt 1 || ( "$mode" != --check && "$mode" != --publish-selector ) ]]; then
  printf 'Usage: %s [--check|--publish-selector]\n' "$0" >&2
  exit 2
fi

repo=organicmaps/organicmaps
owner=JaredTweed
branch=prepare/cycling-selector
expected_base=b55c734f33b278c452a070c1465904c4144dc1ad
expected_head=6f9330d5c002abd40fb7fb425ad6cbc33cf377db
body_file=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/selector-pr-body.md

command -v gh >/dev/null
command -v git >/dev/null
gh auth status >/dev/null
[[ -s "$body_file" ]] || { printf 'Missing PR body\n' >&2; exit 1; }
base=$(gh api "repos/$repo/commits/master" --jq .sha)
head=$(gh api "repos/$owner/organicmaps/branches/prepare%2Fcycling-selector" --jq .commit.sha)
[[ "$base" == "$expected_base" ]] || {
  printf 'Upstream master advanced; rebase, retest, and review before publishing.\n' >&2; exit 1;
}
[[ "$head" == "$expected_head" ]] || {
  printf 'Unexpected fork branch tip; inspect and update the reviewed manifest.\n' >&2; exit 1;
}
existing=$(gh api "repos/$repo/pulls?state=all&head=$owner%3Aprepare%2Fcycling-selector&per_page=1" --jq 'length')
[[ "$existing" == 0 ]] || {
  printf 'A PR already exists for this branch; refusing to create or modify one.\n' >&2; exit 1;
}
printf 'Prepared selector branch %s at %s against %s.\n' "$branch" "$head" "$base"
printf 'Only a draft selector PR is prepared. Later stack items remain blocked.\n'
if [[ "$mode" == --check ]]; then
  printf 'Read-only check complete; no PRs or branches changed.\n'
  exit 0
fi
[[ ${PUBLISH_CYCLING_SELECTOR:-} == YES ]] || {
  printf 'Set PUBLISH_CYCLING_SELECTOR=YES to explicitly create the selector draft.\n' >&2; exit 1;
}
gh pr create --repo "$repo" --head "$owner:$branch" --base master --draft \
  --title '[indexer] Support drawing rules matching feature types' --body-file "$body_file"
