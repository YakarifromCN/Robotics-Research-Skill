# 中文版

## ResearchStudio 与机器人研究的融合

本 skill 改编了 Microsoft ResearchStudio 的 `ResearchStudio-Idea` / IdeaSpark 项目方法，重点包括构想模式词汇、检索优先的证据落地、既有工作碰撞、独立审计、机制感知证伪、廉价否决检查与确定性锁校验。

- 项目：<https://github.com/microsoft/ResearchStudio>
- 项目文档：<https://microsoft.github.io/ResearchStudio/>
- ResearchStudio-Idea 论文：<https://arxiv.org/abs/2607.04439>
- 上游许可证：MIT；版权声明保留于仓库级 `THIRD_PARTY_NOTICES.md`。

### 保持不变的原则

1. **证据先于发明。** 提出机制前，先重构真实研究前沿。
2. **模式是诊断算子。** 它们描述可能闭合缺口的结构性变换；既不是标签，也不是配方。
3. **选择与生成分层。** 先判断算子—缺口匹配，再实例化领域机制。
4. **先碰撞，后建立信心。** 将拟议机制与检索到的最近工作比较，而不只是著名或方便的基线。
5. **审计与生成分离。** 创作轮次不应为自己的逻辑盖章。
6. **证伪必须感知机制。** 命名一个承重变量，并使用使下游结果向基线回归的负对照。
7. **扩张前先廉价否决。** 缺少任务、证据、安全测试或合理资源包络时，应尽早停止。
8. **锁定字段防止静默漂移。** 下游不能悄悄用更容易的问题替换困难实验。
9. **反模式仅用于审计。** 在生成时加载失败配方，可能把候选偏置为泛化的增量工作。

### 针对机器人研究的改变

原始算子语料从机器学习会议结果归纳而来。其论文频率、录用/拒稿关联和饱和度统计都不是机器人刊物的证据，绝不能复用为录用先验。

机器人研究增加了一条物理因果链：

`environment -> embodiment/sensing -> state -> decision -> actuation/contact -> task outcome`

构想必须暴露拟议机制在该链的作用位置、什么内容跨越组件接口，以及为什么机器人不可替代。硬件和材料带来制造差异、迟滞、磨损、校准与安全问题。集成系统带来时序、故障传播与恢复问题。面向人的工作带来伦理与人群有效性。现场工作带来运行包络与可维护性。

这些问题被压缩为一个机器人研究流形，而非按刊物隔离的人格。十个相互正交、由主张触发的修饰符激活领域特定压力测试，同时八个轴对全部机器人研究保持一致。形态依赖与生物启发分离，人机交互与临床/医疗证据分离，因此自然科学默认假设不会泄漏到普通人形或 HRI 工作中。

### 明确的非目标

- 不重建 ResearchStudio 庞大的机器学习特定流水线或结果统计。
- 不训练模型，也不暗示进行了统计意义上的微调；这是透明的 skill 层方法适配。
- 不从轴向量推断刊物声望、录用概率或审稿人行为。
- 不允许刊物格式改变底层主张、机制或证伪测试。

### 去偏的跨领域蒸馏

自然科学与广泛影响期刊 skill 是正负混合的方法来源。只保留领域中立的科研逻辑：证据先于构想或行文、显式主张边界、来源核验、术语与论证纪律、不确定性披露，以及分阶段独立审计。这些是通用的诚信与推理实践，不是 Nature 派生的机器人标准。

移除无法迁移的非工程先验。拒绝：

- 在机器人特定主张存在之前自动采用“广泛意义”框架；
- 把材料、生物医学、临床或多组学证据假设应用到无关机器人工作；
- 一刀切的最大证据活动；
- 在机器人机制、碰撞与证伪锁定前先写期刊成稿；
- 用声望标签替代主张高度。

这是去偏，而不是全盘否定：有用的总体逻辑得以保留，但自然科学采样、材料、生物医学与影响力假设不会成为机器人研究默认值。

### 实现测试

忠实的机器人适配应能回答全部问题：

- 作者能否识别精确的物理或系统瓶颈？
- 算子是否产生具体机制，而不是口号？
- 最近工作差异是否在具身、机制、接口与证据维度上明确？
- 对已命名承重变量的一次干预能否区分机制？
- 主张、最小测试与资源预算是否已锁定，供下游使用？
- 如果最终刊物改变，同一研究卡是否仍有意义？

---

