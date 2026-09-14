# 项目审计

## 中文

审计只发现和比较项目材料，不执行项目代码。默认最多访问 1000 个目录项、检查 8 MB 的候选内容，并给目录扫描 5 秒预算。单个候选文本超过 1 MB 时不读取正文。Git 与进程元数据命令另有 5 秒和 64 KiB 输出上限；扫描预算不代表整个审计的总时限。

CLI 可用 `--audit-max-files`、`--audit-max-bytes`、`--audit-max-seconds`、`--audit-include` 和 `--audit-exclude` 缩小范围。默认读取元数据和有限的声明文本，不对所有文件计算哈希。扫描不跟随符号链接，并跳过运行状态目录和常见缓存。

达到扫描上限返回 `PARTIAL`，receipt 记录覆盖范围并要求核对；未发现冲突不能证明未检查部分没有冲突。CLI 输出摘要和工件位置。审计 receipt 与事件绑定后，历史导入不得撤销 reconciliation 要求；用 `takeover-reconcile --input <resolution.json>` 记录明确处理结果。

# English

## Project audit

Audit discovers and compares project material without executing project code. Defaults cap discovery at 1000 directory entries, candidate content at 8 MB, and directory scanning at 5 seconds. Candidate text above 1 MB is not read. Git and process metadata commands have separate 5-second and 64 KiB output limits; the scan budget is not a whole-audit deadline.

Use `--audit-max-files`, `--audit-max-bytes`, `--audit-max-seconds`, `--audit-include` and `--audit-exclude` to narrow scope. Metadata and bounded declarations are inspected without hashing every file. Symlinks are not followed; runtime-state directories and common caches are skipped.

Reaching a scan limit yields `PARTIAL` with coverage recorded in the receipt. An absence of detected conflicts says nothing about unchecked material. The CLI returns a summary and artifact locations. History import cannot cancel a bound reconciliation requirement; record its resolution with `takeover-reconcile --input <resolution.json>`.
