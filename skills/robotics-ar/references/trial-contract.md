# 试错合同

合同绑定 Project Core、baseline、环境、搜索 tier、允许和禁止的路径、指标、预算、报告、
停止条件、升级条件以及真实机器人权限。每个 trial 之前都会检查合同的 SHA-256。对方法、
声明、指标、数据协议或安全限制的 Tier 3 修改必须升级给用户。

amendment 要逐字保留用户指令、引用父合同 hash，并在新合同确认前使旧批准失效。
生产 takeover 合同还可以绑定实际的 Project Core、baseline、environment 工件和已消费
的上游 approval receipt；任一上游工件重编译或漂移都会清除旧批准。

# English

# Trial Contract

The contract binds Project Core, baseline, environment, search tiers, allowed and
forbidden paths, metrics, budgets, reporting, stop conditions, escalation conditions,
and real-robot permissions. Its SHA-256 is checked before every trial. Tier 3 changes
to method, claim, metric, data protocol, or safety limits always escalate to the user.

An amendment preserves the user instruction verbatim, references the parent hash, and
invalidates the old approval until the new contract is confirmed. A production takeover
contract may additionally bind the concrete Project Core, baseline, environment, and
consumed upstream approval receipts; recompilation or drift of any upstream artifact
clears the old approval.
