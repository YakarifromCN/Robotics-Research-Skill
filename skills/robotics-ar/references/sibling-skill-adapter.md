# Sibling Skill Invocation Adapter / 并列 Skill 调用适配器

## 中文

Adapter 发现四个 sibling 的入口、validator、模板和 native artifact，计算 hash，
生成 candidate manifest；只有用户确认 manifest hash 后才冻结。它准备 invocation
request（allowed files、prompt hash、stage、session），由当前 Agent runtime 实际
执行；Python 不伪造 Agent。

原生工件由 owner validator 校验，Adapter 只保存通用 `StagePackage` 和 `StageReceipt`。
缺少入口/validator 时只有 Robotics-AR 进入 `BLOCKED_DEPENDENCY`；直接调用 sibling
不会创建 `.robotics-ar/`。Review 缺 fresh runtime 时只能显式手工导入或阻断。

# English

The adapter discovers sibling entry points, owner validators, templates, and native
artifacts, hashes them, writes a candidate manifest, and freezes it only after user hash
confirmation. It prepares an invocation request with allowed files and prompt hash; the
actual runtime invokes the Skill. Python never fabricates an Agent. Owner validators
validate native artifacts, while the adapter stores only generic packages and receipts.
Missing sibling files block Robotics-AR only; direct sibling use never initializes
`.robotics-ar/`. Review without a fresh runtime is manual-import or blocked.