# English Version

## ResearchStudio-to-robotics fusion

This skill adapts methodology from Microsoft ResearchStudio's `ResearchStudio-Idea` / IdeaSpark project, especially its ideation-pattern vocabulary, retrieval-first grounding, prior-art collision, independent audit, mechanism-aware falsification, cheap kill checks and deterministic lock validation.

- Project: <https://github.com/microsoft/ResearchStudio>
- Project documentation: <https://microsoft.github.io/ResearchStudio/>
- ResearchStudio-Idea paper: <https://arxiv.org/abs/2607.04439>
- Upstream license: MIT; copyright notice is preserved in the repository-level `THIRD_PARTY_NOTICES.md`.

### What remains invariant

1. **Evidence before invention.** Reconstruct a real research frontier before proposing a mechanism.
2. **Patterns are diagnostic operators.** They describe structural moves that may close a gap; they are neither labels nor recipes.
3. **Selection and generation are layered.** First judge operator-to-gap fit, then instantiate a domain mechanism.
4. **Collision precedes confidence.** Compare the proposed mechanism with the closest retrieved work, not merely famous or convenient baselines.
5. **Audit is separated from generation.** The authoring pass should not rubber-stamp its own logic.
6. **Falsification is mechanism-aware.** Name one load-bearing variable and use a negative control whose downstream outcome returns toward baseline.
7. **Cheap kills precede expansion.** Missing task, evidence, safe test or plausible resource envelope stops the run early.
8. **Locked fields prevent silent drift.** Downstream work cannot quietly replace the hard experiment with an easier one.
9. **Anti-patterns are audit-only.** Loading failure recipes during generation can bias the candidate toward generic incrementalism.

### What changes for robotics

The original operator corpus was induced from machine-learning conference outcomes. Its paper frequencies, accept/reject associations and saturation statistics are not evidence about robotics venues and must not be reused as acceptance priors.

Robotics adds a physical causal chain:

`environment -> embodiment/sensing -> state -> decision -> actuation/contact -> task outcome`

An idea must expose where the proposed mechanism acts in that chain, what crosses component interfaces, and why a robot is essential. Hardware and materials introduce fabrication variability, hysteresis, wear, calibration and safety. Integrated systems introduce timing, fault propagation and recovery. Human-facing work introduces ethics and population validity. Field work introduces operating envelopes and maintainability.

These concerns are compressed into one Robotics Research Manifold rather than separate venue personas. Ten orthogonal, claim-triggered modifiers activate domain-specific pressure tests while the eight axes remain common to all robotics work. Morphology is separate from biological inspiration, and human interaction is separate from clinical or medical evidence, so natural-science defaults do not leak into ordinary humanoid or HRI work.

### Deliberate non-goals

- Do not recreate ResearchStudio's large ML-specific pipeline or its outcome statistics.
- Do not train a model or imply statistical fine-tuning. This is a transparent skill-layer methodological adaptation.
- Do not infer venue prestige, acceptance probability or reviewer behavior from an axis vector.
- Do not let venue formatting change the underlying claim, mechanism or falsification test.

### De-biased cross-domain distillation

Natural-science and broad-impact journal skills are mixed methodological sources. Retain only domain-neutral research logic: evidence before idea or prose, explicit claim boundaries, source verification, terminology and argument discipline, uncertainty disclosure, and staged independent audit. These are general integrity and reasoning practices, not Nature-derived robotics standards.

Remove the non-engineering priors that do not transfer. Reject:

- automatic “broad significance” framing before a robot-specific claim exists;
- materials, biomedical, clinical or multi-omics evidence assumptions applied to unrelated robotics work;
- one-size-fits-all maximal evidence campaigns;
- journal-ready prose before the robotics mechanism, collision and falsification are locked;
- prestige labels used as a substitute for claim altitude.

This is de-biasing, not blanket rejection: useful overall logic survives, while natural-science sampling, materials, biomedical and impact assumptions do not become robotics defaults.

### Implementation test

A faithful robotics adaptation should answer all of these:

- Can an author identify the exact physical or system bottleneck?
- Does the operator produce a concrete mechanism rather than a slogan?
- Is the closest-work delta explicit on embodiment, mechanism, interface and evidence?
- Can one intervention on the named load-bearing variable distinguish the mechanism?
- Are the claim, minimal test and resource budget locked for downstream work?
- Would the same card remain meaningful if the eventual venue changed?
