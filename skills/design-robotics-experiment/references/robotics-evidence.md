# 中文版

## 机器人证据模型

证据必须匹配主张高度。先使用真正能证伪主张的最低阶梯，仅在主张需要时再增加更高阶梯。

自适应强度调节互补条件、边界、复现及产物深度的数量。维护证据预算，并将项目标记为 `required` 或 `deferred`。每个延期项目都要说明延期原因，以及哪些确切措辞/泛化不再得到支持。

不得把自然科学期刊层级整体移植到机器人研究。当材料/制造差异是承重因素时，材料批次是必需项；人类主张必须进行参与者抽样；两者都不是所有机器人算法的通用要求。由主张决定的机器人证据和自适应强度起支配作用。只有安全、诚实、预先声明的标准、公平比较及可审计日志是通用底线。

### 证据阶梯

正文标签为 `L0` 到 `L6`；JSON Contract 和 Result Bundle 将阶梯编码为 0 到 6 的整数，使交接只有一种无歧义类型。

| 阶梯 | 证据 | 可以支持 | 不能单独支持 |
|---|---|---|---|
| `L0` | 推导、静态分析或组件健全性检查 | 内部一致性 | 任务性能或物理鲁棒性 |
| `L1` | 受控仿真或台架测试 | 建模/隔离条件下的机制 | 物理泛化或现场可靠性 |
| `L2` | 集成仿真或硬件在环 | 已声明模型/接口下的系统交互 | 未建模的真实世界接触及材料效应 |
| `L3` | 受控实机试验 | 有边界运行包络内的具身性能 | 广泛部署或群体主张 |
| `L4` | 留出、压力、跨环境或跨平台试验 | 泛化及边界行为 | 持续运营价值 |
| `L5` | 长时现场/部署研究 | 实践影响、恢复、干预、可靠性 | 观测包络之外的普适行为 |
| `L6` | 独立复现或多站点证据 | 可迁移性及异常广泛的影响 | 超出复现条件的主张 |

每条 `C###` 主张指定其最低阶梯。如果收集的证据止于更低阶梯，即使观测指标有利，判定也为 `INCONCLUSIVE`。

### 通用设计义务

#### 单位与分母

定义实验单位是 trial、task instance、object、route、participant、robot、fabrication batch、day 还是 site。在一个对象上重复尝试不是独立的对象层级证据。报告每个成功率背后的分母。

#### 任务分布

规定总体、抽样/生成器、纳入边界及留出维度。区分插值、组合和外推。记录任务 ID 或确定性生成器版本。

#### 基线公平性

匹配主张所保持不变的因素：硬件、传感、观测、控制频率、算力、训练/评估数据、任务实例、复位及调参预算。记录例外。不同硬件或任务分布下的已发表数值只是语境，不是受控比较。

#### 对照与负对照

- 组件消融检验该组件是否重要；
- 机制干预检验其是否出于拟议原因而起作用；
- 负对照改变机制，同时预测一个独立下游指标；
- 正对照验证设备能够揭示已知效应；
- 匹配比较对象隔离形态、材料、信息或集成主张。

#### 不确定性与小样本

预定义估计目标及不确定性单位。只对尝试层级主张使用尝试层级区间。当对象、参与者、批次、机器人、日期或站点是独立单位时，在相应层级聚类或汇总。报告效应量和不确定性，而非仅报告显著性。解释缺失和多重性。

#### 失败

使用稳定类别：`perception`、`estimation`、`planning`、`control`、`contact`、`material`、`hardware`、`integration`、`operator`、`safety` 和 `unknown`。原始错误文本单独保存。区分任务失败、中止、安全停止、硬件故障及排除。

### modifier 条件化证据

#### Learning-centric

记录数据集谱系及许可证、训练/验证/测试划分 ID、留出因素、训练与评估种子、检查点选择、算力、超参数搜索预算、学习组件与工程组件之间的明确边界，以及物理策略是否冻结。在共享结果上量化 sim-to-real，或声明不作迁移主张并限定结论边界。

