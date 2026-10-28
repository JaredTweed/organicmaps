# Cycling PR stack readiness

This is a preparation plan, not approval to publish. No command in this kit
updates PR #12692. The only prepared publication target is a **draft** selector
PR, from `JaredTweed:prepare/cycling-selector` to `organicmaps:master`.

| Stage | State | Required before submission |
| --- | --- | --- |
| Type selector | Prototype on upstream master `303ef27fbc`; fork head `6f9330d5c0`; exact-branch full debug `indexer_tests` passes | Maintainer agreement that this is the right first PR; inspect all existing generated rules and compiler integration; review selector semantics and performance. |
| Bicycle attributes and generation | Design not agreed; no publication branch | Agree centerline vs side information, routing/pedestrian contracts, retention and compatibility; implement and test without compromising routing or old maps. |
| Cycling style | Existing experimental implementation only | Rebase on agreed data design; verify exact solid/dashed/dotted appearance with same roads, zooms and themes; account for compiler selector fallback. |
| Dash rendering / metalines | Existing experimental implementation only | Separate independently useful rendering changes; establish MWM section version compatibility and cross-feature phase correctness. |

Do not publish placeholder dependent PRs, assume side requirements are
settled, or label the experimental phone timings a production benchmark. The
maintainer explicitly requested a reviewable first PR, not simultaneous
publication of unreviewed architectural work.

## GitHub stack constraint

On 2026-10-28 `gh repo view organicmaps/organicmaps --json viewerPermission`
returned `READ`. GitHub's documented native stacked-PR feature requires all
branches in the same repository and does not support cross-fork stacks:
[GitHub stacked PR requirements](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests).
The first fork-to-upstream PR can target upstream `master`, but later upstream
PRs cannot be assumed to target branches that exist only on the fork. This is
separate from keeping local Git branches stacked.

The user chose to prepare dependent review PRs in the fork. These will be fork
PRs, not upstream PRs; moving each change upstream after review still requires
an explicit follow-up workflow and coordination. Review visibility, CI,
retargeting and merge behavior must be communicated to maintainers. The
current selector-only launcher does not require upstream branch-write access.
No fork PRs exist yet and no dependent draft is ready to publish.

`publish-selector.sh --check` performs only read-only GitHub queries and fails
if upstream moved, the prepared branch changed, or a PR already exists.
`PUBLISH_CYCLING_SELECTOR=YES ./publish-selector.sh --publish-selector` creates
only the draft selector PR; it never pushes, updates or comments on existing
PRs. This command has **not** been run. It deliberately does not claim that the
later stack is complete. A future full-stack launcher needs actual reviewed
commits, checked tests and explicit approval for each existing PR update.

An exact-branch debug build of `indexer_tests` passed both the focused
`CyclingResearch|DruleSelector` tests and the full `indexer_tests` suite on
2026-10-28. The debug run found fixture problems fixed in `6f9330d5c0`; it
does not establish cross-platform, compiler-integration or production
performance coverage. The
default temporary filesystem hit its disk quota, so the build used a temporary
directory inside the worktree and locally available pinned submodule objects.
Upstream later advanced to `b55c734f33b2`; the only intervening change was
`.github/FUNDING.yml`, so the branch was not rewritten. The launcher checks
this newer reviewed upstream tip and fails on any further advance.
