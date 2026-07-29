# Corpus-first + ResearchStudio routing contract

Every robotics research stage starts with:

```text
python scripts/route_robotics_research.py <profile.json> --stage idea|experiment|writing|review
```

The entrypoint hard-loads and validates:

1. `corpus/public-paper-index.json`: the balanced 100-paper corpus, 50 journal and 50 conference records;
2. `corpus/robotics-submanifold.v1.json`: the eight transparent robotics research axes;
3. `corpus/venue-catalog.v2.json`: the rating-free venue scope catalog, with directness as an optional routing prior;
4. `corpus/researchstudio-paper-signatures.v2.json`: the mixed-fidelity, field-provenance paper-analysis contract (`v1` remains the metadata-only compatibility baseline);
5. `corpus/researchstudio-pattern-cards.v1.json`: 15 parent operators and 31 robotics-adapted tactical cards;
6. `corpus/researchstudio-pattern-induction.v2.json`: the complete model-simulated 15/31 capability mapping;
7. `corpus/robotics-axis-strategy-analysis.v2.json`: the regenerated per-axis strategy and venue-scope candidate report;
8. `corpus/researchstudio-outcome-contrast.v1.json`: the closed-by-design outcome contract.

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

The compatibility implementation in `scripts/induce_researchstudio_patterns.py`
still emits explicit `FALLBACK_NOT_UMAP` / `FALLBACK_NOT_HDBSCAN` when real
dependencies and vectors are absent. For the current Skill-learning path, model
subagents simulate Stage-2 embedding and grouping without an external API. The
runtime consumes only the derived capability questions and 15/31 mapping; it
does not expose internal cluster IDs or claim real UMAP/HDBSCAN. Signatures v2
separately report `FULLTEXT_EXTRACTED` and `FULLTEXT_WEB_VERIFIED` records with
field-level provenance.

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
- The outcome contrast is complete by explicit closure when no decision-aligned denominator exists; award or presentation traces are never substituted.
- Directness weights help route a robotics-native scope before a strong-related scope; there are no rating or prestige fields in this layer.
- Venue candidates require a fresh official-scope/author-guide/ethics/artifact check before submission.
- The four local skills keep their original contracts in `SKILL.md.source`; this reference adds the shared first-mile context and does not rewrite Claim Lock or Design Lock.
