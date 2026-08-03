# 自主试错循环

每个 trial 都遵循“假设 → 专家检查 → 合同检查 → 最小补丁 → 独立测试 → 在线运行 →
原始证据 → 分析 → 有界专家解释 → Supervisor 决策”。决策只能是 `KEEP`、`REVERT`、
`INVESTIGATE` 或 `ESCALATE`。

同一时间只能有一个写代码的 trial。原始证据冻结后不可修改。batch 在预算耗尽、环境
失败、没有信息增益、出现关键阻塞、用户暂停，或需要修改 Project Core/Trial Contract
时停止。成功的 code/test/run/analysis receipt 必须有自哈希，并绑定 proposal、contract、
代码版本、配置、环境 receipt/fingerprint 和 metric version；每个 trial 开始前重新验证
环境 receipt，只有 status receipt 不能产生 KEEP。

# English

# Autonomous Trial Loop

Each trial follows hypothesis → expert check → contract check → minimal patch →
independent test → online run → raw evidence → analysis → bounded expert interpretation
→ Supervisor decision. Decisions are `KEEP`, `REVERT`, `INVESTIGATE`, or `ESCALATE`.

Only one code-writing trial is active. Raw evidence is immutable after freeze. A batch
stops on budget, environment failures, no information gain, critical block, user
pause, or any required contract/core change. Successful code/test/run/analysis receipts
are self-hashed and cross-bound to the proposal, contract, code/configuration,
environment receipt/fingerprint, and metric versions; the environment is revalidated
before every trial, so a status-only receipt cannot yield KEEP.
