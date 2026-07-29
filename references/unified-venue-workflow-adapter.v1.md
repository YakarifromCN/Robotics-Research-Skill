# Unified venue-workflow adapter v1

这不是十套 venue-specific workflow，也不创建新的 `skills/<venue>/` 目录。
它把外部 workflow 中可复用的研究方法压缩为一个共享适配器，并让现有四个
robotics skill 用八条研究流形轴解释目标 venue 的证据形状。

## 统一方法

```text
研究流形轴解析
  -> 贡献中心 / 证据形状 / 失败边界
  -> Idea / Experiment / Writing / Review 四个 stage adapter
  -> 当前官方 venue scope、author guide 与投稿包装
```

第一步使用 `E/P/C/L/D/H/A/S` 的 0–3 语义向量，记录主轴、副轴、研究强度和
证据压力。第二步由主张、承重变量和 falsification target 冻结贡献中心、条件、
对照、指标、分析、失败日志和 artifact 义务。第三步只把可复用能力路由进四个
现有 skill；第四步才叠加需要新鲜核验的 venue 规则。

不变量：venue fit 不得改写 Claim Lock；venue 偏好不得事后改变 Design Lock、
实验单位、分母、排除或 abort policy；`INCONCLUSIVE`、`EVIDENCE_GAPS` 和
`NOT_SUPPORTED` 不得被包装、奖项、factor fit 或审稿分数升级；录用概率始终
为 `NOT_ESTIMABLE`。

## 模拟归纳后注入的运行时问题

模型子代理对 Stage-2 四字段做了模拟 embedding、分组和审计。该过程只用于把
重复出现的研究动作压缩成下面八个运行时问题；Skill 运行时不读取
`agent/internal/`，也不暴露模拟 cluster ID、簇数或噪声率：

1. 哪个 operating envelope、transfer 或 deployment 条件决定方法能否离开 nominal setup？
2. 哪个 dynamics、feedback 或 safety boundary 让闭环干预可检验？
3. 哪个 task、coordination 或 planning constraint 必须先分型和隔离？
4. 哪个 body、material、contact、morphology 或 interface 是具身主张的承重对象？
5. 哪个人、触觉、参与者或 operator measure 是交互主张的承重条件？
6. 哪个 data、representation、supervision 或 policy substrate 改变下游机器人行为？
7. 哪个 sensing-to-state 选择在排除混杂后改变下游决策？
8. 哪个 software/hardware timing 或 interface contract 决定系统能否部署？

这些问题是候选 workflow prompts，不是统计发现或八类固定 taxonomy。每个 Skill
只选择与活动轴、Claim Lock 和证据义务相符的问题，并把答案落入自己的原始合同。

## 统一学习到四个 skill 的核心能力

| Skill | 应学习的共同能力 | 不得推断 |
|---|---|---|
| `develop-robotics-idea` | 轴形状 → contribution family/center；做 audience 与 sibling collision audit；保持 Claim Lock 独立 | venue fit、奖项或计数不能证明质量、创新或录用 |
| `design-robotics-experiment` | 证据形状 → condition/contrast/metric/analysis/failure/artifact；冻结单位、分母和判定规则 | venue 偏好的 proof、simulation、video 或 spot-check 不能替代锁定证据 |
| `write-robotics-paper` | target-fit snapshot + Claim Ledger；按 claim → result → boundary → task meaning 组织叙事 | 不能为迎合 venue 添加未经证实的泛化、安全、实时或部署主张 |
| `review-robotic-feedback` | 由活动轴、贡献中心、证据形状和官方 scope 组装评审面板；保留 gap 与 disagreement | reviewer score、venue rank 或 factor fit 不能折叠成录用概率 |

## 外部 workflow 的统一映射

以下记录是能力来源和轴解释，不是十个内部 workflow。官方 scope、author guide、
周期、伦理、视频、rebuttal 和 artifact 规则均需在具体目标上重新核验；快照不足时
保持 `REFRESH_REQUIRED`。

| 外部 workflow | 主要轴形状 | 可复用的核心 gate | 四 skill 中的落点 |
|---|---|---|---|
| 通用 AI conference | L/P/D/S | contribution family、evidence shape、audience、sibling disambiguation | Idea 定贡献族；Experiment 定证据形状；Review 查 scope/fallback |
| 通用工程技术 journal | E/P/C/L/S | theory/method/system/device、proof/simulation/bench/field、generality、reproducibility | Idea 定贡献中心；Experiment 做匹配证据；Writing 做 archival framing |
| Science Robotics | E/P/A/H/S | broad significance、physical realism、repeatability、statistics、hardware | Experiment 冻结物理真实性与重复性；Writing 限定 broad claim |
| IJRR | E/P/C/L/D | conceptual framing、mechanism generality、cross-condition、complete validation | Idea 定概念框架；Experiment 做跨条件机制对照；Writing 承载深度 |
| T-RO | E/P/C/L/S | complete validated robotics、quantitative trials、baselines/ablations、failure boundary | Experiment 完整验证；Review 查可复现性与失败边界 |
| HRI | H/P/A | human subjects、interaction mechanism、ethics/IRB、study readiness | Experiment 冻结参与者单位与伦理；Review 查 study readiness |
| CoRL | L/P/C/S | learning core、seeds/splits/baselines、real-robot spot-check、limitations | Experiment 查 split/seed/real check；Review 查 artifact/limitations |
| RSS | E/P/C/D/S | single-track contribution、mechanism ablation、failure attribution、hardware campaign | Idea 收窄单一贡献；Experiment 做机制与失败归因；Review 查硬件证据 |
| IROS | E/P/C/A/S | integrated system、deployment boundary、failure/safety、artifact/video | Experiment 做系统集成与运行边界；Writing/Review 查视频和 artifact |
| ICRA | E/P/C/L/S | robotics relevance、mechanism/algorithm evidence、matched baselines、logged hardware campaign | 由轴形状反推贡献与证据，再叠加当前 ICRA 官方规则 |

## ICRA 轴形状逆推示例

对一个 `C=3, E=2, S=2, L=1` 的项目，适配器应先提出：

1. 贡献中心优先落在 control/dynamics mechanism，而不是“用了学习”这一标签；
2. 最小证据形状是承重方程/控制机制、matched controller baseline、扰动或接触边界、
   失败归因、频率/接口/硬件日志；
3. Idea 做机制 collision audit，Experiment 冻结条件/对照/单位/分母，Writing 用
   Claim Ledger 限定主张高度，Review 检查 C/S 轴的安全、实时和 artifact 缺口；
4. 只有在上述科学证据合同确定后，才刷新 ICRA 当前 scope、author guide、周期和
   supplementary 规则。

这一步是“轴形状解释 workflow”，不是从 ICRA 反推出录用率，也不是把所有 ICRA
论文视为同一向量。