把训练随机性和执行随机性视为不同层次。声称 sim-to-real 差距时，在两个域中评估同一冻结检查点，除非主张明确涉及适应；披露每次更新。

#### Morphology-dependent

对拟议形态进行干预，并隔离其机械或控制后果。当比较性语言是承重因素时，使用匹配的形态比较对象。在主张所需范围内匹配质量、尺寸、驱动/传感、能量及控制能力。形态依赖性本身不能确立生物启发性。

#### Bioinspired

将生物学原理及其经验证的来源证据与形态分开列明。检验该原理向机器人机制的所声称迁移。仅当优越性、必要性或解释性语言使其成为承重因素时，才使用匹配的非生物比较对象。绝不能从 `morphology-dependent` 自动推断 `bioinspired`。

#### Soft-body

根据实际主张及继承强度选择材料配方/批次、制造方差、迟滞、疲劳/耐久性、环境依赖性、机制消融及比较对象证据。对每项已选择义务记录 `reported`、`justified_not_applicable` 或 `deferred`；延期义务必须缩小主张。只有当比较性语言使其成为承重因素时，才要求匹配的刚体比较对象。把永久变形和破裂视为结果，而非清理噪声。

#### Industrial integration

根据实际工业主张及继承证据形状，选择组件/接口版本、时序/抖动、周期时间、吞吐量、质量/可靠性、故障/恢复及长时证据。对每项已选择义务记录 `reported`、`justified_not_applicable` 或 `deferred`，并附理由及主张边界。主张为端到端时必须检验端到端行为；不得把长时生产研究强加给有边界的接口机制主张。

#### Human interaction

记录适用的监督状态及依据、同意或豁免、群体/招募、交互任务、人层级统计单位、风险、隐私、操作员培训及停止规则。人机交互主张并不自动属于临床或医疗。

#### Clinical medical

记录临床治理与批准、同意、群体、招募、纳入/排除、临床终点、风险、隐私、不良事件与停止规则、操作员培训及人层级统计单位。批准待定时不得开始受治理的数据采集。

#### Field practice

定义站点与运行包络、持续时间与占空比、干预分类、恢复时间、正常运行时间/吞吐量/质量或从业者结果、反事实/比较对象，以及另一操作员复现工作流所需的产物。

#### Distributed multi-robot

记录团队规模范围、拓扑与角色、通信预算与故障模型、协调指标、机器人/链路故障条件、争用及扩展行为。区分由更多机器人带来的改进与由更多传感、算力、带宽或尝试带来的改进。

#### Cross-disciplinary impact

使用至少两个面向同一主张的独立证据流，例如分析模型加材料表征再加机器人任务研究。预定义证据流不一致时的处理方式。在两个数据集上重复同一指标并不构成收敛。

### T 轴证据

当 `T >= 3` 时，列出假设及其中可检验的假设。把每个主要命题/机制关联到预测、可识别对照及边界/反例测试。区分定理正确性与经验有用性。此义务来自流形轴，而非 modifier。

### 流形分数义务

对于每个满足 `max(current score, inherited axis floor) >= 3` 的轴，在 Contract 中指定证据：

- `E`：相关硬件或有边界的无硬件主张；
- `M`：机制对照/消融；
- `S`：接口、时序、交互及恢复测试；
- `V`：预定义试验、不确定性、失败及协议纪律；
- `G`：留出/压力/边界评估；
- `A`：可重跑或可审计产物清单；
- `P`：由工业、现场或临床契约承载的运行包络、干预/恢复及利益相关者结果；它不会强制 `field-practice`；
- `T`：假设、因果对照及边界测试。

如实分类复现：`rerunnable`（相同日志/配置可重新生成结果）、`re-collectable`（另一个团队可收集新试验）、`auditable`（可检查受限产物）或 `testimonial`（仅有描述）。在采集时捕获日志；事后叙述不能替代。不存在通用的种子数、试验数、平台数或实机配方——主张高度、独立单位及自适应强度共同决定它们。

---

# English Version

