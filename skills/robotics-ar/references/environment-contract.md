# Environment contract / 环境协议

## 中文

Environment manifest 使用 argv arrays：capabilities、health_check、minimal_rollout、
collect_results、stop；所有路径必须 containment 于批准 root。Runner 使用 `shell=False`、
executable allowlist、精简环境变量、timeout 和 process group；stop 幂等且 timeout 后
不自动 retry。`ONLINE_VERIFIED` 必须通过 schema、adapter hash、capabilities、health、
minimal rollout、结果 finite 校验、artifact/log 存在和 stop 两次安全调用。

# English

The environment manifest contains argv arrays for capabilities, health, minimal rollout,
collection, and stop. CWD, requests, results, and artifacts are contained under the
approved root. The Runner uses `shell=False`, executable allowlists, sanitized variables,
timeouts, process groups, idempotent stop, finite-result checks, and no automatic retry.
`ONLINE_VERIFIED` requires schema, adapter hash, capabilities, health, minimal rollout,
finite results, artifacts/logs, and two safe stop calls.
