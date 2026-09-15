# Execution agents / 执行 Agent

## 中文

Code Agent 只能改 task 允许的实现路径；Test Agent 可运行独立测试；Environment Runner
只能运行已批准命令并创建 raw；Data Analyst 只能读取 raw、计算冻结指标和写 analysis
receipt；Dynamic Expert 只回答一个明确 unknown。每个角色都有 allowed paths，越界是
失败。同一工作树最多一个写 Agent；没有 fresh runtime 不生成独立 panel receipt。

交接 brief 必须指定同一项目根：未经用户明确授权，不得新建隐藏目录或项目外临时工作区；必要临时产物
归入 `robotics-ar/tmp/<任务标识>/`，无需求就不创建。不得自行命名新项目；Supervisor
应先根据上下文提出最简默认名并向用户确认，已有项目直接复用。
新文件按项目已有分类优先合并；默认不生成任务报告、总结或交接文件，用户明确要求才生成。
保留必要机器状态和真实证据回执，不能将报告改名绕过规则。

# English

The Code Agent edits only task-approved implementation paths; the Test Agent runs tests;
the Environment Runner runs approved commands and creates raw data; the Data Analyst reads
raw and emits frozen-metric analysis receipts; a Dynamic Expert addresses one explicit
unknown. Allowed paths are enforced and violations fail. At most one writer touches a
worktree, and no fresh runtime means no fabricated independent panel receipt.

Every brief carries the same project root: no new hidden directories or external scratch
workspaces. Put necessary temporary artifacts in `robotics-ar/tmp/<task-id>/`; otherwise
create nothing. The supervisor asks the user to confirm a minimal context-derived name
before creating a new project; existing projects are reused without renaming.
Only explicit user authorization permits a hidden-directory exception. Consolidate files by
the existing project categories. Do not create task reports, summaries, or handoffs unless
requested. Preserve necessary machine state and genuine evidence receipts; never relabel reports.
