@vng Here is the proposed scope for the split stack; these are proposals for review, not assumptions that the remaining design questions are settled.

- **Model:** retain the road's main type and add one `cyclewaytag` (`track`/`lane`/`shared_lane`). Keep classifier types for this first step; reconsider a richer feature section if side-specific or pedestrian attributes require it.
- **Visuals:** one centerline summary, choosing the least-protected explicitly tagged category where sides/directions differ. No per-side rendering or arrows. Preserving the solid/dashed/dotted appearance is the goal; identical style sources are not a pixel-equivalence proof.
- **Eight-type limit:** a local priority experiment produced identical aggregate type-combination dumps on the Vancouver road extract (209 lines containing `cyclewaytag`, not 209 roads). This does not establish per-road equality or show that the cap can never discard cycling data. Prioritizing cycling can displace access/direction/surface types, which needs matched-feature measurements before changing the ranking. The current ranking remains.
- **Routing:** #14041 changes access/direction flags as well as display classification. Those flags and type retention can affect both styling and routing; I am not claiming they are independent. The `motor_vehicle=permissive` access change is a candidate for extraction if you want it reviewed separately. Generated route-graph tests are still required.
- **Pedestrians:** proposed follow-up, not implemented in this stack.
- **Format:** v3 metalines are rejected by v1-only clients, losing merged label/shield placement. This remains an explicit merge blocker pending acceptance or a tested additive section; a trailing extension is not assumed backward-safe.

The split, in review order:

1. #14040: selector
2. #14041: cycling types (cumulative against master)
3. #14048: metalines offsets (cumulative against master)
4. #14042: continuous dash phase (cumulative against master)
5. #14043: cycling style preview (not for merge as-is)

I would focus review on 1/5 first. The cumulative PRs need rebasing as their prerequisites land; they are not isolated GitHub diffs. #12692's code is unchanged.
