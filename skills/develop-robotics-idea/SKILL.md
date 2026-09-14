---
name: develop-robotics-idea
description: Evidence-driven robotics research ideation, prior-art collision audit, adoption, and migration. Use for forming or auditing the scientific object and Claim Lock; route scoped code implementation, debugging, ROS integration, controller changes, and engineering tuning to develop-robotics-engineering.
---
# Robotics Idea

本 Skill 面向机器人科研 Idea；常规调用只读取紧凑 runtime，不读取本地原始 100 篇语料。

## 统一 workflow 能力

通过活动轴选择贡献中心、证据形状、失败边界与 venue scope 检查。

# English

## Progressive runtime preflight

Read the user artifact first, then at most two references: `references/core-contract.md` for a Research Card, `references/robotics-submanifold-routing.md` for axis routing, or `references/official-venue-policy.md` only for a venue decision. Do not preload sibling Skills, the shared corpus reference, venue catalogs, PDFs, or offline induction artifacts.

Run:

~~~text
python3 <installed-skill-dir>/scripts/route_robotics_research.py <profile.json> --stage idea
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

For a multi-stage candidate audit, read `common/supervisor-research-layer.md` as one of the two selected references and apply its idea-stage gates:

- classify the project as `TECHNIQUE`, `NEW_PROBLEM_SETTING`,
  `BENCHMARK_EVALUATION`, or `MIXED`, then state a one-sentence story;
- run fatal-flaw and closest-work collision checks before any innovation
  scoring; a `CRITICAL` flaw short-circuits the run;
- use `Higher/Faster/Stronger/Cheaper/Broader` as evidence-labelled
  directional probes, never as a total score or acceptance model;
- check lifecycle, compute, data, engineering, and timeline fit against the
  user's actual resources;
- keep the paper-positioning chain inside the Research Card audit: no more
  than three load-bearing limitations and challenges, a one-sentence goal or
  key idea, and an explicit challenge-to-mechanism relationship;
- hand a viable idea to `design-robotics-experiment` when evidence conditions
  are not frozen, or to `write-robotics-paper` when the evidence artifacts are
  ready. Do not jump from a high idea score directly to prose.

## Stage contract

Use the active-axis compact paper exemplars for prior-art collision checks, mechanism distinction, claim altitude, evidence pressure, and falsification planning. Do not silently rewrite the Claim Lock. The venue catalog supplies routing context only; it does not turn awards, directness, or factor fit into quality or acceptance probability.

Select runtime questions only when supported by the active axes. Treat the
runtime-active tactical cards as structural operators, never offline seed cards or claims
to copy. Official venue scope must be refreshed from current authoritative
sources before submission.
