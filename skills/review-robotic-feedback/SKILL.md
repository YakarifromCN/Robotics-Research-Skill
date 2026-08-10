---
name: review-robotic-feedback
description: Multi-perspective robotics peer review and academic revision routing grounded in active research axes and official venue scope. Use for review findings and scientific revision decisions; route requested code fixes or implementation work arising from reviews to develop-robotics-engineering.
---
# Robotics Paper Feedback

本 Skill 面向机器人论文评审；常规调用只读取紧凑 runtime，不读取本地原始 100 篇语料。

## 统一 workflow 能力

通过活动轴、贡献中心、证据形状和官方 scope 组装评审面板。

# English

## Progressive runtime preflight

Read the frozen manuscript/evidence context first, then at most two references: the local routing reference for active axes, the review protocol for panel contracts, or official venue policy only for venue compliance. Do not preload sibling Skills, the corpus, PDFs beyond the explicit manuscript, or all reviewer prompts.

Run:

~~~text
python scripts/route_robotics_research.py <profile.json> --stage review --venue <venue>
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

For a full multi-axis panel, read `common/supervisor-research-layer.md` as one selected reference and
settle paradigm and current official venue scope. Add the Supervisor review
dimensions to the robotics panel: macro logic, writing details, grammar,
LaTeX, and figure quality, alongside axis-specific evidence, mechanism
attribution, baseline fairness, and artifact checks. Every finding needs a
real quote, file line, artifact ID, contract path, or source URL. Use
`CRITICAL`, `MAJOR`, and `MINOR` honestly; unresolved `CRITICAL` findings
block readiness. The review recommends a next action and never emits a true
acceptance probability from scores, awards, or venue labels.

## Stage contract

Compare the manuscript with active-axis mechanism patterns, evidence loops, and do-not-infer boundaries. Then add current venue scope, author-guide, ethics, video, rebuttal, and artifact rules. Awards, factor fit, and reviewer scores must not be collapsed into acceptance probability. A standalone installation may disclose a local runtime fallback, but the complete workspace must use the compact runtime artifact.

Select runtime questions only when supported by the active axes. Treat the
runtime-active tactical cards as structural operators, not seed cards or claims
to copy. Official venue scope must be refreshed from current authoritative
sources before submission.
