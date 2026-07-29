# 机器人研究子流形路由契约

这是本仓库四个原子 Skill 共用的机器人专家层。它使用 `corpus/robotics-submanifold.v1.json` 的八条语义轴、`corpus/venue-catalog.v2.json` 的 114 个 venue 和 `corpus/robotics-submanifold-calibration.v1.json` 的均衡语料校准报告。

## 八条轴

| 轴 | 含义 | 典型证据压力 |
|---|---|---|
| E | 具身形态与接触 | 机构/材料/接触机制、制造边界、接触失败 |
| P | 感知与状态估计 | 标定、held-out 条件、不确定性、失败日志 |
| C | 控制、动力学与安全 | 稳定性、动力学假设、扰动/恢复、安全边界 |
| L | 学习、表示与适应 | 数据 lineage、split、seed、checkpoint、迁移边界 |
| D | 规划、决策与协同 | 规划对照、长时域任务、协同规模、失败类型 |
| H | 人机交互、触觉与 XR | 参与者/操作者单位、协议、效应量、伦理、工作负荷 |
| A | 自主系统与部署运行 | 运行包络、持续时间、跨环境/站点、恢复与失效 |
| S | 系统集成、实时与基础设施 | 接口、频率、版本、资源、硬件—软件组合、artifact |

向量取值为 0–3：0 未激活，1 局部相关，2 实质相关，3 主轴。它是可解释的语义因子编码，不是 PCA、统计因子分析、领域流行度估计或录用概率模型。

## 运行时流程

1. 从 `topic_tags`、`claim_shape`、`domain_packs` 和 `contribution_center` 派生项目向量；用户明确给出的轴值可以覆盖派生值，但必须记录来源。
2. 依据活动轴和最大载荷生成 `research_intensity` 与 `proposed_evidence_pressures`。它们只提出研究强度和证据审计问题，不得静默修改 Claim Lock 或 Design Lock。
3. 用 `venue-catalog.v2.json` 的 `topic_tags`、`contribution_gate` 和 `layer` 计算 venue 向量。`direct_robotics` 权重 1.0，`robotics_strong_related` 权重 0.65；这只是“机器人直接性”先验，不是评级或质量排序。
4. 若用户指定 venue，输出该 venue 的逐轴关系、缺口和条件适配；若未指定，输出 factor-fit ranking。正式投稿前必须另建并刷新官方范围/作者指南/周期/伦理/视频/artifact 的 `target-fit-snapshot`。
5. 对“录用概率”请求只输出 `NOT_ESTIMABLE`，并给出可计算的 factor-fit、证据完整度和官方范围核验状态；不得把向量排名伪装成概率。

## 四个原子 Skill 的重定向

- Idea：先编码主轴和副轴，提出主张高度与最小证据候选，再冻结 Claim Lock；venue 不得反向改写科学主张。
- Experiment：把活动轴的证据压力转成 condition/contrast/metric/analysis、单位层级、失败与安全规则；以真实证据决定 `SUPPORTED`。
- Writing：在 Claim Ledger 中为承重句绑定轴、结果、引文、图表和证据状态；按指定 venue 的官方范围压缩叙事，不抬高主张。
- Review：按活动轴组装评审面板；结合官方范围检查 desk-fit、证据形状、artifact 和补充材料；评分不折叠成录用概率。

## 外部 workflow 的能力映射

CS/AI router 的贡献族、受众、证据形状、周期和 sibling 消歧进入 Idea/Experiment/Review；工程期刊 router 的 theory/method/system/device 与 proof/simulation/bench/field 进入 Experiment/Writing；Science Robotics、IJRR、T-RO、HRI、CoRL、RSS、IROS 和 ICRA 的范围与流程约束进入 `references/venue-skill-routing.md` 的 venue gates。外部仓库的名称不作为本 Skill 的目录层级。
