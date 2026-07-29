# Robotics venue workflow routing

本文件把外部 venue workflow 的可迁移能力压缩为本仓库的四个原子 Skill，而不是把外部 `SKILL.md` 原样复制进来，也不是在仓库中生成十套内部 workflow。统一方法的规范版本见 `unified-venue-workflow-adapter.v1.md`，外部来源与内容哈希见 `external-workflow-source-receipt.v1.json`。所有目标 venue 先经过同一组研究流形问题，再把贡献门槛、证据压力和流程节奏映射到项目向量。

## 统一路由合同

每次 venue 判断必须先回答八个问题：

1. 论文的 load-bearing contribution 是具身机制、感知、控制、学习、规划、交互、自主部署，还是系统基础设施？
2. 该贡献在八轴向量中的主轴和副轴是什么？
3. 证据形状是理论/证明、仿真、台架、真实机器人、长期现场、用户研究，还是可复现实验基础设施？
4. 目标 venue 的官方范围是否把该贡献当作主体，而不是机器人应用案例？
5. 还缺哪一个最可能导致 desk reject 或低可信度的证据？
6. 投稿周期、补充材料、视频、rebuttal、伦理审批和 artifact 是否已经进入负责人—截止日期表？
7. 哪些规则来自当前官方来源，哪些只是需要刷新的历史快照？
8. 该 workflow 中哪项能力可沉淀为跨 venue 的 Skill 知识，哪项只能保留为 venue adapter？

输出固定为：主 venue、条件备选、不要投的相邻 venue、最大缺口、下一步；不输出仅由 venue 名称推断的录用概率。

## 外部 workflow → 当前四个 Skill

| 外部能力 | 子流形重心 | 重定向到 | 当前 Skill 中的落点 |
|---|---|---|---|
| CS/AI conference router | L/P/D/S | Idea → Experiment → Review | 贡献族、证据形状、受众、周期、venue sibling 消歧与 fallback |
| Engineering journal router | E/P/C/L/S | Idea → Writing → Review | theory/method/system/device 与 proof/simulation/bench/field 路由 |
| Science Robotics | E/P/A/H/S | Experiment → Writing → Review | 广泛重要性、真实或高度逼真的物理能力、重复试验、统计、视频、硬件复现、局限性 |
| IJRR | E/P/C/L/D | Idea → Experiment → Writing | 长文概念框架、机制一般性、跨条件分析、深度和完整性 |
| T-RO | E/P/C/L/S | Experiment → Writing → Review | 完整严谨验证、真实机器人/高保真仿真、定量对比、消融、sim-to-real 与复现 |
| HRI | H/P/A | Experiment → Writing → Review | participant/IRB、招募、预注册/效应量、用户协议、论文—rebuttal—camera-ready 与 track 选择 |
| CoRL | L/P/C/S | Idea → Experiment → Review | seeds、split、baseline、真实机器人 spot-check、补充材料、limitation 和 rebuttal |
| RSS | E/P/C/D/S | Experiment → Writing → Review | 单轨制、机制消融、失败归因、硬件 campaign、匿名化、artifact 与 fallback |
| IROS | E/P/C/A/S | Experiment → Writing → Review | paper/video 两个截止点、真实系统、sim-to-real、页数/参考文献和无传统 rebuttal |
| ICRA | E/P/C/L/S | Idea → Experiment → Writing | paper/video 两个窗口、硬件日志、无传统 rebuttal、RA-L/IROS/CoRL fallback |

## 轴—证据重定向规则

- `E`：必须解释形态、材料、接触或机构为何产生能力；补机制干预、制造边界和接触失败。
- `P`：必须证明传感器/状态估计有效；补 held-out 条件、不确定性和失败日志。
- `C`：必须把动力学、稳定性、安全或时序性质变成可检验对象；补控制基线、边界、恢复时间。
- `L`：必须固定数据 lineage、split、seed、checkpoint 和迁移边界；区分 learned contribution 与工程包装。
- `D`：必须有可识别的规划/协同对照、长时域任务或规模预算；报告任务失败类型。
- `H`：必须锁定参与者/操作者单位、交互任务、协议、风险与停止规则；不能用一次简单展示替代人因证据。
- `A`：必须给出运行包络、持续时间、恢复与跨环境/站点边界；不要把一次 demo 写成 deployment claim。
- `S`：必须固定接口、频率、版本、硬件软件组合和 artifact；让他人可以重跑或审计。

## 使用顺序

1. `scripts/analyze_robotics_submanifold.py` 或 v2 八轴策略工件生成项目向量、研究强度和 venue candidates；未实时核验的 venue 候选必须标记 `REFRESH_REQUIRED`。
2. Idea Skill 将 venue 的 contribution gate 转为候选主张和最小证据，不改写 Claim Lock。
3. Experiment Skill 将活动轴的 evidence pressure 转为设计锁、条件矩阵、trial registry、伦理/安全和 artifact 任务。
4. Writing Skill 按 venue 模式选择“广泛重要性 / 长文概念框架 / 完整严谨验证 / 交互贡献 / 学习 benchmark”等叙事，并逐条绑定 Claim Ledger。
5. Review Skill 以活动轴、venue gate、官方周期和未解决证据缺口生成审查面板。

## 外部来源

能力蒸馏基于用户指定的公开仓库目录：

- [cs-ai-conference-workflow](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/Computer-Science-Conference-Skills/skills/cs-ai-conference-workflow)
- [en-engtech-journal-workflow](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/Engineering-Technology-Journal-Skills/skills/en-engtech-journal-workflow)
- [Science Robotics](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/English-NaturalScience-Journal-Skills/skills/science-robotics)
- [IJRR](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/Engineering-Technology-Journal-Skills/skills/the-international-journal-of-robotics-research)
- [T-RO](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/Engineering-Technology-Journal-Skills/skills/ieee-transactions-on-robotics)
- [HRI](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/HRI-Skills)
- [CoRL](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/CoRL-Skills)
- [RSS](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/RSS-Skills)
- [IROS](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/IROS-Skills)
- [ICRA](https://github.com/brycewang-stanford/Awesome-Journal-Skills/tree/main/ICRA-Skills)

官网周期、范围和 awards 证据必须在实际投稿前重新检查；本文件是能力路由基础设施，不替代当年官方 CFP、author guide、program 或 ethics policy。
