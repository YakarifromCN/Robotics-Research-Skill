# Sibling Skill Invocation Adapter / 并列 Skill 调用适配器

## 中文

Adapter 发现四个科研 sibling 和可选 Engineering sibling 的入口、validator、模板和 native artifact，计算 hash，
生成 candidate manifest；只有用户确认 manifest hash 后才冻结。它准备 invocation
request（allowed files、prompt hash、stage、session），由当前 Agent runtime 实际
执行；Python 不伪造 Agent。

原生工件由 owner validator 校验，Adapter 只保存通用 `StagePackage` 和 `StageReceipt`。
缺少任一科研入口/validator 时只有 Robotics-AR 进入 `BLOCKED_DEPENDENCY`；缺少 Engineering
只写入 `optional_missing`，Robotics-AR 继续使用既有 Code/Test/Runner 路径。直接调用 sibling
不会创建 `.robotics-ar/`。Review 缺 fresh runtime 时只能显式手工导入或阻断。

Engineering invocation 继承已经批准的 Robotics-AR Task/Trial Contract、允许路径、预算和
安全限制，标记为 `AUTONOMOUS_WITHIN_APPROVED_TASK`。它不新增 plan 审批、人工代码审计或
stage approval，也不加入科研 sibling 的 `STAGE_STATES`；只有越出合同、需要新的真实设备
授权、触发安全停止或预算停止时才暂停。

# English

The adapter discovers four scientific siblings plus optional Engineering, including owner
validators, templates, and native artifacts. It hashes them, writes a candidate manifest, and freezes it only after user hash
confirmation. It prepares an invocation request with allowed files and prompt hash; the
actual runtime invokes the Skill. Python never fabricates an Agent. Owner validators
validate native artifacts, while the adapter stores only generic packages and receipts.
Missing scientific sibling files block Robotics-AR only. Missing Engineering is recorded as
`optional_missing` and falls back to Code/Test/Runner. Direct sibling use never initializes
`.robotics-ar/`. Review without a fresh runtime is manual-import or blocked.

Engineering invocations inherit the approved Robotics-AR Task/Trial Contract, paths, budget,
and safety limits. They run as `AUTONOMOUS_WITHIN_APPROVED_TASK` without another plan, code-audit,
or stage-approval checkpoint, and Engineering is not added to the scientific sibling
`STAGE_STATES`; only contract expansion, new device authority, safety stops, or budget stops
pause execution.
