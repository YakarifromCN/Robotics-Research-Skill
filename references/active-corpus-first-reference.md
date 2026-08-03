# Runtime-first robotics research routing contract

Normal Idea, Experiment, Writing, and Review calls begin with:

~~~text
python scripts/route_robotics_research.py <profile.json> --stage idea|experiment|writing|review
~~~

The router reads the tracked compact artifact
corpus/robotics-research-runtime.v1.json. It does not read
corpus/public-paper-index.json, paper-level signatures, PDFs, extracted text,
or embedding caches. The complete balanced 100-paper corpus is a local-only
input for the explicit offline build and audit workflow.

The runtime artifact contains:

1. the eight transparent robotics research axes;
2. compact paper exemplars and extract/do-not-infer boundaries for each axis;
3. the eight axis strategy rows distilled from the ResearchStudio analysis;
4. the 15 parent pattern cards and 31 subpattern cards;
5. the closed outcome contract, whose acceptance field is always
   NOT_ESTIMABLE;
6. venue-scope candidates that must be refreshed against official sources.

The output contains paper_reference_bundle and
researchstudio_strategy_context. Use them as first-mile structural
references for mechanism distinction, evidence obligations, claim altitude,
failure audits, and venue-scope routing. They are not prevalence estimates,
quality scores, or acceptance probabilities.

## Offline corpus lifecycle

~~~text
local raw corpus (not Git)
        -> validate / analyze / rebuild offline
        -> robotics-research-runtime.v1.json (tracked)
        -> normal Skill invocation reads runtime only
~~~

Set ROBOTICS_CORPUS_PATH or pass an explicit path when rebuilding:

~~~text
python tools/corpus/validate_public_paper_index.py <local-corpus>
python tools/corpus/build_robotics_research_runtime.py --input <local-corpus>
python tools/corpus/validate_robotics_research_runtime.py
~~~

The runtime records the source corpus SHA-256 and the source count for
provenance, but never requires the source path to exist at runtime.

## ResearchStudio chain

~~~text
paper x_i + descriptive outcome y_i
  -> structured innovation signature
  -> domain-agnostic strategy signature
  -> embedding / UMAP / HDBSCAN when explicitly available
  -> fine-grained strategy clusters
  -> pattern-card induction and outcome audit
~~~

The checked-in pattern and axis artifacts preserve the model-simulation
boundary. They do not claim that statistical PCA, latent-factor estimation,
real UMAP/HDBSCAN, or an acceptance model was run.

## Online idea chain

~~~text
retrieve evidence -> diagnose bottleneck and method lineage
-> fit one to three patterns -> instantiate a subpattern
-> mechanism-level collision audit -> failure-mode audit
-> ADVANCE / REVISE / ABANDON -> deterministic Idea Card validation
~~~

Missing literature, full-text grounding, collision evidence, or a concrete
structural gap is an honest stop state. The runtime must not fill it from
memory. The deterministic validator preserves falsification_prediction and
compute_budget exactly.

## Shared boundaries

- Raw corpus and paper-level intermediate files are offline-only and ignored by Git.
- Runtime artifacts are descriptive research infrastructure, not statistical
  prevalence models or acceptance predictors.
- Directness can be used as a routing weight, but ratings are not a core axis.
- Venue candidates require current official-scope, author-guide, ethics, and
  artifact checks before submission.
- The four local skills contain their current stage contracts directly in
  `SKILL.md`; this reference supplies shared runtime context without rewriting
  Claim Lock or Design Lock.
