---
name: design-robotics-experiment
description: 面向机器人科研的实验设计、审计、微调与结果封装 Skill；将锁定主张变成可执行条件、结构化判定规则、长格式测量和三态证据结论。
---
# 机器人实验 / Robotics Experiment

## 边界

读取 Research Card 的 ID 与 `claim_digest`，不复制投稿适配信息，不静默改变 Claim Lock。先读 `references/core-contract.md`；按 `domain_packs` 读取仓库级 `references/packs/*.md`。

## 模式

`PROSPECTIVE_DESIGN`、`PILOT_AMENDMENT`、`RETROSPECTIVE_AUDIT`、`MICRO_ADJUSTMENT`、`PACKAGE_EXISTING_RESULTS`。同时记录 `design_timing`；回顾性合同不得称为预注册。

## 工作流

1. 把每项证据义务映射为 condition、contrast、metric、analysis。
2. 冻结 Design Lock：实验单位层级、条件、主指标、排除、分母、abort policy、判定规则。
3. 用稳定 ID 连接变量、条件、指标和负对照。负对照签名可为回归基线、反向效应、选择性通道损失、边界移动、零效应或替代机制签名。
4. Operational Mutable 可在记录版本与原因后细化：校准、人员、日志位置、实测频率、更严格安全控制；不得据结果修改 Design Lock。
5. 每次尝试写入 Trial Registry；所有通道/窗口/阶段测量写入 Measurement Log。参与者、示范、session 等层级不得摊平成独立样本。
6. 内置规则由验证器机械求值；复杂分析绑定脚本与输出摘要。结果只能是 `SUPPORTED`、`NOT_SUPPORTED`、`INCONCLUSIVE`。
7. 安全事件、失败试验与 protocol deviation 不得因排除而消失。

## 命令

```bash
python3 skills/design-robotics-experiment/scripts/validate_experiment_contract.py experiment-contract.json --card research-card.json --ready
python3 skills/design-robotics-experiment/scripts/summarize_trials.py trial-registry.csv measurement-log.csv --abort-policy count_as_failure
python3 skills/design-robotics-experiment/scripts/validate_result_bundle.py result-bundle.json experiment-contract.json --ready
```

若合同不可执行输出 `NO_RUN`；若所需变化触及 Claim Lock，输出 `CHANGE_REQUEST_TO_IDEA`。

---

# English

Convert a locked claim into executable evidence. Freeze unit hierarchy, conditions, metrics, denominators, exclusions, and structured decision rules before observing outcomes. Keep operational refinements versioned but mutable. Record every attempt and derive the three-state verdict mechanically.
读取 Research Card 的 ID 与 `claim_digest`，不复制投稿适配信息，不静默改变 Claim Lock。先读 `references/core-contract.md`；按 `domain_packs` 读取仓库级 `references/packs/*.md`。
