# 执行登记与边界

## 中文

本接口管理执行记录，不代替环境运行器。每个新执行先准备 JSON specification：

```json
{
  "execution_id": "EX-001",
  "task_id": "TASK-001",
  "design_timing": "prospective",
  "operation": "run-batch",
  "input_sha256": "<canonical request digest>",
  "environment_fingerprint": "<verified fingerprint>",
  "costs": {"batches": 1, "trials": 1}
}
```

占位摘要必须替换为真实值。用户批准该文件的 TASK、EXPERIMENT 或 BASELINE gate 后，调用 `reserve-execution --input <spec.json> --approval <approval.json>`。预算按预留值保守记入共享已消费计数，失败后不自动退还。返回的 lease token 有效期为一小时；超过时间不自动续租或重跑。

内部 `run-batch`、`baseline-run` 接收 `--execution-id` 和 `--lease-token`，验证 operation、输入和环境绑定后自行写启动记录。外部运行器先调用 `start-execution`，完成后用 `register-external-execution --input <result.json>`，并提供同一 ID/token。结果含 execution_id 与 PASS/FAIL；同一结果重复提交不重复接纳，不同结果冲突。传入的结果仍需独立科学分析，登记不证明真实性。

`import-execution` 仅导入回顾性结果，不消费或补造事前批准。`parent_execution_id` 可记录父执行，但不会自动创建私有项目的多层结构。CLI 账本避免重复接纳，无法保证外部副作用 exactly-once。

崩溃留下 PREPARING、过期 lease 或未知运行状态时，先核对外部进程。用 `reconcile-execution` 提交经 TASK gate 批准的 resolution：包含 execution_id、previous_sha256、external_process_stopped=true、项目内 evidence_ref 和 evidence_sha256。接口保留未知证据状态并关闭该执行，不退款、不把结果升级为成功。证据必须实际证明进程已停止，不能仅为通过校验填写断言。

可选 `--invocation-receipt` 只记录本地 CLI 入口和结果标签，不上传数据，也不能证明语言模型读取了哪份 Skill。相关单机回归不代表跨主机、共享盘或真实设备资格认证。

结果可附带 `actual_costs`。系统保留预留扣账，并仅追加超过预留的实际用量；幂等标记阻止中断后重复扣账。实际用量超过预算会阻止后续预留。缺少计量时明确标为 `USAGE_UNVERIFIED`，不能宣称资源已经核算完成。

# English

## Execution registration and boundaries

This interface records executions; it does not replace an environment runner. Prepare a prospective JSON specification containing execution_id, task_id, operation, canonical input digest, verified environment fingerprint and explicit resource costs, as illustrated above.

Replace placeholders with real digests. After the user approves that file through a TASK, EXPERIMENT or BASELINE gate, call `reserve-execution --input <spec.json> --approval <approval.json>`. Reservations are conservatively charged to shared consumption and are not automatically refunded after failure. Lease tokens expire after one hour; expiration does not authorize renewal or relaunch.

Internal `run-batch` and `baseline-run` accept the execution ID and lease token, validate bindings, and record launch themselves. External runners call `start-execution`, then `register-external-execution --input <result.json>` with the same ID/token. Results carry execution_id and PASS/FAIL. Identical completion is idempotent; conflicting completion is rejected. Registration does not establish scientific validity.

`import-execution` imports retrospective evidence without inventing prior approval. Optional parent_execution_id links a parent without imposing a project-specific hierarchy. Ledger idempotency is not exactly-once external execution.

For PREPARING, expired leases or unknown runs, inspect the external process first. `reconcile-execution` accepts a TASK-approved resolution binding execution_id, previous_sha256, external_process_stopped=true, a project-contained evidence_ref and its digest. It closes the execution while preserving unverified evidence and spent budget. The evidence must actually establish that the process stopped; filling in a boolean is insufficient.

Optional `--invocation-receipt` records local CLI metadata without uploads. It cannot establish which Skill a language model read. Single-host regressions do not qualify remote hosts, shared filesystems or real devices.

Results may include actual_costs. Settlement retains the reservation charge and adds only measured excess, with an idempotency marker against interrupted double charging. Measured overruns block further reservations. Missing measurements remain USAGE_UNVERIFIED rather than being presented as reconciled accounting.
