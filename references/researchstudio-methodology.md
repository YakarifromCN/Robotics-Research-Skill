# ResearchStudio methodology distilled for robotics

Source: [ResearchStudio.pdf](../assets/ResearchStudio.pdf),
[ResearchStudio-Idea](https://arxiv.org/abs/2607.04439v1). This reference is a
robotics adaptation of the method chain, not a claim that the upstream ML
statistics transfer to robotics.

## 1. Three-layer abstraction

For each paper, keep three distinct representations:

1. **Paper record**: title, abstract/introduction or full text, venue, public
   outcome trace, review material and provenance.
2. **Innovation signature**: a paper-specific explanation of the innovation,
   critical step, cognitive barrier, trigger condition and review/outcome
   context.
3. **Strategy signature**: a domain-agnostic rewrite of only the mechanism-
   bearing fields. Replace domain nouns with generic objects, use imperative
   phrasing, preserve the reasoning move, and remove application detail.

The four fields used for strategy embeddings are:

```text
abstract strategy
abstract key step
abstract why non-obvious
abstract trigger condition
```

Keep the base fields and provenance for card evidence. Do not embed raw venue,
application, architecture or dataset names when the goal is strategy space;
that creates topic clusters rather than research-move clusters.

## 2. Unsupervised discovery contract

The production configuration from the paper is:

```text
field-prefixed four-field strategy signature
 -> text-embedding-3-large, L2-normalized
 -> UMAP(n_components=10, n_neighbors=15, min_dist=0, seed=42)
 -> HDBSCAN(min_cluster_size=10,
            min_samples=ceil(min_cluster_size/3),
            cluster_selection_method="eom")
 -> 31 fine-grained tactical clusters
```

`unclustered` is a geometric label, not a quality judgment. A paper can sit
between several strategy modes and still be fully meaningful. The upstream
workflow therefore uses an independent paper-level multi-label pass for one
to three operators, with two as the default composition; clustering is not a
hard exclusive classification.

When dependencies are unavailable, the local script must record a fallback
backend and never call it UMAP/HDBSCAN. When full-text signatures are absent,
the local run must record `METADATA_ONLY` and remain a smoke/baseline artifact.

For the current capability-injection task, model subagents are an explicitly
allowed alternative: they simulate the four-field representation and grouping,
then discard cluster identity after extracting reusable workflow questions.
This path records `SIMULATED_NOT_REAL_UMAP_HDBSCAN`; it is complete for Skill
learning but cannot be cited as statistical discovery.

## 3. Pattern-card induction

Cards are progressively disclosed:

- **Level 1 / 15 main operators**: definition, operational signature and
  when-to-apply clause. These answer “what kind of structural move could close
  this gap?”
- **Level 2 / 31 tactical cards**: signature move, step-by-step recipe,
  differentiation from siblings, trigger, success conditions, failure mode,
  reviewer expectations and paper-agnostic lessons. These answer “how does
  this candidate instantiate the move?”

The cards are non-mutually-exclusive operators. The cluster map may have one
primary parent for organization, while the paper-level representation can use
one to three composed operators. Choose by bottleneck fit, not by the most
frequent pattern or a corpus outcome signal.

Pattern cards must separate:

- positive success conditions;
- reject-derived failure shapes;
- reviewer concerns and evidence provenance;
- low-support or low-coverage warnings;
- user-facing advice versus analytical counts.

The robotics library in
`corpus/researchstudio-pattern-cards.v1.json` keeps the 15 upstream names and
adds robotics-adapted tactical cards.
`corpus/researchstudio-pattern-induction.v2.json` now maps all 15 parent and
31 tactical cards to the eight simulated capability routes. The cards remain a
reasoning vocabulary rather than an empirical taxonomy; runtime selection uses
the active-axis bottleneck and original Skill contract, not cluster frequency.

## 4. Outcome and venue semantics

Oral, High-Cited and Reject are not interchangeable labels. If their
denominators or acquisition mechanisms differ, report class-conditional
descriptions and provenance rather than a Bayesian acceptance probability.
For the current robotics corpus, the available award/presentation trace is
recognition metadata, not a decision-aligned outcome table. It is disabled as
a selection prior.

Venue scope is a separate layer. Direct robotics scope can receive a modest
directness routing weight; strong-related scope remains eligible when the
contribution lands in the corresponding learning, vision, control, HCI,
real-time or systems field. Neither directness, counts, awards nor fit scores
is a quality rank or acceptance estimator.

## 5. Online IdeaSpark-style chain

### Phase 0 — retrieve and cache

Build a multi-source evidence bundle and a small open full-text cache. Deduplicate
records across sources. Do not write the bottleneck from memory or abstract-only
fallback when a full-text check is required.

### Phase 1 — diagnose

Produce one structural bottleneck, adjacent papers and what each leaves open.
Construct a shallow method-lineage tree. Retrieved ancestors are citable;
memory-only ancestors are `awareness_only` and cannot support a novelty claim.

### Phase 2 — fit and instantiate

Select one anchor gap and one to three pattern operators by structural fit.
Choose a child tactical card under the selected parent. Generate a mechanism,
per-gap closure, nearest-work delta, resource envelope and a falsification
prediction with one load-bearing variable and a non-tautological downstream
negative control.

Run the deterministic parent/child citation gate before expensive collision
search. A card citation must resolve to the declared parent; no paper ID is
invented by a pattern card.

### Phase 3 — collision and failure audit

Re-query narrowly for mechanism-level overlap. Audit four things:

1. gap-closure failure lessons;
2. whether the cited child tactic is actually executed;
3. whether a mitigation is substantively delivered rather than keyword-stuffed;
4. whether a specific recent paper subsumes the core claim.

Exact mechanism overlap is a hard-floor `ABANDON`. A clear failure lesson or
an unexecuted child tactic yields `REVISE` when a bounded same-parent repair is
possible. Pattern frequency and saturation are explanation/audit context, not
hard gates.

### Phase 4 — expand and validate

Expand only after the decision. Keep `falsification_prediction` and
`compute_budget` byte-identical through revision and rendering. Run deterministic
validators for citation consistency, evidence provenance, claim completeness,
implementability coverage and kill-switch integrity. If the evidence cannot
support a proposal, return `DO_NOT_GENERATE` or a failed audit artifact.

## 6. Robotics-specific translation

Every pattern application must locate its mechanism in the causal chain:

```text
environment -> embodiment/sensing -> state -> decision
-> actuation/contact -> task outcome
```

The card must say what changes, which interface carries the load, what control
or user intervention distinguishes the mechanism, and what returns toward
baseline under the negative control. Add axis-specific evidence from the
per-axis report before choosing a venue scope. Then run the original local
Idea, Experiment, Writing or Review contract; the ResearchStudio layer cannot
silently rewrite Claim Lock, Design Lock or manuscript claim altitude.
