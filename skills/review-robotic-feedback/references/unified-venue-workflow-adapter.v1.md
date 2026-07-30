# 统一载体工作流适配器（审稿降级参考） / Unified venue-workflow fallback for review

目标会议或期刊只改变当前官方范围、作者指南、伦理、视频、rebuttal、artifact 和格式的检查语境，不改变 Claim Lock、Design Lock 或证据状态。完整仓库可读取根目录的统一适配器；独立安装只能使用下面的通用问题：

1. 贡献中心是否与任务和机器人承重机制一致？
2. 证据是否覆盖条件、对照、失败边界和可复现工件？
3. 目标载体的官方要求是否有来源 ID、检查日期和有效期？
4. 缺少官方来源时是否输出 `VENUE_EVIDENCE_GAP` 而不是推断违规？

不要按会议/期刊名称给固定分数，不要把载体偏好转成科学强度，也不要把评审分数转换为录用概率。

# English

Target information changes only the review context for current scope, author instructions, ethics, video, rebuttal, artifact, and format rules. It never changes Claim Lock, Design Lock, or evidence state. A standalone installation uses the following generic checks when the full adapter is unavailable: contribution center versus task and load-bearing mechanism; coverage of conditions, contrasts, failures, and reproducible artifacts; official source ID/date/expiry; and `VENUE_EVIDENCE_GAP` when official evidence is missing. Do not assign fixed scores by venue name or convert reviewer scores into acceptance probability.
