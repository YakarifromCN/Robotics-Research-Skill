# Architecture / 架构

## 中文

Robotics-AR 由四层组成：Neutral Kernel 保存通用研究对象；Supervisor 负责状态、
预算、批准和恢复；Sibling Adapter 只适配现有 Skill 的入口/validator/原生工件；
Environment/Execution 层负责批准后的可审计执行。依赖方向唯一为
`robotics-ar → sibling skills`。

每个项目只在项目根写入 `.robotics-ar/`。Supervisor 独占 state、events、pointers、
charter、task、report 和 handoff；Agent 使用按 task 分配的目录；Environment Runner
创建 raw。所有跨层交接通过通用 envelope、receipt、hash 和 handoff status，不复制
任何 sibling 科学合同。

# English

Robotics-AR has four layers: a neutral Kernel, a Supervisor, a Sibling Adapter, and
Environment/Execution. The only dependency direction is
`robotics-ar → sibling skills`. A project writes only its own `.robotics-ar/` tree.
Supervisor-owned state and append-only events are separated from agent workspaces and
environment-created raw data. Cross-layer handoff uses generic envelopes, receipts,
hashes, and handoff status; sibling scientific contracts are never duplicated.
