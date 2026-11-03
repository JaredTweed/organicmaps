# OM Test Presentation Promotion

The author requested replacing the split integration's presentation with the
installed **OM Test** experiment. This is an intentional visual revision after
the earlier nonvisual cleanup. Historical nonvisual and native reports retain
their original source pins; they are not relabeled as tests of this revision.

## Scope

Only part 8 (#14043) and the combined #12692 preview acquire these style changes.
Parts 1-7 and independent #14054 retain their source heads. No classifier, map,
routing, topology, offset geometry, arrow geometry or shader code changes.

- Neutral gray car roads and subdued building context in both themes.
- Routine shopping/dining/office/parking icons suppressed through zoom 17.
- Viewpoints suppressed through zoom 15; minor residential/service road labels
  through zoom 14; addresses through zoom 18. Detailed presentation resumes at
  higher zooms. Bicycle shops and existing cycling services remain available.
- Cycling colors, line widths, patterns, symbols and displacement remain the
  same. Solid/dashed/dotted still describe facility categories, not pavement.

The prototype changes **default as well as cycling**. The renderer borrows
default road cores; default palette variables also flow into other families.
This broad effect is preserved deliberately for exact OM Test equivalence,
not hidden as a cycling-mode-only change. Maintainers still need to agree
whether the final product should isolate the presentation to a cycling mode.

Shared declarations now live in `data/styles/common`, with explicit imports
from default/cycling. This avoids duplicate palettes and a default-to-cycling
include dependency. Source and generated assets have separate signed commits.

## Evidence

[Generated-output audit](quiet-style-promotion.json) verifies every regenerated
output against OM Test's generation directory, and each packaged matching asset
against the saved `OM-Test.apk`. It also compares line geometry and cycling line
rules across all four style families and both variants. Native code and
classifier/pattern mappings remain unchanged relative to `ef743e8134`.

The private compiler runs serially under a 1800 MiB memory cap with no extra
swap. The regenerated baseline matched the previously installed source before
the experiment was made. The matching source `3ab7ff9e66` passes
[239 native checks](quiet-style-native-results.json): 193 full indexer and
46 focused renderer tests. The research suite passes 79 tests. A test attempt
using a newer master binary was discarded because
its fixture expected a waterway type absent from this older style base.

The existing phone experiment was inspected at overview zoom in light/dark and
at close zoom in dark. Those are spot checks, not a controlled pixel-equivalence
certificate. The phone's road-only Vancouver fixture is unchanged; the proposed
full-map/coastline script is separate, incomplete work and is not part of these
PRs. No new full-region map or routing validation is claimed.

Both previews still target `ab/cycling-style`. Full CI, review of this broader
presentation change, the schema/renderer/generator decisions already recorded,
and eventual integration onto master remain outstanding. Earlier GitHub
approval of #12692 is not evidence of review of the newly promoted styling.
