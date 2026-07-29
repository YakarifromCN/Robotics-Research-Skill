---
name: develop-robotics-idea
description: 面向机器人科研的证据驱动 Idea Skill；先以 100 篇均衡论文语料建立研究子流形参考，再形成、审计、接纳或迁移可证伪研究主张。
---
# 机器人 Idea / Robotics Idea

## 强制第一核心参考

在任何 Idea 生成、审计、接纳或迁移动作之前，必须先读取 `references/robotics-submanifold-routing.md` 和根目录 `references/active-corpus-first-reference.md`，并运行：

```bash
python scripts/route_robotics_research.py <profile.json> --stage idea
```

该入口硬加载并校验 `corpus/public-paper-index.json` 的 100 篇论文、八轴模型、`venue-catalog.v2.json` 和校准报告。必须把输出中的 `paper_reference_bundle`、`research_intensity`、`proposed_evidence_pressures` 和 `factor_fit_ranking` 作为第一轮先例/机制/证据参考，再进入本 Skill 的原始合同流程。

语料范式只能帮助碰撞检查、机制区分和主张高度审计；不得把奖项、venue fit 或论文数量写成质量/录用概率，也不得静默改写 Claim Lock。完成上述步骤后，继续完整读取并执行保留的原始契约：`SKILL.md.source`。

## 统一 workflow 能力

读取根目录 `references/unified-venue-workflow-adapter.v1.md`。从活动轴选择其中与
项目相符的运行时问题，把它们转为候选 contribution center、承重对象、trigger、
机制反证和 sibling collision 查询；然后由原始合同冻结 Claim Lock。外部 venue
workflow 只提供 scope/audience 检查，不创建 venue-specific Idea 流程，也不能把
模拟分组、venue fit 或奖项写成创新证据。

---

# English

Before any Idea generation, audit, adoption, or migration, read `references/robotics-submanifold-routing.md` and `references/active-corpus-first-reference.md`, then run:

```bash
python scripts/route_robotics_research.py <profile.json> --stage idea
```

The entry point hard-loads and validates the 100-paper corpus, eight-axis model, rating-free v2 venue catalog, and calibration report. Use `paper_reference_bundle`, `research_intensity`, `proposed_evidence_pressures`, and `factor_fit_ranking` as the first prior-art/mechanism/evidence reference. Corpus patterns may inform collision checks, mechanism distinction, and claim altitude, but awards, venue fit, and counts are not quality or acceptance probability. Do not silently rewrite Claim Lock. Then read and obey the preserved original contract in `SKILL.md.source`.

Read the root `references/unified-venue-workflow-adapter.v1.md`. Select only the
runtime questions supported by the active axes, translate them into candidate
contribution centers, load-bearing objects, triggers, falsifiers, and sibling
collision searches, and then freeze the Claim Lock under the original contract.
