# 机器人研究子流形基础设施 / Robotics Research Submanifold Infrastructure

本仓库把用户提供的会议与期刊集合蒸馏成一套透明的、可复核的机器人研究子流形，而不是把 venue 名称当成静态等级表。

## 八个子流形轴

| 轴 | 名称 | 核心问题 |
|---|---|---|
| `E` | 具身形态与接触 | 身体、材料、形态、接触或机电结构是否承重？ |
| `P` | 感知与状态估计 | 世界、机器人状态、接触或人的状态如何被感知和表示？ |
| `C` | 控制、动力学与安全 | 动力学、稳定性、控制、优化或安全性质是什么？ |
| `L` | 学习、表示与适应 | 学习、策略、表示、基础模型或适应是否承重？ |
| `D` | 规划、决策与协同 | 规划、推理、调度、长程任务或多智能体协同是否承重？ |
| `H` | 人机交互、触觉与 XR | 人因、交互机制、触觉通道、遥操作或 XR 是否承重？ |
| `A` | 自主系统与部署运行 | 导航、自主运行、工业/现场/无人系统运行包络是否承重？ |
| `S` | 系统集成、实时与基础设施 | 硬件软件接口、时序、嵌入式、通信、传感基础设施或产物是否承重？ |

模型文件为 [corpus/robotics-submanifold.v1.json](../corpus/robotics-submanifold.v1.json)。它公开每个轴的语义、指示标签、0–3 聚合规则和证据压力，不隐藏在不可解释的总分中。

## 如何使用

1. 从 Research Card、用户给出的 `topic_tags`、`claim_shape`、`domain_packs` 和明确的 `contribution_center` 提取项目向量。
2. 对 catalog 中的每个会议/期刊计算 venue 向量；所有条目都必须能落到至少一个子流形轴。
3. 逐轴比较项目需求与 venue 支持，记录 `supported`、`partial`、`venue_gap`，再用直接机器人/强相关的优先权重形成候选顺序。
4. 将活跃轴映射为“建议核查的证据压力”；这些只是候选义务，必须由研究者明确写入 Experiment Contract，不能静默修改 Claim Lock 或 Design Lock。
5. 对指定 venue 的投稿规则仍建立独立的 target-fit snapshot，并用当前官方来源刷新；子流形模型不能替代投稿政策核验。

## 子流形与四个原子 Skill

- Idea：用项目向量锁定主张所处的研究区域，提出最近邻、机制反证和证据压力；不让 venue 名称改变主张。
- Experiment：把活跃轴的压力翻译为条件、对照、指标、边界、独立单位和产物要求，并保留 `INCONCLUSIVE`。
- Writing：用轴向量检查论文是否把机制、系统、泛化、交互或部署语言写到了证据之外；venue 只改变包装。
- Review：按论文真实轴选择审阅重点，并将 venue 适配检查与科学合同审查分开。

“直接机器人”与“强相关”只用于候选优先级：直接机器人 venue 的优先权重为 `1.0`，强相关 venue 为 `0.65`。这不是录用概率，也不是跨学科总排名。真实投稿决定仍需要论文内容、证据状态和实时官方政策。

## 命令

```bash
python3 scripts/analyze_robotics_submanifold.py project-profile.json --output submanifold-analysis.json
```

输入也可以是 V2 `research-card.json`。建议在 profile 中额外提供：

```json
{
  "contribution_center": "robotics_core",
  "topic_tags": ["manipulation", "learning", "perception"],
  "target_kind": "journal"
}
```

如有可靠的人工判断，可以提供 `submanifold_axes` 覆盖派生值；覆盖必须记录在输出中并接受人工审计。
