---
name: write-robotics-paper
description: Evidence-constrained robotics paper writing, revision, rebuttal, and claim auditing.
---
# Robotics Paper Writing

本 Skill 面向机器人论文写作；常规调用只读取紧凑 runtime，不读取本地原始 100 篇语料。

## 统一 workflow 能力

通过活动轴和 Claim Ledger 组织 claim、result、boundary 与 task meaning。

# English

## Mandatory runtime preflight

Before any writing action, read:

- references/robotics-submanifold-routing.md
- references/active-corpus-first-reference.md
- references/unified-venue-workflow-adapter.v1.md

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

Before drafting, read `common/supervisor-research-layer.md` and reconstruct
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
15 parent patterns and 31 subpatterns as structural operators, not as claims
to copy. Official venue scope must be refreshed from current authoritative
sources before submission.

Then read and obey the preserved original contract in SKILL.md.source.
