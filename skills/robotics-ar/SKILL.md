---
name: robotics-ar
description: Supervise explicitly requested, resumable research sessions across the existing robotics research Skills with domain-neutral state, approval gates, evidence receipts, safe environment execution, isolated agent work, and pause/resume artifacts; use only when the user explicitly asks for Robotics-AR, autonomous research mode, a cross-stage loop, or online execution orchestration.
---

# Robotics-AR

## 概览

`robotics-ar` 是用户显式开启的编排 Skill。它管理一个可暂停、可恢复的
自动研究 session，保存通用状态、事件、预算、批准 hash、证据 receipt 和 handoff；
按用户目标调用现有的 Idea、Experiment、Writing 或 Review sibling Skill。
若独立可用的 `develop-robotics-engineering` 已被 manifest 确认，代码实现任务可以选择性
调用它；缺失时继续使用 Code/Test/Runner 协议，不阻断 Robotics-AR。
调用后继承已批准 Task/Trial Contract 并自主完成实现、测试与回执，不增加用户审计环节；
Engineering 不进入科研阶段审批状态机；只有合同越界、新设备权限、安全停止或预算停止才暂停。

直接请求某个科研阶段时，调用对应 sibling Skill；只有明确要求“自动模式”“自治
研究”“跨阶段循环”“暂停恢复”或“在线执行编排”时才触发本 Skill。

## 输入与模式

### 项目命名与目录

已有项目复用用户指定根目录，不改名、不另建同义项目。确需新建时，从上下文提炼
最简、可辨识的默认名称，先问用户“项目名用 `<建议名>` 可以吗？也可以指定其他名字。”，
确认前不创建目录；用户已明确给出的项目名或路径视为已选择，不重复询问。
新项目名不得以 `.` 开头或包含路径分隔符、`..`。

新会话使用 `<项目根>/robotics-ar/`；临时产物仅在需要时放入该项目的
`robotics-ar/tmp/<任务标识>/`，优先复用，否则不创建。所有执行 Agent 继承此约束：
未经用户明确授权，不得新建点号开头的目录（如 `.tmp`、`.worktrees`、`.robotics-ar`）
或项目外临时工作区。任务执行授权不等于隐藏目录授权；若工具需要，先说明并询问，
不得自行加授权参数。已有工具目录不搬迁、不删除。
旧 `.robotics-ar/` 会话原位兼容，不自动复制；新旧目录并存时阻断并要求核对。
本规则针对目录，不禁用已有 `.git` 或原子写入的短暂隐藏文件。

新文件先按当前项目已有功能分类归档，优先更新或合并同类文档，不按每次任务另建
目录或同义副本；不可合并覆盖原始证据、追加日志或冻结合同。
执行一次任务默认只在对话中说明结果，不生成报告、总结、交接、复盘等报告性质文件，
无论 Markdown、JSON 还是其他格式；只有用户明确要求才创建，并优先维护现有分类中的
单份文件。此约束也传给 sibling/执行 Agent，不因其模板要求自行生成一套报告。
必要的状态、合同、原始证据、测试回执仍保留，但不得把叙述报告改名为 receipt 绕过约束。
`--write-reports` 和 `--allow-hidden-directories` 只表达本次用户明确授权，不默认开启。

必须显式提供：项目根目录、交互语言、研究目标、所需 stage、`PLANNING_ONLY` 或
`EXECUTION_ENABLED`、约束/允许路径，以及 sibling Skill 根目录或已确认 manifest。

- `PLANNING_ONLY`：可形成假设、设计、导入已有 evidence、调用 sibling 和生成缺口
  报告；禁止 rollout、真实设备命令和把计划写成 evidence。
- `EXECUTION_ENABLED`：每个 batch 前必须有冻结的 `ONLINE_VERIFIED` environment
  receipt；没有 receipt 时停在 `BLOCKED_ENVIRONMENT`。

### v3 中途接入模式

显式指定 `entry_mode: MIDSTREAM_TAKEOVER` 或用户要求中途接入已有项目时，先执行
接管访谈、只读项目审计、历史实验重建、在线环境验证和 baseline reproduction。
只有 `Project Core`、`Reconstructed History`、`Reproduced Baseline` 与用户批准的
`Trial Contract` 同时存在，才允许自主 trial batch；否则保持在计划、等待审批或
阻断状态。

`NEW_RESEARCH` 保持 v2 生命周期。Takeover 可以从 Experiment 上下文衔接，但不是
第五个领域科研阶段；Idea 只在需要时以 `IDEA_RECONCILIATION` 调用，Writing 必须
等待 evidence freeze，Review 只生成 route proposal。

每次 checkpoint、暂停、阻断和用户纠正都会保存必要状态与证据；仅在用户要求报告时
更新 `robotics-ar/report.md`、`robotics-ar/handoff.md`，不按任务追加报告副本。
用户纠正只维护 `robotics-ar/tasks/task.md`，不再生成根目录副本。baseline 失败时只能使用
`baseline-recover --diagnostics` 记录恢复诊断，不能升级为可用 baseline；
`batch-resume` 会重验 contract、environment receipt/fingerprint、累计 wall-time
和 terminal stop reason。`trial-analyze` 要求 raw evidence 与 versioned metrics；
完成且有结论的 trial 进入 Do-Not-Repeat，单 seed 不能自动晋升为 stable Best-Known
State。成功 trial 的 code/test/run/analysis receipt 必须自哈希并互相绑定 proposal、
contract、code/configuration、environment receipt/fingerprint 与 metric versions；仅有
`status: PASS` 不能产生 `KEEP`，且 batch tier 必须是合同搜索空间的子集。

