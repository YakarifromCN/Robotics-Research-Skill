---
name: develop-robotics-idea
description: 面向机器人科研的证据驱动 Idea Skill；用于形成、审计、接纳或迁移可证伪研究主张，并建立 Claim Lock、机制反证和停止条件。适用于具身系统、控制、学习、仿生、软体、人机、工业、现场与多机器人研究。
---
# 机器人 Idea / Robotics Idea

## 边界

只负责 Idea 与科学合同，不设计完整实验，不写论文，不用投稿目标替代科学判断。先读 `references/core-contract.md`；仅在 `domain_packs` 激活时读取仓库级 `references/packs/*.md`。需要构思战术时读 `references/robotics-pattern-cards.md`。

## 模式

- `EXPLORE_NEW`：从开放问题生成候选。
- `AUDIT_EXISTING_IDEA`：只审计已有 Idea。
- `ADOPT_LOCKED_IDEA`：接受用户冻结的 Idea，记录不可改边界。
- `MIGRATE_LEGACY_PROJECT`：把既有材料迁移为合同；不得把事后整理描述成预注册。

## 工作流

1. 明确任务、系统边界、承重变量、核心主张和明确不声称什么。
2. 检索最近邻、奠基工作、失败边界与并行路线；保留查询、截止日期和来源。若被近期先例覆盖且没有实质差异，输出 `ABANDON`。
3. 填写七维 `claim_shape`，直接声明 `evidence_obligations`；不得从分数、载体名称或静态映射派生义务。
4. 建立非序数 evidence requirement：分别约束 regime、coverage、duration、independence、experimental unit 与数量。
5. 设计机制级决定性反证；同容量负对照不得只是同义改名。
6. 先写 `candidate.json` 并冻结摘要，再写 `audit.json`；`revision-patch.json` 只能改 audit 明确授权的路径。核心主张、机制或反证目标变化时生成新 candidate。
7. 生成 Research Card，计算 `claim_digest`，运行验证器。

## 硬规则

- Claim Lock：task、system boundary、core claim、mechanism、load-bearing variable、falsification target、claim boundary。
- 资源、安全和伦理约束必须真实；无法安全运行时输出 `DO_NOT_GENERATE`。
- `diagnostic_dashboard` 仅供人阅读，不路由、不锁定。
- 投稿适配另存 `target-fit-snapshot.json`，不得进入 Claim Lock。
- `REVISE` 可以结构有效但不可交接；只有 `READY` 且 `--ready` 通过才可进入实验。

## 工件与命令

使用 `assets/` 中 V2 模板。验证：

```bash
python3 skills/develop-robotics-idea/scripts/validate_research_card.py research-card.json --ready
```

输出必须是 `READY`、`REVISE`、`DO_NOT_GENERATE` 或 `ABANDON` 之一。

---

# English

Build or audit falsifiable robotics ideas. Keep venue adaptation outside the scientific lock; express evidence needs component-wise; preserve immutable candidate→audit→patch boundaries; load only activated domain packs. Use the V2 assets and validator above. Only `READY` may hand off; stopping states are first-class outputs.
