---
name: robotics-ar
description: Supervise explicitly requested, resumable research sessions across the existing robotics research Skills with domain-neutral state, approval gates, evidence receipts, safe environment execution, isolated agent work, and pause/resume artifacts; use only when the user explicitly asks for Robotics-AR, autonomous research mode, a cross-stage loop, or online execution orchestration.
---

# Robotics-AR

## 概览

`robotics-ar` 是用户显式开启的第五个并列 Skill。它管理一个可暂停、可恢复的
自动研究 session，保存通用状态、事件、预算、批准 hash、证据 receipt 和 handoff；
按用户目标调用现有的 Idea、Experiment、Writing 或 Review sibling Skill。

直接请求某个科研阶段时，调用对应 sibling Skill；只有明确要求“自动模式”“自治
研究”“跨阶段循环”“暂停恢复”或“在线执行编排”时才触发本 Skill。

## 输入与模式

必须显式提供：项目根目录、交互语言、研究目标、所需 stage、`PLANNING_ONLY` 或
`EXECUTION_ENABLED`、约束/允许路径，以及 sibling Skill 根目录或已确认 manifest。

- `PLANNING_ONLY`：可形成假设、设计、导入已有 evidence、调用 sibling 和生成缺口
  报告；禁止 rollout、真实设备命令和把计划写成 evidence。
- `EXECUTION_ENABLED`：每个 batch 前必须有冻结的 `ONLINE_VERIFIED` environment
  receipt；没有 receipt 时停在 `BLOCKED_ENVIRONMENT`。

## 不可静默违反的规则

1. 只在显式 `$robotics-ar` 或等价明确请求后初始化 `.robotics-ar/`。
2. 其他四个 Skill 可独立发现、安装、调用和测试；它们不得导入、hook 或依赖本 Skill。
3. Core schema 只使用通用研究对象；领域内容放在 `domain_payload`。
4. `events.jsonl` 是 append-only source of record；`state.json` 只是可重建缓存。
5. 所有 JSON 使用 canonical bytes、有限数值、schema version 和 SHA-256。
6. 所有批准绑定 subject hash；漂移会使批准失效，single-use token 不可重放。
7. Python 只生成 invocation request、receipt 和验证结果；不得假装自行创建 Agent。
8. 无 fresh runtime 时披露 `SINGLE_AGENT_MODE`；独立 Review panel 只能
   `BLOCKED_DEPENDENCY` 或 `MANUAL_REVIEW_IMPORT`。
9. Environment command 必须是 argv array、`shell=False`、allowlist、path containment、
   sanitized environment、timeout、process group 和幂等 stop；禁止自动重试。
10. raw evidence 只能由 Environment Runner 创建；分析 Agent 只读并不能改 raw。
11. Writing 只能消费 `EVIDENCE_FREEZE` 后的证据；Review route 只生成新 task proposal，
    不自动补实验。
12. 真实设备只通过一次性 caution/token gate 进行静态测试；开发和 CI 不连接真实设备。

## 生命周期摘要

`UNINITIALIZED → BOOTSTRAP_VALIDATING → PLANNING_READY`；阶段调用进入对应
`INVOKING_*`/`AWAITING_*_APPROVAL`；任务经过 `TASK_COMPILATION → AWAITING_TASK_APPROVAL`；
执行经过 `EXECUTION_READY → RUNNING_ENVIRONMENT → ANALYZING → EVIDENCE_FREEZE`；写作和
评审经过 evidence/writing/review gate；任意 active state 可经 `PAUSING → PAUSED`，
恢复必须重建状态并再次检查 hash、预算、环境 fingerprint 和 token。

## CLI

从仓库根目录运行：

```bash
python3 skills/robotics-ar/scripts/robotics_ar.py discover --project-root <project-root> --robotics-research-root <robotics-research-root>
python3 skills/robotics-ar/scripts/robotics_ar.py init --project-root <project-root> --mode PLANNING_ONLY --interaction-language zh
python3 skills/robotics-ar/scripts/robotics_ar.py status --project-root <project-root>
python3 skills/robotics-ar/scripts/robotics_ar.py validate-siblings --project-root <project-root>
python3 skills/robotics-ar/scripts/robotics_ar.py pause --project-root <project-root> --reason user-request
```

命令 stdout 只输出一个 machine-readable JSON；人类说明写 stderr。验证/阻断返回稳定
非零码，支持 `--dry-run`，不交互式修改文件。

## Progressive disclosure

- 总体结构和状态：阅读 `references/architecture.md`、`neutral-kernel.md`。
- gate、批准、task 和恢复：阅读 `references/supervisor-protocol.md`、`pause-resume.md`。
- sibling 调用：阅读 `references/sibling-skill-adapter.md`。
- 环境与真实设备：阅读 `references/environment-contract.md`、`real-robot-gate.md`。
- Agent 隔离和 receipts：阅读 `references/execution-agents.md`。

细节由 `scripts/robotics_ar_core/` 和 `schemas/` 的确定性实现承担；不要把本文件扩展
成第二套 Research Card、Experiment Contract、Claim Ledger 或 Meta Review。

## 阻断与停止

缺失 sibling 入口/validator、schema drift、dirty Git、环境未验证、越权写入、raw
篡改、预算耗尽、两次 debug 失败、Critical Block 或用户要求暂停，都必须生成 report
和 handoff 并停止在可恢复状态。失败、负结果、abort、inconclusive 和
`NOT_APPLICABLE` 是一等结果，不能升级成成功。

# English

## Overview

`robotics-ar` is the explicitly enabled fifth sibling Skill. It supervises a
resumable research session, stores neutral state/events/budgets/approval hashes,
and calls only the existing Idea, Experiment, Writing, or Review siblings that
the user's objective requires.

Direct stage requests use the corresponding sibling. Trigger this Skill only for
an explicit Robotics-AR/automatic/autonomous/cross-stage/pause-resume/online-
execution request.

## Modes and hard boundaries

`PLANNING_ONLY` permits planning, evidence import, sibling calls, and gap reports
but no rollout or fabricated evidence. `EXECUTION_ENABLED` requires a frozen
`ONLINE_VERIFIED` environment receipt before every batch. Core objects are
domain-neutral; domain values live in `domain_payload`. Events are append-only,
state is reconstructible, JSON is canonical and finite, approvals bind hashes,
and one-shot tokens cannot replay.

The Python layer prepares requests and receipts; it never pretends to create an
Agent. Missing fresh runtime is disclosed as `SINGLE_AGENT_MODE`,
`BLOCKED_DEPENDENCY`, or `MANUAL_REVIEW_IMPORT`. Environment execution uses argv
arrays, `shell=False`, allowlists, containment, sanitized variables, timeout,
process groups, idempotent stop, finite-result validation, and no automatic
retry. Writing requires frozen evidence; Review routes create proposals only.

## CLI and references

Run `python3 skills/robotics-ar/scripts/robotics_ar.py <command> ...`. stdout is
one machine-readable JSON object, validation/blocking returns a stable non-zero
code, and side-effecting commands support `--dry-run`. Load the directly linked
reference files for architecture, kernel, supervisor, sibling adapter,
environment, execution agents, or pause/resume details. Never duplicate a
sibling's scientific contract inside this Skill.
