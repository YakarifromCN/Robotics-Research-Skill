# Supervisor protocol / Supervisor 协议

## 中文

Supervisor 先验证 config、mode、interaction language、Git 和 sibling manifest，再
进入 `PLANNING_READY`。每个阶段都有 candidate → confirmed → invocation → owner
validation → receipt → user gate；批准只消费一次，subject hash 漂移自动失效。

Type-A gate 只判断机器可验证事实（命令退出、文件存在、预算计数）；Type-B gate
判断质量/正确性，必须由外部 fresh reviewer 或用户签署。Supervisor 可以驱动循环，
不能给自己的产物质量结论。状态转换来自静态表，未知转换拒绝。

# English

The Supervisor validates config, mode, language, Git, and the sibling manifest before
`PLANNING_READY`. Each stage follows candidate → confirmed → invocation → owner
validation → receipt → user gate; approvals are single-use and hash-bound.
Type-A gates cover mechanical facts, while Type-B quality/correctness gates require a
fresh external reviewer or human. The Supervisor may drive a loop but cannot acquit its
own artifacts. A static transition table rejects unknown transitions.
