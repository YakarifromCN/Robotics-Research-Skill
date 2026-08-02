---
name: design-robotics-experiment
description: Evidence-driven robotics experiment design, audit, pilot revision, and result packaging.
---
# Robotics Experiment

本 Skill 面向机器人科研实验；常规调用只读取紧凑 runtime，不读取本地原始 100 篇语料。

## 统一 workflow 能力

通过活动轴把证据形状转换为 condition、contrast、metric、failure 与 artifact 义务。

# English

## Mandatory runtime preflight

Before any experiment action, read:

- references/robotics-submanifold-routing.md
- references/active-corpus-first-reference.md
- references/unified-venue-workflow-adapter.v1.md

Run:

~~~text
python scripts/route_robotics_research.py <profile.json> --stage experiment
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

Translate active-axis exemplar boundaries and strategy rows into candidate conditions, contrasts, metrics, failure logs, and artifact obligations. Freeze the Design Lock afterward. Runtime patterns do not replace project results, and venue preference cannot change units, denominators, exclusions, or abort policy after outcomes are observed.

Select runtime questions only when supported by the active axes. Treat the
15 parent patterns and 31 subpatterns as structural operators, not as claims
to copy. Official venue scope must be refreshed from current authoritative
sources before submission.

Then read and obey the preserved original contract in SKILL.md.source.
