# Real-device one-shot gate / 真实设备一次性门

## 中文

真实设备只生成 caution document 和 one-shot token；token 绑定 task、environment、
adapter、limits、batch 和 operator presence 的 hash。任何参数漂移、token 已消费、
operator 缺失、stop 失败或 retry 尝试都拒绝。失败后固定为 STOP → SAVE RECEIPT →
PAUSE → REPORT → USER DECISION。CI 永不连接真实设备。

# English

Real-device support creates only a caution document and a one-shot token. The token binds
task, environment, adapter, limits, batch, and operator-presence hashes. Drift, replay,
missing operator, failed stop, or retry attempts are rejected. Failure follows STOP → SAVE
RECEIPT → PAUSE → REPORT → USER DECISION. CI never connects to a real device.
