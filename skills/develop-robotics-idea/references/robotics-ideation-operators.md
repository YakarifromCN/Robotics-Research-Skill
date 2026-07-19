# 中文版

## 面向机器人研究的 ResearchStudio 构想算子

这 15 个算子改编自 ResearchStudio-Idea 的 IdeaSpark 词汇。它们是施加于已检索机器人瓶颈的结构性问题，不是填空配方、主题标签、刊物画像或构想将被录用的证据。上游来源与许可证记录于 [researchstudio-fusion.md](researchstudio-fusion.md)。

选择前阅读每一行。只有在证据包与瓶颈形成后，才能选择一个主算子和至多两个辅助算子。

| ID | 结构变换 | 机器人实例化问题 | 常见误用 |
| --- | --- | --- | --- |
| `assumption_audit_and_pivot` | 暴露承重假设，再放松或违反它 | 哪种准静态、刚体、已知接触、已校准传感器、平稳性或完美重置假设在机器人上失效？什么机制能在失效后继续工作？ | 只是罗列局限 |
| `architectural_operator_substitution` | 替换昂贵算子或表示，同时保留关键性质 | 能否替换传感器、估计器、规划器、控制器、通信步骤或材料组件，而不丢失所需物理性质？ | 没有保真论证的廉价实现 |
| `generative_process_redesign` | 把惯常固定的阶段变成设计变量 | 能否重新设计轨迹端点、重置策略、形态调度、任务生成器、制造参数或仿真到现实课程？ | 任意超参数调整 |
| `controlled_diagnostic_design` | 从混杂中隔离隐藏性质 | 能否使用匹配物体、接触、动力学、材料、用户或任务实例，把机制与数据、硬件、算力或操作技能区分开？ | 没有混杂假设的基准构建 |
| `unify_into_shared_representation` | 把异构输入或任务映射至同一底座 | 视觉、触觉、本体感觉、力、几何或异构机器人任务能否共享具有物理意义的状态/动作表示？ | 没有统一不变量就拼接模态 |
| `reframe_as_solvable_object` | 把瓶颈重述为可处理的数学对象 | 接触、分配、规划、校准或设计问题是否等价于成熟的优化、博弈、图、估计或约束问题？ | 改名却没有获得新工具 |
| `self_supervised_signal_engineering` | 从系统行为导出监督 | 接触事件、一致性、不确定性、能量、运动学闭合、成功轨迹或机器人干预能否提供原本不可得的标签？ | 未分析失败就信任噪声伪标签 |
| `structural_prior_encoding` | 通过构造强制已知结构 | 能否把对称性、等变性、守恒、运动学、拓扑、无源性、柔顺性或形态嵌入表示或控制？ | 添加软惩罚却声称保证 |
| `algebraic_equivalence_unification` | 证明不同程序等价 | 多个控制器、估计器、目标函数或校准阶段是否属于同一形式，从而可统一分析或折叠？ | 没有推导的视觉相似性 |
| `heterogeneous_decomposition` | 按区分性属性划分组件 | 接触模式、误差源、地形、材料区域、关节、任务或不确定性类型是否应接受不同处理？ | 没有操作后果的任意分类 |
| `decompose_and_delegate` | 把子问题路由给合适求解器 | 哪些部分属于学习、模型控制、优化、验证、人类或专用硬件？什么结构化接口把它们连接起来？ | 没有接口契约的大杂烩模块 |
| `relax_discrete_search_to_continuous` | 使结构搜索可微或摊销 | 能否优化形态、抓取、接触序列、任务分配、硬件布局或控制器结构，而不执行穷尽嵌套搜索？ | 舍入后设计无效或不安全的松弛 |
| `adapt_via_conditioning` | 通过上下文或目标输入适应，而非重新训练 | 机器人能否借助演示、检索、目标参数或在线上下文适应物体、用户、任务、动力学或形态？ | 把在线训练藏在“条件化”中 |
| `characterize_limit_then_surpass` | 形式化方法族的极限，再超越它 | 哪种可观测性、可控性、表达力、可达性、带宽、刚度或样本效率边界阻碍当前方法族？什么增量能跨越它？ | 只报告平台期而无极限论证 |
| `targeted_self_supervised_objective` | 将一种结构性质设为无标签学习目标 | 目标能否专门编码接触状态、可供性、形变、滑移、动力学、安全裕度或形态，而不是通用不变性？ | 给通用对比学习换名字 |

### 选择协议

对每个算子用一句话回答：“若忠实应用，该变换如何闭合已引用的瓶颈？”若它只能装饰构想，标记为 `no_fit`。按以下顺序对可行算子排序：

