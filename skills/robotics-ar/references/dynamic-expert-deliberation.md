# 动态专家审议

专家 panel 由 Robot-Research-Skill 基础设施根据当前机器人问题动态生成，不是硬编码的
委员会。每名专家只回答一个明确未知量，最多进行两轮，并返回 `ACCEPT`、
`ACCEPT_WITH_CONSTRAINTS`、`REQUEST_DISCRIMINATIVE_EXPERIMENT` 或 `CRITICAL_BLOCK`。

未解决的 Critical Block 不得进入下一个 trial。分歧必须通过一个最小判别实验或用户
决定解决，不能通过无限讨论解决。

# English

# Dynamic Expert Deliberation

The panel is generated from the active robotics problem by the Robot-Research-Skill
infrastructure; it is not a hard-coded committee. Experts answer one explicit unknown,
run at most two rounds, and return `ACCEPT`, `ACCEPT_WITH_CONSTRAINTS`,
`REQUEST_DISCRIMINATIVE_EXPERIMENT`, or `CRITICAL_BLOCK`.

No unresolved Critical Block may enter the next trial. Disagreement is resolved by one
minimal discriminative experiment or a user decision, never by unlimited debate.
