---
name: review-robotic-feedback
description: 面向机器人论文的多视角同行评审与修改路线 Skill；先读取均衡机器人论文语料，再按活动研究子流形轴和目标 venue 官方范围配置评审。
---
# 机器人论文反馈 / Robotics Paper Feedback

## 强制第一核心参考

在发现稿件、启动任何 reviewer panel 或 re-review 前，必须读取 `references/robotics-submanifold-routing.md` 和根目录 `references/active-corpus-first-reference.md`，并运行：

```bash
python scripts/route_robotics_research.py <profile.json> --stage review --venue <venue>
```

先用 `paper_reference_bundle` 对照活动主轴/副轴的机制范式、证据闭环和禁止外推边界，再叠加当前官方 scope、author guide、伦理、video、rebuttal 和 artifact 规则。语料奖项、factor fit 和审稿分数不得折叠成录用概率。完成这一步后，继续完整读取并执行 `SKILL.md.source` 的原始只读评审契约。

---

# English

Before manuscript discovery, launching a reviewer panel, or re-review, read `references/robotics-submanifold-routing.md` and `references/active-corpus-first-reference.md`, then run:

```bash
python scripts/route_robotics_research.py <profile.json> --stage review --venue <venue>
```

First compare the manuscript with active-axis mechanism patterns, evidence loops, and do-not-infer boundaries from `paper_reference_bundle`; then add the target venue's current official scope, author guide, ethics, video, rebuttal, and artifact rules. Corpus awards, factor fit, and reviewer scores must not be collapsed into an acceptance probability. Then read and obey the preserved original read-only review contract in `SKILL.md.source`.
