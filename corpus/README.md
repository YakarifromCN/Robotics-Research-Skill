# Robotics research corpus and runtime

The complete 100-paper index is a local-only offline input. It is not required
for a normal Skill invocation and is not committed to Git.

~~~text
local corpus -> offline validation/build -> robotics-research-runtime.v1.json
                                      -> normal route reads runtime only
~~~

Tracked runtime:

- robotics-research-runtime.v1.json: compact exemplars, source digest, eight
  axis strategy rows, pattern-system summary, and non-claims;
- robotics-submanifold.v1.json: transparent axis model;
- venue-catalog.v2.json: venue scope and directness priors;
- researchstudio-pattern-cards.v1.json: 15 parent and 31 subpattern cards;
- researchstudio-pattern-induction.v2.json,
  robotics-axis-strategy-analysis.v2.json, and
  researchstudio-outcome-contrast.v1.json: auditable aggregate ResearchStudio
  results.

Local-only corpus and paper-level intermediates include
public-paper-index.json, paper-level signature indexes, PDFs, extracted text,
embeddings, and agent-internal simulation files. Provenance manifests and
full-text receipts may remain tracked because they do not contain the corpus
records or paper text.

Build or audit explicitly:

~~~text
python scripts/validate_public_paper_index.py <local-corpus>
python scripts/build_robotics_research_runtime.py --input <local-corpus>
python scripts/validate_robotics_research_runtime.py
~~~

The runtime is descriptive research infrastructure. It does not claim
statistical PCA, latent-factor fitting, real UMAP/HDBSCAN, prevalence, quality
ranking, or acceptance probability.