## Robotics evidence model

Evidence must match claim altitude. Use the lowest rung that can actually falsify the claim, then add higher rungs only when the claim needs them.

Adaptive intensity scales the number of complementary conditions, boundaries, replications, and artifact depth. Keep an evidence budget with items marked `required` or `deferred`. Every deferred item states why it is deferred and exactly which wording/generalization is no longer supported.

Do not transfer a natural-science journal hierarchy wholesale into robotics. Material batches are mandatory when material/fabrication variation is load-bearing; participant sampling is mandatory for human claims; neither becomes a universal requirement for every robot algorithm. Claim-dependent robotics evidence and adaptive intensity govern. Only safety, honesty, predeclared criteria, fair comparison, and auditable logging are universal floors.

### Evidence ladder

The prose labels are `L0` through `L6`; JSON contracts and Result Bundles encode the rung as the integer `0` through `6` so the handoff has one unambiguous type.

| Rung | Evidence | Can support | Cannot alone support |
|---|---|---|---|
| `L0` | derivation, static analysis, or component sanity check | internal consistency | task performance or physical robustness |
| `L1` | controlled simulation or bench test | mechanism under modeled/isolated conditions | physical generalization or field reliability |
| `L2` | integrated simulation or hardware-in-the-loop | system interaction under a declared model/interface | unmodeled real-world contact and material effects |
| `L3` | controlled real-robot trials | embodied performance in a bounded operating envelope | broad deployment or population claims |
| `L4` | held-out, stress, cross-environment, or cross-platform trials | generalization and boundary behavior | sustained operational value |
| `L5` | long-run field/deployment study | practice impact, recovery, intervention, reliability | universal behavior outside the observed envelope |
| `L6` | independent replication or multi-site evidence | transferability and unusually broad impact | claims beyond the replicated conditions |

Each `C###` claim names its minimum rung. If the collected evidence stops below it, the verdict is `INCONCLUSIVE`, even when the observed metric is favorable.

### Common design obligations

#### Units and denominators

Define whether the experimental unit is a trial, task instance, object, route, participant, robot, fabrication batch, day, or site. Repeated attempts on one object are not independent object-level evidence. Report the denominator behind every success rate.

#### Task distributions

Specify population, sampling/generator, inclusion boundaries, and held-out dimensions. Separate interpolation, composition, and extrapolation. Record task IDs or deterministic generator versions.

#### Baseline fairness

Match what the claim holds constant: hardware, sensing, observations, control frequency, compute, training/evaluation data, task instances, resets, and tuning budget. Record exceptions. Published numbers from different hardware or task distributions are context, not a controlled comparison.

#### Controls and negative controls

- component ablation asks whether the component matters;
- mechanism intervention asks whether it works for the proposed reason;
- negative control changes the mechanism while predicting an independent downstream metric;
- positive control verifies the apparatus can reveal a known effect;
- matched comparator isolates morphology, material, information, or integration claims.

#### Uncertainty and small samples

Predefine the estimand and uncertainty unit. Use attempt-level intervals only for attempt-level claims. Cluster or summarize at object, participant, batch, robot, day, or site level when those are the independent units. Report effect sizes and uncertainty, not only significance. Explain missingness and multiplicity.

#### Failures

Use stable categories: `perception`, `estimation`, `planning`, `control`, `contact`, `material`, `hardware`, `integration`, `operator`, `safety`, and `unknown`. Keep raw error text separately. Distinguish task failure, abort, safety stop, hardware fault, and exclusion.

### Modifier-conditioned evidence

#### Learning-centric

Record dataset lineage and license, train/validation/test split IDs, held-out factors, training and evaluation seeds, checkpoint selection, compute, hyperparameter search budget, the explicit boundary between learned and engineered components, and whether the physical policy was frozen. Quantify sim-to-real on a shared outcome, or state that no transfer claim is made and bound the conclusion.

Treat training randomness and execution randomness as separate layers. When claiming a sim-to-real gap, evaluate the same frozen checkpoint in both domains unless the claim explicitly concerns adaptation; disclose every update.

