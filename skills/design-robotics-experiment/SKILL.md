---
name: design-robotics-experiment
description: "Design and audit scientific robotics experiments: hypotheses, conditions, comparators, metrics, units, denominators, analyses, pilot revision, and result packaging. Do not use for code implementation, debugging, feature development, ROS or hardware integration, controller or optimizer implementation, model-training code, or engineering tuning; route those tasks to develop-robotics-engineering."
---
# Robotics Experiment

本 Skill 面向机器人科研实验；常规调用只读取紧凑 runtime，不读取本地原始 100 篇语料。

## 统一 workflow 能力

通过活动轴把证据形状转换为 condition、contrast、metric、failure 与 artifact 义务。

# English

## Progressive runtime preflight

Read the Research Card first, then at most two references: `references/core-contract.md` for Contract/Result schemas, `references/robotics-evidence.md` for a robotics evidence boundary, or the routing reference only when axes are unresolved. Do not preload sibling Skills, corpus sources, PDFs, venue catalogs, or offline induction artifacts.

Run:

~~~text
python3 <installed-skill-dir>/scripts/route_robotics_research.py <profile.json> --stage experiment
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

For a complex multi-stage design, read `common/supervisor-research-layer.md` as one selected reference. Build one auditable row per load-bearing
challenge: mechanism intervention, comparator or negative control, metric and
independent unit, expected falsification signature, failure log, and artifact.
Keep the `limitations -> goal -> challenges -> modules -> contributions`
chain visible; normally do not exceed three challenges. For benchmark or
evaluation projects, additionally audit the five pillars: research gap,
construction pipeline, evaluation framework, empirical capability boundaries,
and optional companion method. Organise experiments by research question and
do not let target-venue preference change denominators or add post-hoc tests.

## Stage contract

Translate active-axis exemplar boundaries and strategy rows into candidate conditions, contrasts, metrics, failure logs, and artifact obligations. Freeze the Design Lock afterward. Runtime patterns do not replace project results, and venue preference cannot change units, denominators, exclusions, or abort policy after outcomes are observed.

Select runtime questions only when supported by the active axes. Treat the
runtime-active tactical cards as structural operators, not seed cards or claims
to copy. Official venue scope must be refreshed from current authoritative
sources before submission.
