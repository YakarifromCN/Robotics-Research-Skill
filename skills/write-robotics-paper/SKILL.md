---
name: write-robotics-paper
description: Evidence-constrained robotics paper writing, revision, rebuttal, claim auditing, and bidirectional contribution calibration. Use for drafting from locked research artifacts, revising overclaimed or underclaimed prose, reducing defensive academic writing without deleting necessary caution, and preserving claim/result/number/citation traceability.
---
# Robotics Paper Writing

本 Skill 面向机器人论文写作；常规调用只读取紧凑 runtime，不读取本地原始 100 篇语料。

## 统一 workflow 能力

通过活动轴和 Claim Ledger 组织 claim、result、boundary 与 task meaning。

# English

## Progressive runtime preflight

Read the Claim Ledger and supplied manuscript first, then at most two references: `references/core-contract.md`, `references/claim-evidence-writing.md`, `references/evidence-bound-revision.md` for existing-prose revision, or official venue policy only when formatting for a venue. Do not preload sibling Skills, the corpus, PDFs, venue catalogs, or reviewer prompts.

Run:

~~~text
python scripts/route_robotics_research.py <profile.json> --stage writing --venue <venue>
~~~

The normal route reads only the tracked compact artifact
corpus/robotics-research-runtime.v1.json. It does not load
corpus/public-paper-index.json, paper-level signatures, PDFs, extracted text,
or embedding caches. The full 100-paper corpus is a local-only input for the
explicit offline build and audit scripts.

Use paper_reference_bundle, research_intensity, factor_fit_ranking,
researchstudio_strategy_context, and the active-axis stage adapter as the
shared first-mile context.

## Supervisor-Skills distillation

For a full research-to-paper reconstruction, read `common/supervisor-research-layer.md` as one selected reference and reconstruct
the argument chain directly from the Research Card, Experiment Contract, and
Result Bundle. If the logic chain is not locked, route back to
`develop-robotics-idea` or `design-robotics-experiment` before prose. For a technical paper, preserve the
six-part chain `background/running example -> limitations -> goal/key idea ->
challenges -> solution overview -> contributions`; for a benchmark paper,
use its distinct evaluation-gap/RQ/design chain. Build an Evidence Map before
the Claim Ledger, keep every factual sentence within user material, verified
retrieval, or field common knowledge, and never use placeholders to hide a
missing source. Treat the motivated example, solution overview, and results
figures as load-bearing narrative objects linked to claims and sections.

## Stage contract

Use active-axis paper patterns, evidence boundaries, and do-not-infer limits for related-work positioning, Claim Ledger sentence audits, claim altitude, and evidence gaps. Then layer the target venue's current official scope. Runtime summaries must never become acceptance probability, academic rank, or manuscript evidence.

Select runtime questions only when supported by the active axes. Treat the
runtime-active tactical cards as structural operators, not seed cards or claims
to copy. Official venue scope must be refreshed from current authoritative
sources before submission.

## Evidence-bound revision

For revision, rebuttal, camera-ready compression, or defensive-writing audit,
read `references/evidence-bound-revision.md`. Diagnose lexical cues only as
candidates. Bind the revision artifact to the Claim Ledger digest and its
change envelope before editing. If authority is absent, stop at diagnosis.

Calibrate in both directions: strengthen underclaimed prose up to the frozen
evidence ceiling, keep at-ceiling prose, narrow overclaim, and repair a
misaligned claim type. Preserve evidence functions and stable IDs rather than
duplicate sentences. Run `scripts/validate_revision_audit.py`, the Claim Ledger
validator, and the LaTeX audit before declaring the revision ready.
