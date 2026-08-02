# Pause and resume / 暂停与恢复

## 中文

暂停先停止新 Agent，再进入 `PAUSING`，调用环境 stop，登记 PID/command/cwd/stdout/stderr，
校验 artifact hash，写 report/handoff，最后进入 `PAUSED` 或对应 awaiting state。恢复
只读取磁盘上的 config、events、state、task、approval、receipt、Git 状态、环境 receipt
和 process registry；删除 `state.json` 后必须由 events 重建相同缓存状态。stale PID、dirty
Git、task/environment drift 都阻断恢复。

# English

Pause starts by preventing new Agents, enters `PAUSING`, stops the environment, records
process metadata, verifies artifact hashes, writes report/handoff, and reaches `PAUSED` or
an awaiting state. Resume reads only disk artifacts: config, events, state, task,
approvals, receipts, Git state, environment receipt, and process registry. Deleting
`state.json` must allow identical reconstruction from events. Stale PIDs, dirty Git, and
task/environment drift block resume.
