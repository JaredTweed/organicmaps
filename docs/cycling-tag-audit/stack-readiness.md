# Cycling PR stack readiness

This is a preparation plan, not approval to publish. No command in this kit
updates PR #12692. The only prepared publication target is a **draft** selector
PR, from `JaredTweed:prepare/cycling-selector` to `organicmaps:master`.

| Stage | State | Required before submission |
| --- | --- | --- |
| Type selector | Prototype cherry-picked to upstream master `303ef27fbc`; fork branch prepared | Maintainer agreement that this is the right first PR; clean exact-branch build and tests; inspect all existing generated rules and compiler integration; review selector semantics and performance. |
| Bicycle attributes and generation | Design not agreed; no publication branch | Agree centerline vs side information, routing/pedestrian contracts, retention and compatibility; implement and test without compromising routing or old maps. |
| Cycling style | Existing experimental implementation only | Rebase on agreed data design; verify exact solid/dashed/dotted appearance with same roads, zooms and themes; account for compiler selector fallback. |
| Dash rendering / metalines | Existing experimental implementation only | Separate independently useful rendering changes; establish MWM section version compatibility and cross-feature phase correctness. |

Do not publish placeholder dependent PRs, assume side requirements are
settled, or label the experimental phone timings a production benchmark. The
maintainer explicitly requested a reviewable first PR, not simultaneous
publication of unreviewed architectural work.

`publish-selector.sh --check` performs only read-only GitHub queries and fails
if upstream moved, the prepared branch changed, or a PR already exists.
`PUBLISH_CYCLING_SELECTOR=YES ./publish-selector.sh --publish-selector` creates
only the draft selector PR; it never pushes, updates or comments on existing
PRs. This command has **not** been run. It deliberately does not claim that the
later stack is complete. A future full-stack launcher needs actual reviewed
commits, checked tests and explicit approval for each existing PR update.

The prepared source files match the tested research selector prototype exactly;
the existing research build passed its focused native tests. That binary was
not built from this exact branch, so its result is not a clean branch build.
An exact-branch configure was attempted with `SKIP_QT_GUI=ON`; it could not
complete because the new worktree's third-party submodules were not initialized.
The default temporary filesystem also hit its disk quota; setting `TMPDIR` to
the worktree's build directory got past that error. Initializing the pinned
submodules was started but did not finish, so this remains a release gate.
