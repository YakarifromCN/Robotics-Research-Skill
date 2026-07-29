# Robotics Research Skill — Handoff

> 状态：进行中（WIP）
> 快照日期：2026-07-29
> 当前工作区：`E:\Project\Robotics-Research-Skill`

这份文件供未来在工作站接入本环境后继续工作。先读本文件，再读
`references/active-corpus-first-reference.md` 和
`references/researchstudio-methodology.md`。不要把当前的 smoke/fallback 产物
误报成真实的 ResearchStudio 统计结果。

## 1. 用户要求的不可改变约束

本项目的核心目标是：用机器人论文/venue 形成可解释的研究子流形轴，作为
idea 设计、实验设计、论文行文和审稿反馈的第一核心参考；再把研究因子向量、
证据需求、主张高度与指定 venue 的最新官方范围结合起来做路由。

必须保持：

- venue 的所有主题信息都服务于机器人研究子流形分解；不要把学会评级或 CCF
  评级作为核心轴，也不要重新引入 rating/prestige 字段。
- 直接机器人 venue 与机器人强相关 venue 可以作为 scope prior；直接机器人
  venue 的 `directness_weight` 较高，强相关 venue 权重较低，但这不是质量排名。
- 不能从目录、奖项、模式频率或 fit score 推导真实录用概率；运行时统一使用
  `acceptance probability = NOT_ESTIMABLE`。
- 100 篇论文保持期刊:会议 = 50:50；会议必须有 oral 或更高的公开演示痕迹；
  奖项认可记录至少 51 篇；八个研究轴均匀采样，当前主轴计数为
  `E/P/C/L = 13/13/13/13`、`D/H/A/S = 12/12/12/12`。
- 论文语料库不是静态附件：未来必须用它支撑 idea、实验条件、对照、主张高度、
  related work 和 venue 路由。

## 2. 已经落地的基础设施

### 2.1 机器人研究子流形

`corpus/robotics-submanifold.v1.json` 定义了八条透明语义轴：

| ID | 轴 |
|---|---|
| E | 具身形态与接触 |
| P | 感知与状态估计 |
| C | 控制、动力学与安全 |
| L | 学习、表示与适应 |
| D | 规划、决策与协同 |
| H | 人机交互、触觉与 XR |
| A | 自主系统与部署运行 |
| S | 系统集成、实时与基础设施 |

它包含语义标签、0–3 轴向编码规则、证据压力和路由解释。它是可解释的
机器人专家层，不是声称由 100 篇样本完成了统计意义上的 PCA/因子分析。

### 2.2 Venue catalog

`corpus/venue-catalog.v2.json` 是运行时 canonical catalog，共 114 条记录，
覆盖自动化学会/CCF 提供的会议和期刊语义，以及用户补充的机器人原生期刊：

- IEEE Transactions on Robotics
- IEEE Robotics and Automation Letters
- The International Journal of Robotics Research
- Science Robotics
- Autonomous Robots
- IEEE Robotics and Automation Practice
- IEEE Transactions on Haptics

v2 不保存评级；使用 `layer`、`topic_tags`、`contribution_gate` 和
`directness_weight` 做候选 scope 路由。`venue-catalog.v1.json` 只保留作兼容/旧
测试参考，新逻辑应使用 v2。

### 2.3 100 篇论文语料库

主文件是 `corpus/public-paper-index.json`，schema 为
`robotics-public-corpus.v2`：

- 100 条记录，50 journal + 50 conference；
- 会议演示痕迹为 36 oral、6 spotlight、8 best_paper；
- 51 条 `award_recognition` 配额记录，其中当前状态为 37 winner、13 finalist、
  1 award；这不是“中稿/录用标签”；
- 每条记录含公开 preprint/author PDF 或 final venue URL、轴向向量、模式标签、
  可抽取提示和 `do_not_infer` 边界；
- 当前 JSON 是元数据/短抽取提示语料，不是 100 篇全文已经摄入的本地全文库。

语料约束与生成/校验入口：

- `references/public-paper-corpus-contract.md`
- `scripts/build_public_paper_index_v2.py`
- `scripts/validate_public_paper_index.py`

### 2.4 ResearchStudio 方法链

已蒸馏于 `references/researchstudio-methodology.md` 和
`references/active-corpus-first-reference.md`：

