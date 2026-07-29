# Corpus-first + ResearchStudio routing contract

Every robotics research stage starts with:

```text
python scripts/route_robotics_research.py <profile.json> --stage idea|experiment|writing|review
```

The entrypoint hard-loads and validates:

1. `corpus/public-paper-index.json`: the balanced 100-paper corpus, 50 journal and 50 conference records;
2. `corpus/robotics-submanifold.v1.json`: the eight transparent robotics research axes;
3. `corpus/venue-catalog.v2.json`: the rating-free venue scope catalog, with directness as an optional routing prior;
4. `corpus/researchstudio-paper-signatures.v1.json`: the paper-analysis contract;
5. `corpus/researchstudio-pattern-cards.v1.json`: 15 parent operators and 31 robotics-adapted tactical cards;
6. `corpus/robotics-axis-strategy-analysis.v1.json`: the per-axis anchor/support pattern baseline.

The resulting JSON contains both `paper_reference_bundle` and
`researchstudio_strategy_context`. Use the latter to read, for each active
axis, the anchor pattern, supporting composition, tactical subpatterns,
evidence recipe, failure guard, claim altitude and venue-scope candidates.
The pattern is a structural operator, not the contribution claim. Select it
from the diagnosed gap before consulting frequency, recognition or venue
context.

## ResearchStudio chain

```text
paper x_i + descriptive outcome y_i
  -> Stage-1 structured signature
  -> Stage-2 domain-agnostic strategy signature
  -> embedding -> UMAP -> HDBSCAN
  -> fine-grained tactical clusters
  -> pattern-card induction and outcome-contrast audit
```

The runtime implementation is in `scripts/induce_researchstudio_patterns.py`.
It uses real UMAP/HDBSCAN when the optional dependencies and vectors exist;
otherwise it emits explicit `FALLBACK_NOT_UMAP` / `FALLBACK_NOT_HDBSCAN` status.
The current 100-paper run is `METADATA_ONLY`: its signatures are an adapter
for infrastructure and axis strategy baselines, not a claim of full-text LLM
extraction or true induced clusters.

## Online idea chain

```text
retrieve evidence -> diagnose bottleneck and method lineage
-> fit one to three patterns -> instantiate a subpattern
-> mechanism-level collision audit -> failure-mode audit
-> ADVANCE / REVISE / ABANDON -> deterministic Idea Card validation
```

Use `scripts/ideate_robotics_research.py` for the chain. Missing literature,
full-text grounding, collision evidence, or a concrete structural gap is an
honest stop state; the runtime must not fill it from memory. The deterministic
validator preserves `falsification_prediction` and `compute_budget` exactly.

## Shared boundaries

- Corpus and pattern outcomes are descriptive audit context. Acceptance probability is always `NOT_ESTIMABLE`.
- Directness weights help route a robotics-native scope before a strong-related scope; there are no rating or prestige fields in this layer.
- Venue candidates require a fresh official-scope/author-guide/ethics/artifact check before submission.
- The four local skills keep their original contracts in `SKILL.md.source`; this reference adds the shared first-mile context and does not rewrite Claim Lock or Design Lock.
