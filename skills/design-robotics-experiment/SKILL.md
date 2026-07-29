---
name: design-robotics-experiment
description: 面向机器人科研的实验设计、审计、微调与结果封装 Skill；先读取均衡机器人论文语料，再将锁定主张变成可执行证据合同。
---
# 机器人实验 / Robotics Experiment

## 强制第一核心参考

开始任何实验设计、pilot 修订、回顾审计或结果封装前，必须读取 `references/robotics-submanifold-routing.md` 和根目录 `references/active-corpus-first-reference.md`，并运行：

```bash
python scripts/route_robotics_research.py <profile.json> --stage experiment
```

先用 `paper_reference_bundle.axis_pattern_summary` 将活动轴的论文范式转为候选 condition、contrast、metric、analysis、失败日志和 artifact 任务；再冻结 Design Lock。语料均值不能替代项目结果，venue 偏好不能事后改变单位、分母、排除或 abort policy。完成这一步后，继续完整读取并执行 `SKILL.md.source` 的原始实验合同。

---

# English

Before experiment design, pilot amendment, retrospective audit, or result packaging, read `references/robotics-submanifold-routing.md` and `references/active-corpus-first-reference.md`, then run:

```bash
python scripts/route_robotics_research.py <profile.json> --stage experiment
```

First translate `paper_reference_bundle.axis_pattern_summary` for the active axes into candidate conditions, contrasts, metrics, analyses, failure logs, and artifact tasks; only then freeze the Design Lock. Corpus summaries do not replace project results, and venue preference must not change units, denominators, exclusions, or abort policy after outcomes are observed. Then read and obey the preserved original experiment contract in `SKILL.md.source`.
