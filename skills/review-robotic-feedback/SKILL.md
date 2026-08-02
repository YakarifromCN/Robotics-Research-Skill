---
name: review-robotic-feedback
description: Multi-perspective robotics peer review and revision routing grounded in active research axes and official venue scope.
---
# Robotics Paper Feedback

本 Skill 面向机器人论文评审；常规调用只读取紧凑 runtime，不读取本地原始 100 篇语料。

## 统一 workflow 能力

通过活动轴、贡献中心、证据形状和官方 scope 组装评审面板。

# English

## Mandatory runtime preflight

Before any review action, read:

- references/robotics-submanifold-routing.md
- references/active-corpus-first-reference.md
- references/unified-venue-workflow-adapter.v1.md

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

## Stage contract

Compare the manuscript with active-axis mechanism patterns, evidence loops, and do-not-infer boundaries. Then add current venue scope, author-guide, ethics, video, rebuttal, and artifact rules. Awards, factor fit, and reviewer scores must not be collapsed into acceptance probability. A standalone installation may disclose a local runtime fallback, but the complete workspace must use the compact runtime artifact.

Select runtime questions only when supported by the active axes. Treat the
15 parent patterns and 31 subpatterns as structural operators, not as claims
to copy. Official venue scope must be refreshed from current authoritative
sources before submission.

Then read and obey the preserved original contract in SKILL.md.source.
