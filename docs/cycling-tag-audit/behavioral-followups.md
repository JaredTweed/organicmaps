# Behavioral fixes outside the equivalence stack

The baseline must preserve PR #12692 at
`955cd49403ed025c24beec09f5551e8d274a38ff`. Useful fixes are not automatically
appearance-neutral. These preparation branches on the fork are deliberately excluded from
`rollout.sh` and must receive their own review and rendering evidence.

## Conflicting-tag precedence

- Baseline: `prepare/cycling-equivalence-types`, `33c33e44b0`.
- Follow-up: `prepare/cycling-order-followup`, `9e7915de8d`.
- Makes a positive side-specific facility override `cycleway=no` regardless
  of input tag order. It can change bicycle flags and cycling styling on
  conflicting-tag ways; that is a behavioral correction, not extraction.
- The follow-up tree equals the earlier tested types candidate `29c724492b`.

## Collision-free chain grouping

- Baseline: `prepare/cycling-equivalence-metalines`, `30ebe4827d`.
- Follow-up: `prepare/cycling-chain-key-followup`, `9990d07b85`.
- Replaces hashed/synthetic grouping identities with explicit tagged keys.
  Collisions can alter chain membership, ordering, reversal and phase. A fix
  must not be bundled with a supposedly equivalent compatibility format.
- Builder sources and metalines fixtures equal the earlier tested candidate
  `af080bbfb1`; the follow-up still needs its own exact-head validation.

## Side-aware rendering

vng's offset-line proposal is separate from both fixes. The user selected
#12692's centerline appearance as the baseline. Left/right/both geometry,
per-side directions and pedestrian reuse require an explicit side-aware
model and a separate visual proposal; none is silently implemented here.

The first two follow-ups are independent on their recorded bases. Combining
them later requires an explicit integration, not assuming either branch
already contains the other.

Earlier exact tested revisions are retained on fork branches
`prepare/cycling-style-prior-audit` (`f8f603fc7e`) and
`prepare/cycling-dash-prior-audit` (`29834257a1`). They are provenance archives,
not new PRs or dependencies of the updated baseline.