#### Morphology-dependent

Intervene on the proposed morphology and isolate its mechanical or control consequence. Use a matched morphology comparator when comparative language is load-bearing. Match mass, size, actuation/sensing, energy, and control capacity as far as the claim requires. Morphology dependence does not by itself establish biological inspiration.

#### Bioinspired

Name the biological principle and its verified source evidence separately from morphology. Test the claimed transfer of that principle to the robot mechanism. Use a matched non-biological comparator only when superiority, necessity, or explanatory language makes it load-bearing. Never infer `bioinspired` automatically from `morphology-dependent`.

#### Soft-body

Select material formulation/lot, fabrication variance, hysteresis, fatigue/durability, environment dependence, mechanism ablation, and comparator evidence according to the actual claim and inherited intensity. For every selected obligation record `reported`, `justified_not_applicable`, or `deferred`; a deferred obligation must narrow the claim. A matched rigid comparator is required only when comparative language makes it load-bearing. Treat permanent deformation and rupture as outcomes, not cleanup noise.

#### Industrial integration

Select component/interface versions, timing/jitter, cycle time, throughput, quality/reliability, fault/recovery, and long-run evidence according to the actual industrial claim and inherited evidence shape. Record each selected obligation as `reported`, `justified_not_applicable`, or `deferred` with its rationale and claim boundary. Test end-to-end behavior whenever the claim is end-to-end; do not force a long-run production study onto a bounded interface-mechanism claim.

#### Human-interaction

Record the applicable oversight status and basis, consent or waiver, population/recruitment, interaction task, human-level statistical unit, risk, privacy, operator training, and stopping rules. A human-interaction claim is not automatically clinical or medical.

#### Clinical-medical

Record clinical governance and approval, consent, population, recruitment, inclusion/exclusion, clinical endpoints, risk, privacy, adverse-event and stopping rules, operator training, and human-level statistical unit. Do not begin governed data collection while approval is pending.

#### Field-practice

Define site and operating envelope, duration and duty cycle, intervention taxonomy, recovery time, uptime/throughput/quality or practitioner outcome, counterfactual/comparator, and artifact needed for another operator to reproduce the workflow.

#### Distributed-multi-robot

Record team-size range, topology and roles, communication budget and failure model, coordination metrics, robot/link failure conditions, contention, and scaling behavior. Separate improvement caused by more robots from improvement caused by more sensing, compute, bandwidth, or attempts.

#### Cross-disciplinary impact

Use at least two independent evidence streams—for example analytical model plus material characterization plus robot task study—aimed at the same claim. Predefine what happens when the streams disagree. Mere repetition of one metric on two datasets is not convergence.

### T-axis evidence

When `T >= 3`, list assumptions and which are testable. Tie each main proposition/mechanism to a prediction, an identifiable contrast, and a boundary/counterexample test. Separate theorem correctness from empirical usefulness. This obligation comes from the manifold axis, not a modifier.

### Manifold score obligations

For every axis with `max(current score, inherited axis floor) >= 3`, name evidence in the contract:

- `E`: relevant hardware or a bounded no-hardware claim;
- `M`: mechanism control/ablation;
- `S`: interface, timing, interaction, and recovery tests;
- `V`: predefined trials, uncertainty, failures, and protocol discipline;
- `G`: held-out/stress/boundary evaluation;
- `A`: rerunnable or auditable artifact manifest;
- `P`: operating envelope, interventions/recovery, and stakeholder outcome carried by an industrial, field, or clinical contract; it does not force `field-practice`;
- `T`: assumptions, causal contrast, and boundary test.

Classify reproduction honestly: `rerunnable` (same logs/configs can regenerate results), `re-collectable` (another team can collect new trials), `auditable` (restricted artifacts can be inspected), or `testimonial` (description only). Capture collection-time logs; a post hoc narrative is not a substitute. There are no universal seed, trial-count, platform-count, or real-robot recipes—claim altitude, the independent unit, and adaptive intensity determine them.