```text
paper + descriptive outcome
  -> Stage-1 innovation signature
  -> Stage-2 domain-agnostic strategy signature
  -> embedding -> UMAP -> HDBSCAN
  -> fine-grained clusters
  -> 15 parent operators / 31 robotics tactical cards
  -> axis strategy + online idea chain
```

已生成：

- `corpus/researchstudio-pattern-cards.v1.json`：15 个主模式卡、31 个机器人
  适配子模式卡；当前为可解释 seed library，不是假称由机器人全文聚类诱导；
- `corpus/researchstudio-paper-signatures.v1.json`：100 条签名适配记录；显式标注
  `data_fidelity = METADATA_ONLY`、`llm_reextraction_required = true`；
- `corpus/researchstudio-cluster-analysis.v1.json`：当前管线 smoke 输出；
- `corpus/robotics-axis-strategy-analysis.v1.json`：每个轴的最佳结构策略基线、
  组合模式、子模式、证据配方、失败护栏、主张高度和 venue scope 标签。

当前八轴策略锚点为：

| 轴 | 当前结构策略锚点 | 默认组合 |
|---|---|---|
| E | P08 Encode Structure by Construction | P08 + P02 |
| P | P04 Design a Confound-Isolating Diagnostic | P04 + P05 |
| C | P01 Audit and Pivot an Assumption | P01 + P14 |
| L | P07 Manufacture the Supervisory Signal | P07 + P03 |
| D | P10 Decompose for Differentiated Treatment | P10 + P11 |
| H | P04 Design a Confound-Isolating Diagnostic | P04 + P05 |
| A | P06 Reframe as a Solvable Object | P06 + P04 |
| S | P08 Encode Structure by Construction | P08 + P04 |

这些是“根据轴和结构性缺口选择研究策略”的基线，不是固定 venue 排名，也不是
录用概率模型。

### 2.5 四个本地 Skill 已接入

当前仓库实际有四个可用入口：

- `skills/develop-robotics-idea/SKILL.md`
- `skills/design-robotics-experiment/SKILL.md`
- `skills/write-robotics-paper/SKILL.md`
- `skills/review-robotic-feedback/SKILL.md`

它们通过各自的 `references/robotics-submanifold-routing.md` 和根目录
`references/active-corpus-first-reference.md` 调用共享上下文；原始契约保存在
同目录的 `SKILL.md.source`，不要在升级时悄悄删除 Claim Lock、Design Lock、
Claim Ledger 或只读审稿边界。

运行时模块/入口：

- `common/robotics_submanifold.py`
- `common/robotics_research_context.py`
- `common/researchstudio_patterns.py`
- `common/researchstudio_ideation.py`
- `scripts/route_robotics_research.py`
- `scripts/ideate_robotics_research.py`
- `scripts/induce_researchstudio_patterns.py`
- `scripts/run_researchstudio_robotics_pipeline.py`

## 3. 当前明确未完成的任务

按优先级继续，不要直接把下面项目标记为完成。

### P0 — 建立真正可分析的 100 篇全文语料

1. 逐条核验 `public-paper-index.json` 的公开最终中稿预印本/作者稿；将可合法
   使用的 PDF 或抽取文本放入独立缓存目录（建议 `corpus/papers/` 或外部缓存），
   不要把大段受版权保护的正文复制进 JSON。
2. 为每条记录补充全文缓存路径、下载/核验日期、哈希、版本关系、开放来源和
   final-publication 对应关系。
3. 维持 50:50、oral+、51 条 award_recognition 和八轴均衡；任何替换都要重新
   跑 `validate_public_paper_index.py`。
4. 公开论文的奖项/演示证据只能作为 provenance 和描述性审计信号，不能被改名为
   decision outcome。

### P0 — 用全文/摘要重新抽取 ResearchStudio 签名

当前 `scripts/build_researchstudio_signature_index.py` 是 metadata adapter。下一版
必须从 title + abstract/introduction + methods/experiments（如可得）和公开 review/
decision 材料抽取：

- Stage-1：innovation approach、key step、why non-obvious、trigger condition、
  reviewer praise、reviewer concern、acceptance signal、contribution type；
- Stage-2：四个去领域化、机制保真的 strategy fields；
- 每个字段的来源定位、抽取置信边界和 `do_not_infer`；
- 没有 review/decision 的论文，明确留空，不要编造 Oral/HC/Reject。