## 不可静默违反的规则

1. 只在显式 `$robotics-ar` 或等价明确请求后初始化 `robotics-ar/`。
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
python3 skills/robotics-ar/scripts/robotics_ar.py init --project-root <project-root> --entry-mode MIDSTREAM_TAKEOVER --mode EXECUTION_ENABLED
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-init --project-root <project-root>
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-status --project-root <project-root>
# After the user has approved the core, baseline, and contract:
python3 skills/robotics-ar/scripts/robotics_ar.py batch-start --project-root <project-root> --contract <approved-contract> --receipt <environment-receipt>
# A real-robot batch additionally requires a one-shot token and its exact binding.
python3 skills/robotics-ar/scripts/robotics_ar.py batch-start --project-root <project-root> --real-robot --real-robot-token <token.json> --real-robot-binding <binding.json> --contract <approved-contract> --receipt <environment-receipt>
```

命令 stdout 只输出一个 machine-readable JSON；人类说明写 stderr。验证/阻断返回稳定
非零码，支持 `--dry-run`，不交互式修改文件。

## Progressive disclosure

- 总体结构和状态：阅读 `references/architecture.md`、`neutral-kernel.md`。
- gate、批准、task 和恢复：阅读 `references/supervisor-protocol.md`、`pause-resume.md`。
- sibling 调用：阅读 `references/sibling-skill-adapter.md`。
- 环境与真实设备：阅读 `references/environment-contract.md`、`real-robot-gate.md`。
- Agent 隔离和 receipts：阅读 `references/execution-agents.md`。
- 执行预留、外部运行登记或未知运行恢复：按需阅读 `references/execution-receipts.md`。审计上限与 reconciliation 见 `references/project-audit.md`。

细节由 `scripts/robotics_ar_core/` 和 `schemas/` 的确定性实现承担；不要把本文件扩展
成第二套 Research Card、Experiment Contract、Claim Ledger 或 Meta Review。

## 阻断与停止

缺失 sibling 入口/validator、schema drift、dirty Git、环境未验证、越权写入、raw
篡改、预算耗尽、两次 debug 失败、Critical Block 或用户要求暂停，都必须保留机器恢复状态，
在对话中说明并停止；只有用户要求才生成 report/handoff。失败、负结果、abort、inconclusive 和
`NOT_APPLICABLE` 是一等结果，不能升级成成功。

v3 参考协议：`midstream-takeover.md`、`project-audit.md`、
`history-reconstruction.md`、`baseline-reproduction.md`、`trial-contract.md`、
`autonomous-trial-loop.md`、`human-reentry.md`、`dynamic-expert-deliberation.md`。
可复制的 intake、contract、report、handoff 和 task 起始工件位于 `assets/*.example.*`。

# English

## Overview

`robotics-ar` is the explicitly enabled orchestration sibling. It supervises a
resumable research session, stores neutral state/events/budgets/approval hashes,
and calls only the existing Idea, Experiment, Writing, or Review siblings that
the user's objective requires.
When an independently usable `develop-robotics-engineering` sibling is present and
confirmed, code tasks may invoke it; otherwise Code/Test/Runner remains available,
so Engineering is not a hard dependency.
The invocation inherits the approved Task/Trial Contract and autonomously implements,
tests, and receipts the change without another user-audit gate. Engineering does not enter
the scientific stage-approval state machine. Contract expansion, new device authority,
safety stops, and budget stops still pause execution.

Direct stage requests use the corresponding sibling. Trigger this Skill only for
an explicit Robotics-AR/automatic/autonomous/cross-stage/pause-resume/online-
execution request.

## Modes and hard boundaries

Reuse the user's existing project root without renaming or creating a parallel project.
For a new project, propose the shortest descriptive name derived from context and ask
the user to confirm or replace it before creating directories. An explicit name or path
already counts as a choice. New names must not start with a dot or contain separators or `..`.

New sessions use `<project-root>/robotics-ar/`. Put temporary artifacts only when needed
under `robotics-ar/tmp/<task-id>/` in that project; otherwise create nothing. Every execution
agent must not create dot-prefixed directories or external scratch workspaces without
explicit user authorization. Task authorization does not imply hidden-directory permission;
ask before using an exception flag. Preserve existing tool directories. Existing `.robotics-ar/` sessions remain in place; dual
old/new roots block for reconciliation. This is a directory rule, not a ban on existing
`.git` or transient atomic-write files.

Classify new files by the existing project structure; prefer updating or consolidating
same-purpose documents over per-task folders and duplicates. Never merge away raw evidence,
append-only logs, or frozen contracts. A normal task ends with a conversational result, not
report, summary, handoff, or retrospective files in any format. Create those only on explicit
user request, preferably updating one categorized file. Sibling templates do not override
this rule. Keep necessary state, contracts, raw evidence, and test receipts; do not relabel
narrative reports as receipts. `--write-reports` and `--allow-hidden-directories` express
explicit authorization for the current invocation only; neither is enabled by default.

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

The v3 CLI requires approved Project Core, reproduced baseline, online environment,
and Trial Contract bindings before a batch. Every batch checkpoint also carries the
environment receipt hash and fingerprint plus accumulated wall-time, and simulation
resume rejects terminal stop reasons. Every successful trial receipt is self-hashed and
cross-bound to its proposal, contract, code/configuration, environment, and metric
versions; a status-only PASS cannot yield KEEP, and batch tiers cannot exceed the
contract search space. Real-robot execution additionally needs an
operator-bound one-shot token; failure stops the batch and never retries it.
