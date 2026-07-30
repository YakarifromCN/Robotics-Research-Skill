# 审稿 Skill 的语料优先降级参考 / Corpus-first fallback reference for review

完整 Robotics-Research-Skill 仓库中，审稿前应读取根目录的 100 篇公开机器人论文语料、八轴子流形、ResearchStudio 策略卡和 venue catalog，并运行完整路由器。独立安装只有本 Skill 时，使用本文件和 `scripts/route_robotics_research.py` 的 `LOCAL_FALLBACK_NO_CORPUS` 输出；不得把它误报为已加载语料。

独立安装仍可以：

- 根据稿件内容选择 E/P/C/L/D/H/A/S 评审问题；
- 检查任务、机制、条件、对照、指标、失败边界和工件链；
- 保留 `NOT_ESTIMABLE`、`EVIDENCE_GAPS` 和 `NOT_ASSESSABLE`。

独立安装不能仅凭本地 fallback 声称完成最近工作碰撞、语料支持或目标载体官方合规判断；这些结论必须回到完整仓库和新鲜官方来源。

# English

In the complete Robotics-Research-Skill repository, review starts from the 100-paper public robotics corpus, the eight-axis submanifold, ResearchStudio strategy cards, and the venue catalog. When only this Skill is installed, use this file and the `LOCAL_FALLBACK_NO_CORPUS` output from `scripts/route_robotics_research.py`; never claim that the corpus was loaded.

The standalone fallback may select E/P/C/L/D/H/A/S review questions and audit claims, mechanisms, conditions, contrasts, metrics, failure boundaries, and artifacts. It must not claim prior-work collision coverage, corpus support, or official venue compliance without the complete repository and fresh official sources. Preserve `NOT_ESTIMABLE`, `EVIDENCE_GAPS`, and `NOT_ASSESSABLE`.
