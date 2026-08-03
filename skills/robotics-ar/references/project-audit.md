# 项目审计

审计是只读的。它记录 Git branch/HEAD/dirty 状态、worktree、文档中找到的命令、配置、
checkpoint、日志、结果、候选环境和冲突。审计不执行项目脚本，也不跟随项目根目录之外
的 symlink。每个恢复出的事实都带有来源和状态，例如 `DOCUMENTED`、`DETECTED`、
`EXECUTION_VERIFIED`、`CONTRADICTED` 或 `UNKNOWN`。

高优先级冲突会生成 discrepancy 工件，并要求进行 reconciliation。

# English

# Project Audit

Audit is read-only. It records Git branch/HEAD/dirty state, worktrees, commands found
in documentation, configs, checkpoints, logs, results, environment candidates, and
conflicts. It does not execute a project script and does not follow symlinks outside
the project root. Every recovered fact carries a source and a status such as
`DOCUMENTED`, `DETECTED`, `EXECUTION_VERIFIED`, `CONTRADICTED`, or `UNKNOWN`.

High-priority contradictions become a discrepancy artifact and require reconciliation.
