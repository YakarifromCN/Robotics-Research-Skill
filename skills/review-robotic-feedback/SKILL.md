---
name: review-robotic-feedback
description: 面向机器人论文的多视角同行评审与修改路线 Skill；先读取均衡机器人论文语料，再按活动研究子流形轴和目标 venue 官方范围配置评审。
---
# 机器人论文反馈 / Robotics Paper Feedback

## 运行时解析与强制第一核心参考

在完整仓库中，发现稿件、启动任何 reviewer panel 或 re-review 前，必须读取 `references/robotics-submanifold-routing.md`、根目录 `references/active-corpus-first-reference.md` 和 `references/unified-venue-workflow-adapter.v1.md`，并运行：

```bash
python3 skills/review-robotic-feedback/scripts/route_robotics_research.py <profile.json> --stage review --venue <venue>
```

先用 `paper_reference_bundle` 对照活动主轴/副轴的机制范式、证据闭环和禁止外推边界，再叠加当前官方 scope、author guide、伦理、video、rebuttal 和 artifact 规则。语料奖项、factor fit 和审稿分数不得折叠成录用概率。若路由输出 `LOCAL_FALLBACK_NO_CORPUS`，必须把它记录为限制，只能选择评审问题，不能声称完成语料碰撞或 venue 结论。完成这一步后，继续完整读取并执行 `SKILL.md.source` 的原始只读评审契约。

## 统一 workflow 能力

读取根目录 `references/unified-venue-workflow-adapter.v1.md`；独立安装时读取本目录 `references/unified-venue-workflow-adapter.v1.md` 和 `references/active-corpus-first-reference.md`。按活动轴选择运行时问题，
把它们转成 panel 的 claim/mechanism/condition/contrast/failure/artifact 检查项；不适用
的问题不激活。venue-specific workflow 只进入 `venue-compliance-review` 的当前官方
scope 快照；模拟分组不能成为评分、CRITICAL finding 或录用判断。

## PDF-only 与 panel 执行边界

`discover_manuscript.py` 对 PDF 在内存中调用 `pdftotext -layout`，用抽取文本补充标题、摘要、Claim Shape 和领域包检测，并把工具状态、字符数、页面尺寸和字体预检写入 context。抽取失败时输出 `PDF_TEXT_UNAVAILABLE`，不得假装已完成领域路由。

`build_panel_prompts.py` 默认生成 `execution_mode=FRESH_SUBAGENT_PANEL`。主编排代理必须为七个角色分别启动全新 reviewer agent；代理只接收自己的 prompt 和 frozen `allowed_files`，不能读取项目记忆或其他报告。若当前运行时没有独立 agent 能力，不得手工伪装成七个自动代理；必须显式使用 `--execution-mode MANUAL_PANEL`，并在 run-state 与最终报告中披露。

---

# English

Before manuscript discovery, launching a reviewer panel, or re-review, read `references/robotics-submanifold-routing.md` and `references/active-corpus-first-reference.md`, then run:

```bash
python3 skills/review-robotic-feedback/scripts/route_robotics_research.py <profile.json> --stage review --venue <venue>
```

First compare the manuscript with active-axis mechanism patterns, evidence loops, and do-not-infer boundaries from `paper_reference_bundle`; then add the target venue's current official scope, author guide, ethics, video, rebuttal, and artifact rules. Corpus awards, factor fit, and reviewer scores must not be collapsed into an acceptance probability. If routing reports `LOCAL_FALLBACK_NO_CORPUS`, record that limitation and use it only to select review questions; do not claim corpus collision or venue conclusions. Then read and obey the preserved original read-only review contract in `SKILL.md.source`.

Read the root `references/unified-venue-workflow-adapter.v1.md`, or the bundled fallback
when this Skill is installed without the repository. Translate only
active-axis runtime questions into panel checks for claims, mechanisms, conditions,
contrasts, failures, and artifacts. Venue-specific workflow belongs only to the
current compliance snapshot; simulation cannot support a score or finding.

For PDF-only input, `discover_manuscript.py` runs `pdftotext -layout` in memory and
uses the bounded text for title, abstract, Claim Shape, and domain-pack detection;
it records page-size/font preflight and emits `PDF_TEXT_UNAVAILABLE` when extraction
fails. `build_panel_prompts.py` defaults to `FRESH_SUBAGENT_PANEL`: launch seven
fresh isolated reviewer agents. If no independent-agent runtime exists, use the
explicit `MANUAL_PANEL` mode and disclose it in run-state and final output rather
than presenting manual reports as automatic parallel reviews.