完成后把 `data_fidelity` 从 `METADATA_ONLY` 改成更细的、按记录可追溯的状态，
同时保留旧适配结果或版本化输出，避免不可审计覆盖。

### P0 — 真正运行 embedding / UMAP / HDBSCAN

“缺少 UMAP/HDBSCAN 依赖”指当前 Python 环境没有第三方算法库 `umap-learn`
和 `hdbscan`（通常还需要 `numpy`/`scikit-learn`）。这不是缺少论文数据。

当前报告的真实状态是：

```text
embedding: hash_smoke
projection: FALLBACK_NOT_UMAP  (numpy_svd)
clustering: FALLBACK_NOT_HDBSCAN (density_components)
cluster_count: 0
all 100 records: geometric unclustered/noise in this smoke run
```

当前脚本已经接好严格门禁：

```powershell
$env:PYTHONUTF8 = '1'
python -B scripts/run_researchstudio_robotics_pipeline.py --strict-real
```

在依赖未安装或输入向量仍是 hash smoke 时，`--strict-real` 应该失败或不能被
当作生产结果。生产运行还需要真正的文本 embedding（ResearchStudio 方法链的
目标配置为 `text-embedding-3-large`，或经过记录的等价离线 embedding），不能仅
因为 UMAP/HDBSCAN 导入成功就把 hash 向量称作研究结论。

建议将 embedding 作为可复现的单独 artifact/manifest 保存，去除 venue 名称、应用
名和数据集名造成的 topic leakage；不要把 API key 写入仓库。

### P1 — 真实 cluster audit 与模式卡诱导

真实签名和向量完成后：

1. 对 cluster 数量、噪声比例、稳定性、近邻样本、轴/venue 混杂进行审计；不要求
   HDBSCAN 的 cluster 数量机械等于 31。31 是 tactical card vocabulary；实际 cluster
   数量由数据和参数决定。
2. 用 LLM 将细粒度策略簇归纳到 31 个 tactical cards 和 15 个 parent operators，
   记录每张卡的正例、失败形状、审稿关切、证据 provenance 和低覆盖警告。
3. 当前 `pattern_card_status` 是
   `SEED_LIBRARY_AVAILABLE; CLUSTER_TO_CARD_LLM_INDUCTION_NOT_RUN`，完成后才可
   版本化升级为生产卡库。

### P1 — outcome 对比仍待补齐

当前语料虽然有 oral/spotlight/best_paper 和 award recognition，但没有同一抽样
机制下的 decision-aligned Oral/HC/Reject 表。因此：

- `outcome_contrast.status = DISABLED` 是正确状态；
- 不要用 award 或 presentation 代替 reject/accept；
- 要做模式对比，必须补充有 provenance、分母清楚、来源机制一致的 outcome dataset，
  并只报告类条件描述；仍不能输出真实录用概率。

### P1 — 十个外部 workflow 的逐项能力蒸馏

用户给出的 Awesome-Journal-Skills 目标包括：通用 AI conference、通用工程技术
journal、Science Robotics、IJRR、T-RO、HRI、CoRL、RSS、IROS、ICRA。

当前仓库没有这十个独立的本地 skill 目录；目前是把共享机器人子流形、ResearchStudio
策略上下文和 venue routing 能力接入四个本地 skill。外部仓库提交版本只在
`SOURCE_SNAPSHOTS.json` 留有来源快照。因此尚待：

1. 在网络可用时逐项读取十个外部 skill 的最新内容，并记录 URL、commit、读取日期；
2. 提炼各自的 scope、格式、审稿/投稿、实验和写作约束，不复制与机器人无关的
   主题分类；
3. 形成 venue-specific adapter/reference 和测试，全部先经过八轴 + 100 篇语料
   + ResearchStudio strategy context，再叠加目标 venue 官方 scope；
4. 对 ICRA/IROS/RSS/CoRL/HRI 与 T-RO/IJRR/Science Robotics 分别做 route smoke。

### P2 — 重新生成每轴投稿策略

`robotics-axis-strategy-analysis.v1.json` 当前是 metadata-only 的透明结构拟合基线。
完成全文签名、真实聚类和卡库诱导后，重新生成每个轴的：

- 主模式及 1–3 个组合模式；
- tactical subpattern；
- 证据配方、失败护栏、主张高度；
- 候选 venue 的官方范围适配说明；
- 研究强度/证据需求/主张高度的解释性输出。