1. 直接闭合锚定瓶颈；
2. 与具身和系统接口兼容；
3. 能产生已命名机制与证伪变量；
4. 与最近工作存在实质差异；
5. 在给定资源与安全包络内可行。

不得使用 ResearchStudio 原始模式计数、录用/拒稿率或饱和区间排序。它们来自不同语料，不是机器人研究先验。

### 机制实例化契约

只有当候选说明以下内容时，才算真正执行了算子：

- 变换前状态与结构变换；
- 被改变的物理/软件对象；
- 该改变通过什么接口传导至机器人行为；
- 一个已命名的承重变量；
- 下游预测与匹配负对照；
- 最近工作差异。

变量示例包括：在控制使用时的估计器数据龄期、接触模式后验熵、单次冲击注入能量、任务方向有效刚度、闭环相位裕度、形变状态误差、周期时间尾延迟或操作员干预率。“更好的表示”和“具身智能”只是主题，不是变量。

### 组合纪律

使用一个主算子。只有当辅助算子闭合另一个必要子缺口时才添加。每增加一个算子都会引入一个接口和一种替代解释；两者都要记录。一张研究卡最多使用三个算子。

拒绝大杂烩组合、循环依赖，以及删除组件后主张仍不改变的机制。如果每个组件为何必要都由一条因果链解释，多组件系统仍然可以是简单的。

### 仅用于审计的失败检查

不要在无约束生成期间加载以下检查。候选形成后再使用：

- **假设审计 + 辅助信号：** 新信号是否真正解决被违反的假设，还是只与成功相关？
- **假设审计 + 结构先验：** 所声称不变量在正在研究的精确物理违例下是否成立？
- **假设审计 + 算子替换：** 替代项是否保留了在转向后变成承重因素的性质？
- **分解：** 划分能否在运行时识别？差异化处理是否胜过匹配的统一替代？
- **委派：** 中间产物是否类型明确、带时序且可审计，并具备故障恢复？
- **松弛：** 连续解能否映射至可行的离散/硬件设计而不抹去收益？
- **仿生或软体机制：** 形态/材料是否在因果上与控制器容量、制造质量和总能量隔离？
- **学习机制：** 数据、算力、随机种子与仿真器差异是否受控？

审计发现只产生具名、有边界的补丁。不得静默替换核心主张、最小证伪测试、承重变量或算力预算。

---

# English Version

## ResearchStudio ideation operators for robotics

These 15 operators are adapted from ResearchStudio-Idea's IdeaSpark vocabulary. They are structural questions to apply to a retrieved robotics bottleneck. They are not fill-in-the-blank recipes, topic labels, venue profiles, or evidence that an idea will be accepted. Upstream source and license are recorded in [researchstudio-fusion.md](researchstudio-fusion.md).

Read every row before choosing. Select one primary operator and at most two supporting operators only after the evidence bundle and bottleneck exist.

