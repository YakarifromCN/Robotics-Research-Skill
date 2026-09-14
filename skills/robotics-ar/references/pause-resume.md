# 暂停与恢复

## 中文

暂停通过 `PAUSING` 停止已登记进程，写 report/handoff，再进入 `PAUSED`。恢复前检查冻结任务、批准、环境、预算和设备 token。终态 `COMPLETE`、`TAKEOVER_COMPLETE`、`ABORTED` 的 resume 不创建新工作。

事件追加和 CLI 写操作使用同机协作锁。状态转移先提交包含投影的事件，再写缓存；中断的投影可以在重新加载时恢复。旧写者遇到状态变化必须重新加载，不能覆盖新状态。共享盘的跨主机锁语义未由单机测试证明。

默认恢复要求 Git 干净。多仓库或非 Git 项目可使用 `snapshot-repositories --input <spec.json>` 记录已授权文件清单；spec 包含 `authorization` 与 `roots`，每个 root 记录 `id`、`path`、`files`，非 Git 根还需 `kind: directory`。内容与 HEAD 漂移、未纳入清单的 Git 脏文件或越界链接会阻断恢复。快照只能反映明确列出的非 Git 文件，不证明整个目录未变化。

`doctor` 诊断状态与关键工件；`migrate-v2` 仅迁移已知版本，先保留内容寻址的备份。不要重排损坏的事件或手工把状态改为成功。外部执行恢复见 [执行回执](execution-receipts.md)。

# English

## Pause and resume

Pause enters `PAUSING`, stops registered processes, writes report/handoff and reaches `PAUSED`. Resume validates frozen tasks, approvals, environment, budgets and device tokens. Resume in `COMPLETE`, `TAKEOVER_COMPLETE` or `ABORTED` creates no new work.

Event append and CLI mutations use a local cooperative lock. Transitions commit a projection-bearing event before updating the state cache, allowing interrupted projections to recover on reload. Stale writers must reload rather than overwrite newer state. Single-host tests do not establish cross-host shared-filesystem semantics.

Resume requires clean Git state by default. `snapshot-repositories --input <spec.json>` records an authorized file list for multiple repositories or non-Git roots. The spec contains `authorization` and `roots`; each root provides `id`, `path`, `files`, and `kind: directory` for a non-Git root. Content or HEAD drift, unlisted dirty Git files and escaping links block resume. A non-Git snapshot covers only its explicit files.

`doctor` diagnoses state and key artifacts. `migrate-v2` handles known versions and preserves a content-addressed backup. Do not reorder damaged events or manually mark state successful. See [execution receipts](execution-receipts.md) for external execution recovery.
