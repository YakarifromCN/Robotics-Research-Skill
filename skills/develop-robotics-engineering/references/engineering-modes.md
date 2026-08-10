# 工程路由与专家合同

机器人轴描述“改动影响哪个子系统”，开发模式描述“如何实现和测试”；二者不得混用。

## 机器人轴

| 轴 | 子系统 | 必查不变量 |
|---|---|---|
| E | 具身、形态、接触 | model/frame/joint/contact |
| P | 感知、估计 | replay/shape/timestamp/calibration |
| C | 控制、动力学、安全 | finite output/limit/sign/stability fallback |
| L | 学习、表示、适应 | schema/shape/checkpoint/train-infer split |
| D | 规划、决策、状态机 | legal/unreachable transition/recovery |
| H | 交互、遥操作、触觉 | mapping scale/frame/disconnect fallback |
| A | 自主运行、部署 | lifecycle/start-stop/recovery/logging |
| S | ROS、实时、系统集成 | build/interface/TF/timing/transport |

## 开发模式

| 模式 | 最小实现与测试合同 |
|---|---|
| `CONTROL_LOOP` | 冻结 rate、frame、sign、limits；replay/sim 与边界输出 |
| `CONVEX_OPTIMIZER` | 冻结变量、维度、约束；feasible + infeasible，检查 status/residual |
| `ML_DATA_PIPELINE` | schema/version/hash；known sample 与坏输入 |
| `ML_TRAINING` | one-batch forward/backward、seed、checkpoint |
| `MODEL_DEPLOYMENT` | load/inference、device/dtype/shape、fallback |
| `ROS_NODE` | build、node/launch smoke、topic/service/action schema |
| `ROS_REALTIME_INTERFACE` | control rate、deadline、queue/lock、timeout/watchdog |
| `EMBEDDED_FIRMWARE` | compile/static pin-voltage-timing；未授权不 flash/erase |
| `SENSOR_DRIVER` | calibration、timestamp、frame、disconnect/corrupt packet |
| `SIMULATOR_EXTENSION` | asset/reset/control/record-replay，最小场景 |
| `HARDWARE_INTERFACE` | unit/limit/calibration/watchdog；offline mock 优先 |
| `STATE_MACHINE` | normal、illegal、unreachable、recovery path |
| `SYSTEM_TUNING` | 一次一组参数，固定其余项，记录 before/after |
| `BUILD_TOOLING` | deterministic build/config/path 与失败退出码 |

常见组合：C+S+`ROS_REALTIME_INTERFACE`；C+`CONVEX_OPTIMIZER`；L+S+`MODEL_DEPLOYMENT`；E+S+`HARDWARE_INTERFACE`；H+C+S+`CONTROL_LOOP`。

## 动态组合轴专家

- T0/T1 或单文件局部改动：不创建专家。
- T2 且至少两个轴：创建一个组合轴专家。
- T3：创建一个组合轴专家，并强制给出安全边界。

专家只读取 Task、直接调用路径、接口定义和已有测试，只输出：

```yaml
affected_call_path: []
critical_interfaces: []
invariants: []
smallest_change_locus: []
mandatory_safeguards: []
minimal_tests: []
blockers: []
```

禁止专家输出新科研 Idea、架构重写、新 benchmark、多方案 brainstorming 或扩大用户目标。主实现 Agent 必须逐项继承 safeguards 和 tests；不得让专家与实现 Agent 同时写文件。

# English

Axes identify the affected robotics subsystem; development modes define implementation and test behavior. Use no expert for T0/T1 or a local single-file fix, one bounded expert for multi-axis T2, and one safety-focused expert for T3. The expert emits only call path, invariants, smallest change locus, safeguards, minimal tests, and stop-worthy unknowns; it never writes code or expands scope.
