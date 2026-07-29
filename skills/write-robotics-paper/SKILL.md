---
name: write-robotics-paper
description: 面向机器人论文的证据约束写作、修订、回复与主张审计 Skill；先读取均衡机器人论文语料，再以 Claim Ledger 组织可追溯稿件。
---
# 机器人论文写作 / Robotics Paper Writing

## 强制第一核心参考

在完整写作、writing-only、修订、回复或主张审计前，必须读取 `references/robotics-submanifold-routing.md` 和根目录 `references/active-corpus-first-reference.md`，并运行：

```bash
python scripts/route_robotics_research.py <profile.json> --stage writing --venue <venue>
```

把活动轴的论文范式、证据模式和 `do_not_infer` 边界用于 related-work 定位、Claim Ledger 句子审计、主张高度和证据缺口；再叠加指定 venue 当前官方范围。语料 award、factor fit 和样本数不能进入正文成为录用概率或学术等级。完成这一步后，继续完整读取并执行 `SKILL.md.source` 的原始写作契约。

## 统一 workflow 能力

读取根目录 `references/unified-venue-workflow-adapter.v1.md`。用活动轴对应的运行时
问题检查稿件是否交代了承重对象、trigger、机制动作、matched evidence 和失败边界，
再按 `claim -> result -> boundary -> task meaning` 写入 Claim Ledger。venue workflow
只改变 target-fit snapshot、篇幅和组织，不得把模拟归纳写成论文结果。

---

# English

Before full drafting, writing-only import, revision, rebuttal, or claim audit, read `references/robotics-submanifold-routing.md` and `references/active-corpus-first-reference.md`, then run:

```bash
python scripts/route_robotics_research.py <profile.json> --stage writing --venue <venue>
```

Use active-axis paper patterns, evidence patterns, and `do_not_infer` boundaries for related-work positioning, Claim Ledger sentence audits, claim altitude, and evidence gaps; then layer the target venue's current official scope. Corpus awards, factor fit, and counts must not become acceptance probability or academic rank in the manuscript. Then read and obey the preserved original writing contract in `SKILL.md.source`.

Read the root `references/unified-venue-workflow-adapter.v1.md`. Use the selected
runtime questions to check the load-bearing object, trigger, mechanism action,
matched evidence, and failure boundary, then encode them as claim, result,
boundary, and task meaning in the Claim Ledger. Never present simulation as a result.