“最适合某 venue”只能表达为当前贡献结构与官方 scope 的 fit 解释和候选排序；
必须附上官方 scope/author guide 的新鲜核验日期，不能输出录用概率。

## 4. 在工作站恢复工作的顺序

在新工作站把仓库路径替换为实际路径后：

```powershell
Set-Location E:\Project\Robotics-Research-Skill
$env:PYTHONUTF8 = '1'
python --version
```

先做无网络、无写入外部系统的完整回归：

```powershell
python -B scripts/run_all_checks_corpus_first.py
```

预期最后一行：

```text
ALL_CHECKS_CORPUS_FIRST_RESEARCHSTUDIO: PASS
```

该回归默认允许 fallback，所以 PASS 不代表真实 UMAP/HDBSCAN 已完成。四个 skill
的结构校验另行运行（`D:\.codex\skills\.system\skill-creator\scripts\quick_validate.py`
路径按新工作站实际环境调整）：

```powershell
$q = 'D:\.codex\skills\.system\skill-creator\scripts\quick_validate.py'
python $q 'skills/develop-robotics-idea'
python $q 'skills/design-robotics-experiment'
python $q 'skills/write-robotics-paper'
python $q 'skills/review-robotic-feedback'
```

检查研究上下文和路线：

```powershell
python -B scripts/route_robotics_research.py `
  skills/develop-robotics-idea/assets/research-card.template.json `
  --stage idea --venue conf-icra --per-axis 2 `
  --output tmp/route-idea.json
```

运行当前可用的 ResearchStudio smoke 管线：

```powershell
python -B scripts/run_researchstudio_robotics_pipeline.py
```

安装并确认真正的 UMAP/HDBSCAN、补入真实 embedding 和全文签名后，再运行：

```powershell
python -B scripts/run_researchstudio_robotics_pipeline.py --strict-real
```

在线 idea 链的输入是一个 profile JSON：

```powershell
python -B scripts/ideate_robotics_research.py <profile.json> `
  --venue journal-t-robotics --output tmp/idea-card.json
```

缺少文献、全文 grounding、机制碰撞证据或结构性缺口时，预期是
`DO_NOT_GENERATE` / `REVISE` / `ABANDON`，不是让模型补写一个看似完整的 idea。

## 5. 编辑约定和常见陷阱

- 许多入口文件是薄 wrapper，真实实现保存在同名 `.source` 文件；改实现时先比对
  wrapper/source 约定，避免只改 wrapper 导致下一次生成覆盖修改。
- Windows PowerShell 的默认编码可能破坏 UTF-8 JSON；读取/验证时使用
  `-Encoding UTF8`，运行 Python 时设置 `$env:PYTHONUTF8='1'`。
- 不要用 `git reset --hard`、`git checkout --` 或批量删除来“清理”工作区；当前
  工作区存在大量用户新增/未跟踪的基础设施文件。
- `corpus/venue-catalog.v2.json` 是运行时目录；不要把 v1 的旧评级语义重新带回
  skill。
- 论文的 `award`、presentation、venue、计数和 pattern fit 只能作检索/审计/路由
  上下文；不应写入论文主张作为质量或录用证据。
- 任何 venue 的最终投稿建议都要重新查看该 venue 官方 CFP、aims & scope、
  author guide、伦理、artifact、视频、rebuttal 和页数规则；目录只提供候选方向。

## 6. 交接完成标准

下一位维护者在声称本项目完成前，至少应能给出：

1. 可追溯的 100 篇开放全文/最终中稿预印本缓存和逐条来源；
2. 非 metadata-only 的 Stage-1/Stage-2 签名及抽取 provenance；
3. 真实 embedding manifest、`REAL_UMAP`、`REAL_HDBSCAN` 和 cluster audit；
4. 真实 cluster-to-card 归纳后的 15/31 模式卡版本；
5. 每个 E/P/C/L/D/H/A/S 轴的策略模式、证据压力、主张高度和官方 venue scope
   fit 报告；
6. 四个本地 skill 的回归测试，以及十个外部 workflow 能力是否完成逐项蒸馏的明确
   记录；
7. 全部输出继续明确 `NOT_ESTIMABLE`，不伪造录用概率。

本文件本身只记录交接状态，不替代各 skill 的 `SKILL.md`、ResearchStudio 方法
参考和 corpus schema。任何升级都应同时更新对应 schema、validator、测试和本文件。
