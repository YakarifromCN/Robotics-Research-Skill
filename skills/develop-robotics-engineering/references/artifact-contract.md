# Artifact contract

优先沿用项目已有正文风格，但四个工件都必须保留模板中的极小 YAML frontmatter，并使用同一 `task_id`、语言、轴和风险层级：

- `agent/plan/<slug>.md`：目标、现状、范围和验收；已有计划时只补理解摘要。
- `agent/task/<slug>.md`：允许/禁止修改、相关路径、3–7 步、0–3 个测试和停止条件。
- `agent/report/<slug>.md`：面向用户的结果、改动、测试、未做事项和限制。
- `agent/handoff/<slug>.md`：面向下一 Agent 的稳定状态、修改路径、精确恢复命令和风险。

Task 冻结用户需求、3–7 步、0–3 条原样命令、allowed/forbidden scope 与 stop conditions。用 `scripts/run_engineering_tests.py` 执行命令；Report 必须携带绑定 command/result/exit-code 的 receipt，changed files 必须落在 allowed paths；Handoff 与 Report 的状态、文件、receipts 和 Task hash 必须一致。`DONE`/`NO_CODE_CHANGE` 的 `resume_command` 为 `null`，`PARTIAL`/`BLOCKED` 必须非空。正文不得为空或只有占位符。完成前运行 `scripts/validate_engineering_artifacts.py`。

不要复制聊天、chain-of-thought、大段 diff 或日志。无代码改动时明确写 `NO_CODE_CHANGE`。简单任务仍保持文件短小；需要恢复信息时才扩展。

# English

Prefer the project's body style, but preserve the minimal YAML frontmatter in all four artifacts with one task ID, language, axes, and risk tier. Maintain one user-language file per task:

- `agent/plan/<slug>.md`: objective, current state, scope, and acceptance criteria.
- `agent/task/<slug>.md`: allowed/forbidden changes, relevant paths, 3–7 steps, 0–3 tests, and stop conditions.
- `agent/report/<slug>.md`: user-facing outcome, changed paths, tests, exclusions, and limitations.
- `agent/handoff/<slug>.md`: stable state, changed paths, exact resume command, remaining work, and risks.

Freeze 3-7 steps, 0-3 exact commands, and allowed paths in Task. Report the same commands and only allowed changed files. Keep Report and Handoff states/files identical. DONE/NO_CODE_CHANGE use a null resume command; PARTIAL/BLOCKED require one. Run `scripts/validate_engineering_artifacts.py`. Do not copy chat transcripts, private reasoning, large diffs, or logs.
