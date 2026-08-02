# Execution agents / 执行 Agent

## 中文

Code Agent 只能改 task 允许的实现路径；Test Agent 可运行独立测试；Environment Runner
只能运行已批准命令并创建 raw；Data Analyst 只能读取 raw、计算冻结指标和写 analysis
receipt；Dynamic Expert 只回答一个明确 unknown。每个角色都有 allowed paths，越界是
失败。同一工作树最多一个写 Agent；没有 fresh runtime 不生成独立 panel receipt。

# English

The Code Agent edits only task-approved implementation paths; the Test Agent runs tests;
the Environment Runner runs approved commands and creates raw data; the Data Analyst reads
raw and emits frozen-metric analysis receipts; a Dynamic Expert addresses one explicit
unknown. Allowed paths are enforced and violations fail. At most one writer touches a
worktree, and no fresh runtime means no fabricated independent panel receipt.
