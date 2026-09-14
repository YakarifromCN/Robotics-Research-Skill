# 基线复现

## 中文

先用 `baseline-compile` 固定代码、配置、环境、任务/数据身份、种子、预期指标、容差和工件，再用 `baseline-select --reason ...` 明确选择。相同选择可重复确认，配置变化需要新的明确决定；不能在复现前静默更换配置。

`baseline-run` 必须绑定已批准的 execution specification、输入摘要和有效 lease，详见 [执行回执](execution-receipts.md)。新项目可用 `baseline-bootstrap-new` 生成基线规格与选择绑定，但这不授予执行权限，也不产生实验结果。通用 baseline-run 不执行真实设备；真实设备使用既有一次性 token 路径。

每次失败保存独立 attempt receipt；连续恢复失败不会覆盖原始原因或触发非法自转移。`baseline-recover` 记录诊断，不能修改算法来制造复现。复现偏差需要用户决定，单次失败也不能被写成科学反证。成功复现后仍需完成对应批准，旧批准不继承到新结果。

修改未完成的选择时，在 `baseline-select` 额外传入绑定新规格的 BASELINE `--approval`；先关闭所有未完成的执行记录。旧选择被保留，新结果仍需重新批准。

# English

## Baseline reproduction

Use `baseline-compile` to fix code, configuration, environment, task/data identity, seeds, metrics, tolerances and artifacts, then `baseline-select --reason ...` to select explicitly. Reconfirming an identical selection is idempotent. Configuration changes require a new explicit decision.

`baseline-run` requires an approved execution specification, input digest and live lease; see [execution receipts](execution-receipts.md). `baseline-bootstrap-new` creates a new-project specification and selection binding without authorizing execution or producing results. Generic baseline-run does not operate physical hardware; use the established one-shot token path.

Each failed attempt retains its receipt. Repeated recovery failures preserve causes without an invalid self-transition. `baseline-recover` records diagnostics, not an algorithm change to manufacture reproduction. Variance requires a user decision; execution failure is not scientific falsification. New results require their own approval.

To amend an unfinished selection, pass a BASELINE approval bound to the new specification to baseline-select. Close outstanding executions first. The previous selection remains archived; new results need their own approval.