| ID | Structural move | Robotics instantiation question | Common misuse |
| --- | --- | --- | --- |
| `assumption_audit_and_pivot` | expose a load-bearing assumption, then relax or violate it | Which quasi-static, rigid-body, known-contact, calibrated-sensor, stationarity or perfect-reset assumption fails on the robot, and what mechanism survives? | merely listing limitations |
| `architectural_operator_substitution` | replace a costly operator or representation while preserving what matters | Can a sensor, estimator, planner, controller, communication step or material component be replaced without losing the required physical property? | cheaper implementation with no preservation argument |
| `generative_process_redesign` | turn a conventionally fixed stage into a design variable | Can trajectory endpoints, reset policy, morphology schedule, task generator, fabrication parameter or sim-to-real curriculum be redesigned? | arbitrary hyperparameter tuning |
| `controlled_diagnostic_design` | isolate a hidden property from confounds | Can matched objects, contacts, dynamics, materials, users or task instances separate mechanism from data, hardware, compute or operator skill? | benchmark creation without a confound hypothesis |
| `unify_into_shared_representation` | map heterogeneous inputs or tasks into one substrate | Can vision, touch, proprioception, force, geometry or heterogeneous robot tasks share a physically meaningful state/action representation? | concatenating modalities without a unifying invariant |
| `reframe_as_solvable_object` | recast the bottleneck as a tractable mathematical object | Is the contact, allocation, planning, calibration or design problem equivalent to a mature optimization, game, graph, estimation or constraint problem? | renaming the problem without gaining machinery |
| `self_supervised_signal_engineering` | derive supervision from system behavior | Can contact events, consistency, uncertainty, energy, kinematic closure, success traces or robot interventions provide labels that are otherwise unavailable? | trusting noisy pseudo-labels without failure analysis |
| `structural_prior_encoding` | enforce known structure by construction | Can symmetry, equivariance, conservation, kinematics, topology, passivity, compliance or morphology be embedded into representation or control? | adding a soft penalty and claiming a guarantee |
| `algebraic_equivalence_unification` | prove distinct procedures are equivalent | Are multiple controllers, estimators, objectives or calibration stages instances of one form that can be analyzed or collapsed? | visual similarity without derivation |
| `heterogeneous_decomposition` | partition components by a discriminating property | Should contact modes, error sources, terrain, material regions, joints, tasks or uncertainty types receive different treatments? | arbitrary taxonomy with no operational consequence |
| `decompose_and_delegate` | route subproblems to appropriate solvers | Which pieces belong to learning, model-based control, optimization, verification, humans or specialized hardware, and what structured interface joins them? | kitchen-sink modules with no interface contract |
| `relax_discrete_search_to_continuous` | make structural search differentiable or amortized | Can morphology, grasp, contact sequence, task allocation, hardware layout or controller structure be optimized without exhaustive nested search? | relaxation whose rounded design is invalid or unsafe |
| `adapt_via_conditioning` | adapt through context or goal input rather than retraining | Can a robot adapt to objects, users, tasks, dynamics or morphology through demonstrations, retrieval, goal parameters or online context? | hiding online training inside “conditioning” |
| `characterize_limit_then_surpass` | formalize a method-class limit, then exceed it | What observability, controllability, expressivity, reachability, bandwidth, stiffness or sample-efficiency boundary blocks the current class, and what addition crosses it? | reporting a plateau without a limit argument |
| `targeted_self_supervised_objective` | make one structural property the target of label-free learning | Can an objective specifically encode contact state, affordance, deformation, slip, dynamics, safety margin or morphology rather than generic invariance? | generic contrastive learning with a new name |

### Selection protocol

For each operator, write one sentence answering: “If applied faithfully, how would this move close the cited bottleneck?” Mark `no_fit` when it would only decorate the idea. Prioritize the viable operators by:

1. direct closure of the anchor bottleneck;
2. compatibility with embodiment and system interfaces;
3. ability to yield a named mechanism and falsification variable;
4. substantive difference from the closest work;
5. feasibility inside the stated resources and safety envelope.

Do not prioritize using ResearchStudio's original pattern counts, accept/reject rates or saturation bands. Those came from a different corpus and are not robotics priors.

### Mechanism instantiation contract

An operator has been enacted only if the candidate states:

- the before-state and the structural move;
- the physical/software objects changed;
- the interface through which the change reaches robot behavior;
- a named load-bearing variable;
- a downstream prediction and matched negative control;
- the closest-work delta.

Examples of variables include estimator age at control use, contact-mode posterior entropy, energy injected per impact, effective stiffness along a task direction, closed-loop phase margin, deformation-state error, cycle-time tail latency, or operator intervention rate. “Better representation” and “embodied intelligence” are themes, not variables.

### Composition discipline

Use one primary operator. Add a supporting operator only when it closes a different necessary sub-gap. Every added operator creates an interface and an alternative explanation; record both. Three operators is the hard maximum for a single card.

Reject kitchen-sink compositions, circular dependencies and mechanisms whose pieces can be removed without changing the claim. A multi-component system may still be simple if one causal chain explains why every component is necessary.

### Audit-only failure checks

Do not load these checks during unconstrained generation. Use them after the candidate exists:

- **Assumption audit + auxiliary signal:** did the new signal actually address the violated assumption, or only correlate with success?
- **Assumption audit + structural prior:** is the claimed invariant valid under the exact physical violation being studied?
- **Assumption audit + operator substitution:** does the replacement preserve the property that became load-bearing after the pivot?
- **Decomposition:** is the partition identifiable at run time and does differentiated treatment beat a matched uniform alternative?
- **Delegation:** are intermediate artifacts typed, timed and auditable, with failure recovery?
- **Relaxation:** does the continuous solution map to a feasible discrete/hardware design without erasing the gain?
- **Biomimetic or soft mechanism:** is morphology/material causally isolated from controller capacity, fabrication quality and total energy?
- **Learning mechanism:** are data, compute, seed and simulator differences controlled?

An audit finding produces a named bounded patch. It must not silently replace the core claim, minimal falsification test, load-bearing variable or compute budget.
