# 机器人科研 Skill

面向长期机器人科研的统一 Skill 包。Idea → Experiment → Writing → Review 是它的主干闭环，但不是能力边界；系统同时覆盖文献检索、先例碰撞、既有项目迁移、实验审计、结果封装、可复现性、LaTeX 审计和投稿前主张检查。

本仓库不是一组按会议或期刊拆分的提示词，也不根据投稿载体建立静态科学层级。它把机器人研究中可复用的科研约束压缩为统一工作流，再根据用户主张、机制、资源、风险和预期证据，选择适当的研究深度。覆盖具身智能、控制、学习、仿生、软体机器人、人机交互、工业自动化、现场系统与多机器人研究，可用于 SII、Humanoids、ROBIO、ICRA、IROS、RA-L、RAP、T-RO、IJRR、RSS、CoRL、CASE、RoboSoft、Soft Robotics、Science Robotics 等相关研究场景。

当前版本采用 corpus-first v2 路径：100 篇均衡公开论文先形成来源、文本覆盖和混合保真签名收据，再由模型子代理模拟 embedding、聚类审计和策略归纳。该模拟不冒充真实 UMAP/HDBSCAN；运行时只注入由 8 个能力簇归纳出的 15 个模式族、31 个子模式和 8 个研究路由问题。十个外部 venue workflow 也只被蒸馏为一套统一方法及 venue 映射，不在仓库中复制十套内部 workflow。

本项目另有独立的 `develop-robotics-engineering` 工程执行 Skill，以及显式启用的 `robotics-ar` 自动研究模式。Engineering 可单独完成控制、优化、ROS、学习、嵌入式、仿真和部署代码任务；Robotics-AR 可在其存在时选择性调用，缺失时继续使用自身 Code/Test/Runner 协议。Robotics-AR 从 ARIS（[auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/auto-claude-code-research-in-sleep)）蒸馏领域中立生命周期与安全契约，但不把 ARIS 作为运行时依赖。

当前稳定契约版本由根目录 `VERSION` 管理。发布前唯一 CI 入口为：

```bash
python3 -B scripts/run_stable_checks.py
```

只有该命令通过、正式 release builder 在 clean checkout 上通过且包内 manifest 标记 `source_dirty=false`，才能标记为 STABLE。

## 为什么需要这套 Skill

机器人论文经常跨越算法、动力学、硬件、材料、控制、感知和真实环境。仅靠写作模板无法解决以下问题：

- Idea 阶段的核心主张在实验阶段被悄悄改写；
- 实验完成后才重新定义主指标、分母或排除规则；
- 仿真、台架、实机、现场和独立复现被压成不合理的单一序列；
- 负对照只是方法改名，无法区分真正机制；
- `INCONCLUSIVE` 在写作中被升级成“有效”；
- 既有项目被强行套入从零开始的科研流程；
- 投稿格式、篇幅和读者偏好反过来改变科学事实。

本项目通过稳定 ID、摘要锁、结构化判定规则、非序数证据画像和一等停止状态约束这条链路。

## 原子 Skill 主干

### `develop-robotics-idea`

把研究方向转化为可证伪的科学合同，支持：

- 新 Idea 探索；
- 已有 Idea 审计；
- 接纳用户已经冻结的 Idea；
- 迁移没有 Research Card 的既有项目；
- 最近邻检索与先例碰撞检查；
- 机制、承重变量、主张边界和停止条件设计；
- candidate → audit → revision patch 的不可变审计链。

主要输出：`research-card.json`、`evidence-bundle.json`，以及候选审计工件。

### `design-robotics-experiment`

把锁定主张转化为可执行实验，支持：

- 前瞻实验设计；
- pilot 后但揭盲前的修订；
- 回顾性审计；
- 已锁定 Idea 下的微调；
- 已有结果的规范封装；
- 结构化指标估计与判定规则；
- 机器人、参与者、示范、session、trial 等层级实验单位；
- abort、排除、失败、安全事件和 protocol deviation 的完整记录。

主要输出：`experiment-contract.json`、`trial-registry.csv`、`measurement-log.csv` 和 `result-bundle.json`。

### `develop-robotics-engineering`

以最小计划、最小正确改动和聚焦测试执行机器人代码开发，包括控制/优化、感知、学习、ROS、嵌入式、仿真、硬件接口、部署和工程调参。它优先执行既有 plan/handoff，不设计科学 condition、metric 或论文 claim；默认不强制 TDD、worktree、review swarm、commit 或 push。

主要输出：代码改动，以及带统一 `task_id` 的紧凑 `agent/plan`、`agent/task`、`agent/report` 和 `agent/handoff`；完成前由单一 validator 交叉核对允许路径和冻结测试。

### `write-robotics-paper`

从冻结主张和实际结果构建可追溯稿件，支持：

- 完整论文写作；
- writing-only 既有项目；
- 仅修订、回复和主张审计；
- Claim Ledger；
- LaTeX 数字自动渲染；
- BibTeX 生成；
- 中英文夸大、泛化、因果和 demo-speak 审计；
- 证据状态单调性与 claim boundary 检查。

主要输出：`claim-ledger.json` 和经过审计的 LaTeX 稿件。

### `review-robotic-feedback`

对机器人论文执行只读、多视角同行评审，包含七个独立专门代理：

- `manuscript-proofreading`：文字、术语、LaTeX 和交叉引用；
- `robotics-contribution-review`：任务、机制、贡献差异、先例碰撞和主张边界；
- `control-optimization-review`：控制、优化、动力学假设、稳定性、实时性和基线公平；
- `robot-learning-review`：数据、训练/测试隔离、seed、oracle、泛化和 sim-to-real；
- `hardware-review`：机器人硬件、标定、制造批次、传感器、运行条件和安全；
- `evidence-artifact-audit`：Claim → Trial → Metric → Result → Figure/Table → Sentence 证据链；
- `venue-compliance-review`：基于当前官方来源的范围、格式、匿名和补充材料核验。

随后由 `meta-review` 合并共识与分歧，逐条处理 CRITICAL，输出到本次独立目录 `reviews/review-<YYYYMMDDHHMM>/{jsons,markdowns}/`。每个代理给出 1–5 分，但总分不会替代证据判断或变成投稿概率。

评审运行有三个硬约束：启动时必须显式输入目标语言；可以指定任意单语，也可以指定 `en+任意语言`（如 `en+zh` 或 `en+日本語`），但不能省略。输入只能是待审 PDF 或指定的 LaTeX 工作区；每个子代理都是刚接触稿件的独立领域审稿人，只能读取发现快照中的 `allowed_files`，不使用项目记忆、旧评审、作者意图或未列出的工作区文件。发现快照、panel prompt、报告、运行清单和 JSON 结果写入本次时间戳目录的 `jsons/`，修改路线等 Markdown 写入同目录的 `markdowns/`。

## 核心设计

### 三层科学对象

1. **Claim Shape**：只说明论文声称什么，例如具身系统、学习、机制、人类参与、软材料、实践或跨场景主张。
2. **Evidence Obligations**：逐项说明该主张为什么需要某类证据、由哪个决定性实验承担，以及未覆盖时如何收窄边界。
3. **Domain Packs**：仅在实际相关时加载 learning、soft-body、morphology、human-interaction、clinical、industrial、field 或 multi-robot 规则。

### 三类锁

- **Claim Lock**：任务、系统边界、核心主张、机制、承重变量、反证目标和主张边界。下游不得静默修改。
- **Design Lock**：实验单位、条件、主指标、分析、排除、分母和判定规则。观察结果后不得修改。
- **Operational Mutable**：校准、人员、日志位置、实测频率和更严格的安全措施。允许有理由、有版本地细化。

### 非序数证据画像

证据不使用单一总分。每项证据分别描述：

- regime：推导、仿真、硬件在环、台架、实机、人体研究或现场运行；
- coverage：分布内、留出对象/任务/环境、跨平台、压力条件或失效边界；
- duration：单次、多 session 或长期运行；
- independence：同一运行、同实验室、独立团队、独立场地或多场地；
- experimental unit：seed、对象、任务、轨迹、样件、机器人、参与者、示范、session 或场地。

充分性按分量比较，不把互相正交的证据类型强行排成一条线。

### 科学合同与投稿适配分离

`target-fit-snapshot.json` 单独保存目标载体、article type、读者、篇幅、匿名、格式和补充材料政策。它可以在写作阶段更新，但不会改变 Claim Lock。正式投稿前仍应依据官方来源实时复核。

## 快速开始

要求 Python 3.8+，核心工具只使用标准库。所有结构化工件都可以使用 JSON；只有
主动提供 `.yaml`/`.yml` 输入时才需要可选依赖 PyYAML：

```bash
python3 -m pip install PyYAML
```

不使用 YAML 时无需安装 PyYAML；运行时不会联网安装依赖。

```bash
git clone <your-repository-url>
cd Robotics-Research-Skill
python3 scripts/run_all_checks.py
python3 scripts/run_all_checks_corpus_first.py
```

在 Codex 中可分别调用：

```text
使用 $develop-robotics-idea 审计这个机器人研究方向，并生成 V2 Research Card。
使用 $design-robotics-experiment 将锁定主张转化为结构化实验合同。
使用 $write-robotics-paper 从结果工件构建可追溯的 LaTeX 稿件。
使用 $review-robotic-feedback 审阅机器人论文并生成 Meta Review 和修改路线。
使用 $robotics-ar（仅在明确要求时）开启带审批、可暂停恢复的跨阶段自动研究 session。
```

每个 Skill 的 `assets/` 目录提供语言中立的起始模板；不要直接把模板中的 `null` 当成有效科研判断。

脚本按正常运行、安装维护、离线语料构建和兼容迁移分层；完整清单与 staged runtime 复制边界见 [`scripts/README.md`](scripts/README.md)。

### Robot-AR v3 中途接入

Robot-AR v3 保留 `NEW_RESEARCH` 的 v2 流程，并新增 `MIDSTREAM_TAKEOVER`：接入一个
已经有代码、实验历史、环境和局部瓶颈的机器人科研项目。自主试错前必须同时存在
Project Core、历史实验 ledger、可在线验证且带 fingerprint 的环境、可复现 baseline
和用户批准的 Trial Contract。合同限定搜索空间、预算、路径、指标和停止/升级条件；
Tier 3 方法或 claim pivot、主要指标、数据协议以及真实机器人限制变化会自动暂停。

最小启动方式：

```bash
python3 skills/robotics-ar/scripts/robotics_ar.py init \
  --project-root /path/to/project \
  --entry-mode MIDSTREAM_TAKEOVER \
  --mode EXECUTION_ENABLED
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-init --project-root /path/to/project
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-status --project-root /path/to/project
```

每次 checkpoint、暂停、阻断和用户纠正都会更新 `.robotics-ar/report.md`、
`.robotics-ar/handoff.md` 和任务工件；用户纠正同时写入
`.robotics-ar/tasks/task.md`（并保留根目录兼容副本）。真实机器人仍遵守一次一批次
caution/token gate，失败后停止并等待用户。

接管的核心命令顺序是：

```bash
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-record-intake --project-root <project-root> --input <intake.yaml>
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-audit --project-root <project-root>
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-import-history --project-root <project-root>
python3 skills/robotics-ar/scripts/robotics_ar.py validate-environment --project-root <project-root> --environment-manifest <manifest.json>
python3 skills/robotics-ar/scripts/robotics_ar.py baseline-compile --project-root <project-root> --input <baseline.yaml>
python3 skills/robotics-ar/scripts/robotics_ar.py baseline-run --project-root <project-root> --environment-manifest <manifest.json>
python3 skills/robotics-ar/scripts/robotics_ar.py contract-compile --project-root <project-root> --input <contract.yaml>
python3 skills/robotics-ar/scripts/robotics_ar.py trial-propose --project-root <project-root> --input <proposal.yaml>
python3 skills/robotics-ar/scripts/robotics_ar.py batch-start --project-root <project-root> --contract <approved-contract> --receipt <environment-receipt>
```

baseline 无法复现时使用 `baseline-recover --diagnostics "..."` 记录诊断，不得借此
伪造 baseline；暂停的 simulation batch 只能在重新验证 contract、environment fingerprint
和剩余预算后使用 `batch-resume`。`trial-analyze` 必须接收 raw evidence 及带
`metric_versions`（或等价嵌入版本）的指标输入。Proposal、queue 状态、raw evidence、
decision receipt 和 checkpoint 都保留 SHA-256 绑定；完成且有结论的 trial 会进入
Do-Not-Repeat Registry，单 seed 结果不会自动成为 stable Best-Known State。

## 安装模式与本地更新

安装器位于 `scripts/`，面向六个并列 Skill：四个科研证据 Skill、独立的 `develop-robotics-engineering`，以及可选编排器 `robotics-ar`。Engineering 可单独安装；Robotics-AR 对它仅为可选依赖。`--skills all` 会自动发现当前仓库中的全部 Skill。

安装目的会决定 `--mode auto` 的默认行为：

| 使用目的 | `auto` 的默认模式 | 行为 |
| --- | --- | --- |
| `development` | `SYMLINK_TRACKED_CLONE` | 从本地 Git clone 将每个 Skill 建立到 `$CODEX_HOME/skills` 的符号链接；本地分支、工作区修改和提交立即可见，无需重新安装。 |
| `use` + `--source-root` | `SAFE_STAGED_WORKTREE` | 从本地 clone 生成带 commit 标识的发布快照，并复制当前运行时依赖闭包，再原子切换 Skill 链接；更新前检查分支、干净工作区、快速校验和 fast-forward。 |
| `use` + `--archive-url` | `DIRECT_DOWNLOAD` | 从轻量 `runtime.zip` 建立由归档 SHA-256 固定的不可变 staged release，保留 shared runtime，并将选中的 Skill 链接到该快照。 |

参与开发时：

```bash
git clone git@github.com:YakarifromCN/Robotics-Research-Skill.git
cd Robotics-Research-Skill
python3 scripts/install_local_skills.py \
  --source-root "$PWD" \
  --purpose development
```

普通使用者可从本地 clone 建立安全发布快照：

```bash
python3 scripts/install_local_skills.py \
  --source-root /path/to/Robotics-Research-Skill \
  --purpose use \
  --mode SAFE_STAGED_WORKTREE
```

正式发行先从干净工作树构建轻量包；`runtime.zip` 必须小于 5 MiB，`developer.zip` 必须小于 20 MiB，且都排除 PDF、`.git`、`agent/` 和缓存：

```bash
python3 scripts/build_release_bundle.py
```

也可以从发布页的 `runtime.zip` 安装固定版本：

```bash
python3 scripts/install_local_skills.py \
  --archive-url https://github.com/YakarifromCN/Robotics-Research-Skill/releases/latest/download/runtime.zip \
  --purpose use \
  --mode DIRECT_DOWNLOAD
```

默认目标目录是 `${CODEX_HOME:-$HOME/.codex}/skills`；可用 `--dest` 改变。`--skills all` 安装所有被发现的并列 Skill，也可用逗号分隔的 slug 选择子集。安装器不会覆盖已有目录；只有显式提供 `--replace-owned-symlink` 时才会替换本安装器自己生成的符号链接。

若安装时已经有 Robotics-AR 会话根目录，可重复提供 `--active-session-root /path/to/session`；只要该目录下存在 `.robotics-ar/session.lock`，跟踪型更新就会被阻止。

安装回执保存在目标目录的 `.robotics-research-install.json`，包含模式、目的、源 clone、分支、commit、Skill 文件哈希、归档哈希和更新策略，不包含用户稿件、实验数据或全局工作区快照。

跟踪本地 clone 的安装可手动刷新回执并执行快速校验：

```bash
python3 scripts/update_local_skills.py \
  --install-receipt "$HOME/.codex/skills/.robotics-research-install.json" \
  --ff-only \
  --fetch \
  --run-fast-checks
```

如果只希望使用已经 fetch 的远程引用，可改用 `--no-fetch`。`SAFE_STAGED_WORKTREE` 每次更新先在新发布目录完成复制和校验，再切换链接；分支偏离、未提交修改、活动中的 `.robotics-ar/session.lock` 或检查失败都会停止更新。`SYMLINK_TRACKED_CLONE` 的核心特性仍是本地分支内容实时可见。`DIRECT_DOWNLOAD` 和 `COPY_PINNED` 是固定快照，不提供自动更新。

检查安装是否漂移：

```bash
python3 scripts/doctor_local_skills.py \
  --install-receipt "$HOME/.codex/skills/.robotics-research-install.json"
```

doctor 会报告 `PASS`/`FAIL`、符号链接漂移、Skill 文件哈希变化、源 clone 是否存在以及当前 HEAD；它不会读取待审稿 PDF、LaTeX 工作区或用户项目文件。

## 典型工作流

```text
公开文献与用户材料
        │
        ▼
Research Card ── claim_digest ──┐
        │                       │
        ▼                       │
Experiment Contract ─ design_digest
        │
        ├── Trial Registry
        ├── Measurement Log
        ▼
Result Bundle
        │
        ▼
Claim Ledger ── Number/Citation/Figure trace
        │
        ▼
Audited LaTeX manuscript

Manuscript + artifacts ──► Specialist Review Panel ──► Meta Review ──► Revision Roadmap

Target Fit Snapshot ───────────► 仅影响组织、压缩与提交格式
```

项目级 `project-manifest.json` 只保存当前阶段和工件摘要，不承担科学推理。

## 常用命令

校验 Research Card：

```bash
python3 skills/develop-robotics-idea/scripts/validate_research_card.py research-card.json --ready
```

校验 candidate 审计链：

```bash
python3 skills/develop-robotics-idea/scripts/validate_revision_chain.py candidate.json audit.json revision-patch.json
```

校验实验合同与结果：

```bash
python3 skills/design-robotics-experiment/scripts/validate_experiment_contract.py experiment-contract.json --card research-card.json --ready
python3 skills/design-robotics-experiment/scripts/validate_result_bundle.py result-bundle.json experiment-contract.json --ready
```

汇总试验日志：

```bash
python3 skills/design-robotics-experiment/scripts/summarize_trials.py trial-registry.csv measurement-log.csv --abort-policy count_as_failure
```

渲染和审计论文：

```bash
python3 skills/write-robotics-paper/scripts/validate_claim_ledger.py claim-ledger.json --result result-bundle.json --card research-card.json --ready
python3 skills/write-robotics-paper/scripts/render_numbers.py manuscript.tex claim-ledger.json --output manuscript.rendered.tex
python3 skills/write-robotics-paper/scripts/audit_latex.py manuscript.rendered.tex claim-ledger.json
python3 skills/write-robotics-paper/scripts/render_bibliography.py claim-ledger.json --output references.bib
```

迁移旧项目：

```bash
python3 scripts/migrate_v1.py legacy.json --kind idea --output research-card.v2.json
```

迁移结果始终需要人工审计，回顾性合同不会被描述为预注册。

运行机器人论文评审（目标语言必须显式提供）：

```bash
python3 skills/review-robotic-feedback/scripts/discover_manuscript.py paper.pdf --language en+zh
# 或：python3 skills/review-robotic-feedback/scripts/discover_manuscript.py latex_workspace/ --language 日本語
python3 skills/review-robotic-feedback/scripts/build_panel_prompts.py reviews/review-<timestamp>/jsons/review-context.json
python3 skills/review-robotic-feedback/scripts/validate_review_report.py reviews/review-<timestamp>/jsons/*-review.json
python3 skills/review-robotic-feedback/scripts/synthesize_reviews.py reviews/review-<timestamp>/jsons/review-context.json reviews/review-<timestamp>/jsons/*-review.json
```

## 结构化实验判定

内置规则支持置信区间下界/上界、点估计阈值、非劣效和区间内判定。验证器依据冻结规则与结构化估计机械生成：

- `SUPPORTED`
- `NOT_SUPPORTED`
- `INCONCLUSIVE`

复杂分析可以引用外部脚本与输出工件，但二者都必须提供 SHA-256，并使用项目内安全相对路径。

## 试验日志与负对照

Trial Registry 每次尝试一行；Measurement Log 以长格式保存每个指标、阶段和窗口。abort policy 必须在合同中冻结：

- `count_as_failure`
- `unscored_but_in_denominator`
- `excluded_only_if_predeclared_hardware_fault`

机制负对照使用稳定的变量、指标和条件 ID，可表达回归基线、反向效应、选择性通道损失、边界移动、零效应和替代机制签名。

## 停止状态

停止不是失败的格式错误，而是正式科研输出：

- Idea：`DO_NOT_GENERATE`、`ABANDON`
- Experiment：`NO_RUN`、`CHANGE_REQUEST_TO_IDEA`
- Writing：`EVIDENCE_GAPS`

`REVISE` 可以满足 schema，但不能交接；使用 `--ready` 区分“结构合法”和“可进入下一阶段”。

## 公开语料与 Golden Regression Suite

完整 100 篇公开机器人论文索引是本地离线构建输入，不提交 Git；正常 Skill 只读取轻量化的 `corpus/robotics-research-runtime.v1.json`。v2 全文路径只跟踪可审计收据：

- `public-paper-fulltext-manifest.v1.json`：100 篇来源、缓存哈希和版本关系；当前 81 篇本地缓存、19 篇公开网页全文收据，合计 100/100 可用全文；
- `public-paper-text-coverage.v1.json`：78 篇具有可识别章节、3 篇文本不完整、19 篇无本地全文；
- `robotics-research-runtime.v1.json`：按八个研究子流形轴提取的紧凑论文先例、轴策略、15/31 模式系统摘要和非主张边界；
- `researchstudio-pattern-induction.v2.json`：模型模拟聚类审计后的 15/31 可复用模式；
- `robotics-axis-strategy-analysis.v2.json`：八轴问题、能力簇路由和需要实时刷新的 venue 候选；
- `researchstudio-outcome-contrast.v1.json`：因没有 decision-aligned 数据而正式关闭 outcome 对照，不伪造录用结论。

原始索引、论文级 signatures、PDF、抽取文本、embedding、模型子代理中间 JSON 和临时下载均为本地离线输入/缓存并被 `.gitignore` 排除；GitHub 只保存 runtime、公开收据、生成器、验证器和 Skill 知识。`corpus/golden/synthetic-cases.json` 使用完全合成的研究案例测试：

- 完整正向路径；
- writing-only 导入；
- 人体数据层级；
- 软体机器人批次与疲劳边界；
- 工业运行与安全边界；
- 近期先例碰撞后的 `ABANDON`。

公开奖项和社区复用记录只用于发现值得分析的论文，不代表某项主张已经获得充分证据。

所有版本化 corpus artifact 的路径必须是仓库相对 POSIX 路径；若输入来自仓库外，生成器只记录内容 SHA-256，不记录 `E:`、`/mnt`、`/home` 等主机路径。`scripts/check_portable_corpus_paths.py` 会在发布检查中阻止这类污染。

## 仓库结构

```text
Robotics-Research-Skill/
├── skills/                  # 六个并列、可独立安装的 Skill（robotics-ar 可选编排）
├── common/                  # 严格 JSON、ID、摘要、证据画像和判定规则
├── references/              # 三个共享运行说明与可审计来源 receipt
├── assets/                  # project manifest 与 target snapshot 模板
├── corpus/                  # 公开论文索引与合成 Golden Suite
├── scripts/                 # 日常路由、安装、统一检查与项目级验证入口
├── tools/corpus/            # 不进入运行时的离线语料构建与审计工具
├── archive/legacy-v1/       # 不进入安装的历史迁移与追溯文件
├── schemas/                 # 安装回执等语言中立 schema
├── tests/                   # 跨阶段与双语检查
├── SOURCE_SNAPSHOTS.json    # 上游来源快照
├── THIRD_PARTY_NOTICES.md   # 第三方声明
└── LICENSE                  # MIT
```

## 测试与发布检查

```bash
python3 scripts/run_all_checks.py
```

统一入口执行并列 Skill 的单元测试、安装模式回归测试、跨阶段合同检查和双语布局检查。发布前还建议执行密钥、隐私标识、缓存文件和未替换占位符扫描。

## 隐私与数据原则

- 仓库不包含用户私人项目名称、缩写、机制或实验数据；
- Golden Suite 只使用公开论文和完全合成案例；
- 不复制受版权保护的论文正文；
- 搜索日志应记录来源和截止日期；
- 用户项目的真实日志、结果和稿件默认保留在用户自己的项目目录中。

## 来源与许可证

方法设计吸收了 ResearchStudio、Academic Research Skills、机器人会议/期刊工作流和部分高影响科学写作工具中的通用逻辑，并针对工程系统剔除了不适用的自然科学假设。具体来源快照见 `SOURCE_SNAPSHOTS.json`，许可证与第三方声明见 `LICENSE` 和 `THIRD_PARTY_NOTICES.md`。

## 来源与引用

以下项目是本仓库进行方法阅读、能力蒸馏或接口对照时参考的公开来源；它们不是本仓库的运行时依赖，也不表示任何投稿结果、质量排名或录用概率。

- [ARIS / auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/auto-claude-code-research-in-sleep)：仅蒸馏领域中立的生命周期、门禁、receipt、追踪、隔离和暂停恢复能力；固定参考 commit 为 `3e49e63aae6a653067f9e2101d50457f1f7d6a2f`。
- [HKUSTDial/Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills)：参考监督、阶段编排和人工检查点的组织方式。
- [ResearchStudio](https://arxiv.org/abs/2607.04439)：参考从公开研究结果中提取可解释研究策略的分析思路；本仓库保留其“描述性分析而非录用模型”的边界。
- [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills-codex)：参考学术检索、阅读、写作和审阅的可复用工作流。
- [Awesome-Journal-Skills](https://github.com/brycewang-stanford/Awesome-Journal-Skills)：参考跨会议/期刊的投稿准备和 venue-specific workflow 组织方式；本仓库将共同不变量压缩为一套方法，不复制十套内部 Skill。
- [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills)：参考文献检索、引用核验、数据记录、图表和论文准备等可审计步骤。
- 公开可搜索到的会议和期刊论文、官方范围页面及作者公开版本：作为机器人研究子流形、先例碰撞、证据需求、写作和 venue 路由的分析语料库。语料库和奖项/演示记录只用于发现与描述性比较，不代表录用概率、质量排名，也不能推出统计因果结论。

引用这些来源时，请同时阅读上游项目当前的许可证、版本和官方政策；本仓库只保留必要的归属、内容哈希和能力边界。

本项目采用 MIT License。

---

# English

## Robotics Research Skill

## Overview

Robotics Research Skill is a unified package with an **Idea → Experiment → Writing** backbone. The backbone is extensible: literature search, prior-work collision checks, legacy-project migration, experiment auditing, artifact packaging, reproducibility, LaTeX auditing, and submission-time claim checks are also supported. It is not a collection of outlet-specific prompts and does not derive scientific requirements from a static venue hierarchy.

The package supports embodied systems, control, learning, bio-inspired robotics, soft robotics, human interaction, industrial automation, field systems, and multi-robot research. Target information affects packaging and submission constraints only; it never rewrites the scientific contract.

The current runtime-first v2 path is built offline from a balanced 100-paper
corpus. The raw index, paper-level signatures, PDFs, extracted text, and
embedding caches are local-only. The tracked
corpus/robotics-research-runtime.v1.json is the only paper-derived artifact
read by normal Skill routing; it contains compact exemplars, eight axis
strategy rows, 15 parent patterns, 31 subpatterns, and eight routing
questions. This is explicitly not statistical PCA, real UMAP/HDBSCAN, or an
acceptance model. Ten external venue workflows are distilled into one
reusable method plus venue mappings, not copied into ten internal workflows.

The repository also contains an explicitly enabled, fifth sibling Skill,
`robotics-ar`. It distills domain-neutral lifecycle, evidence-gate, artifact,
trace, isolation, and pause/resume contracts from ARIS
([auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/auto-claude-code-research-in-sleep)),
pinned to commit `3e49e63aae6a653067f9e2101d50457f1f7d6a2f`. ARIS is not a
runtime dependency; provider, MCP, UI, ML, paper, and venue workflows are
excluded. The receipt and audit records live under
`agent/robotics-ar-distillation/`, with license attribution in
`THIRD_PARTY_NOTICES.md`.

## Atomic-skill backbone

- `develop-robotics-idea` builds or audits a falsifiable Research Card, checks prior-work collisions, establishes claim boundaries, and preserves an immutable candidate–audit–patch chain.
- `design-robotics-experiment` converts a locked claim into conditions, contrasts, metrics, unit hierarchies, negative controls, denominator policies, and mechanically executable decision rules.
- `develop-robotics-engineering` executes scoped control, optimization, perception, learning, ROS, embedded, simulation, hardware-interface, deployment, and tuning changes with a minimal plan, frozen focused tests, and cross-validated plan/task/report/handoff artifacts.
- `write-robotics-paper` builds a traceable Claim Ledger and LaTeX manuscript without upgrading evidence states or inventing experiments, numbers, or citations.
- `review-robotic-feedback` runs seven fresh, scope-isolated robotics reviewer perspectives and a source-linked Meta Review with a revision roadmap. It requires an explicit output language and stores every run below an independent `reviews/review-<timestamp>/{jsons,markdowns}/` directory.

## Key guarantees

- Claim, design, and operational changes have separate governance.
- Evidence is represented component-wise rather than collapsed into one total order.
- Target-fit metadata is stored separately from the scientific lock.
- Trial registration and long-format measurement logs preserve robot, participant, demonstration, session, and trial nesting.
- Structured rules produce `SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE` deterministically.
- Stopping states are first-class outputs.
- Existing projects can enter through audit, migration, micro-adjustment, or writing-only modes.
- Review cycles can be re-run in `re-review` mode against a prior roadmap and revised manuscript.

## Quick start

Python 3.8 or newer is required. The core tools use only the standard library.
All structured artifacts may use JSON. PyYAML is an optional dependency only
when you provide `.yaml` or `.yml` input files:

```bash
python3 -m pip install PyYAML
```

If you use JSON inputs, PyYAML is not required and the runtime never installs
dependencies from the network.

```bash
git clone <your-repository-url>
cd Robotics-Research-Skill
python3 scripts/run_all_checks.py
python3 scripts/run_all_checks_corpus_first.py
```

Example invocations:

```text
Use $develop-robotics-idea to audit this robotics direction and create a V2 Research Card.
Use $design-robotics-experiment to turn the locked claim into a structured experiment contract.
Use $write-robotics-paper to build a traceable LaTeX paper from the frozen results.
Use $review-robotic-feedback to review a robotics paper and produce a traceable Meta Review and revision roadmap.
Use $robotics-ar only when explicitly requested to start a gated, resumable cross-stage research session.
```

Templates live in each skill's `assets/` directory. A `null` template value is an unresolved scientific decision, not a valid answer.

Scripts are separated into normal runtime, installation/maintenance, offline corpus
build, and compatibility/migration layers. See [`scripts/README.md`](scripts/README.md)
for the complete inventory and staged-runtime copy boundary.

### Robot-AR v3 Midstream Takeover

Robot-AR v3 preserves the v2 `NEW_RESEARCH` lifecycle and adds
`MIDSTREAM_TAKEOVER` for a robotics project that already has code, experiment
history, an executable environment, and a local bottleneck. Before autonomous
trials, the project must have a Project Core, reconstructed history, an online
environment receipt, a reproduced baseline, and a user-approved Trial Contract.
The contract binds search tiers, paths, metrics, budgets, and stop/escalation
conditions. A Tier 3 method or claim pivot, primary-metric or data-protocol
change, or real-robot safety-limit change pauses for the user.

Each checkpoint, pause, block, and correction updates `report.md`, `handoff.md`,
and task artifacts; a correction also writes `.robotics-ar/tasks/task.md` while
keeping a root compatibility copy. Real-robot execution requires a single
operator-bound token per batch; failures stop and are never retried. Example
intake, contract, report, handoff, and task artifacts are in
`skills/robotics-ar/assets/`.

The takeover CLI sequence is `takeover-record-intake`, `takeover-audit`,
`takeover-import-history`, environment validation, baseline compile/run,
contract compile/approve, trial proposal, and batch start. If a baseline cannot
be reproduced, `baseline-recover --diagnostics` records bounded diagnostics only;
it does not manufacture evidence. `batch-resume` rechecks the contract,
environment receipt/fingerprint, elapsed wall-time, and terminal stop reason.
`trial-analyze` requires raw evidence plus versioned metrics. Proposal and queue
state hashes, raw-evidence receipts, decision receipts, and checkpoints remain
auditable; concluded trials enter Do-Not-Repeat, and a single seed cannot become
stable Best-Known State automatically.

## Installation modes and local updates

The repository ships one installer for six sibling Skills: four scientific evidence Skills, independently usable `develop-robotics-engineering`, and optional orchestrator `robotics-ar`. Robotics-AR may invoke Engineering when present but falls back to its Code/Test/Runner protocol when absent. `--skills all` discovers all available Skills automatically.

The `--mode auto` choice follows the declared purpose:

| Purpose | Default mode | Behavior |
| --- | --- | --- |
| `development` | `SYMLINK_TRACKED_CLONE` | Links each Skill from a local Git clone into `$CODEX_HOME/skills`; local branch changes, working-tree edits, and commits are immediately visible without reinstalling. |
| `use` with `--source-root` | `SAFE_STAGED_WORKTREE` | Builds a commit-addressed release snapshot, copies the active runtime dependency closure, and switches Skill links atomically; updates check the branch, clean worktree, fast checks, and fast-forward relation. |
| `use` with `--archive-url` | `DIRECT_DOWNLOAD` | Creates an immutable staged release from lightweight `runtime.zip`, pins it by archive SHA-256, preserves shared runtime, and links selected Skills to that snapshot. |

For active development:

```bash
git clone git@github.com:YakarifromCN/Robotics-Research-Skill.git
cd Robotics-Research-Skill
python3 scripts/install_local_skills.py \
  --source-root "$PWD" \
  --purpose development
```

For normal use from a local clone, choose the staged mode explicitly:

```bash
python3 scripts/install_local_skills.py \
  --source-root /path/to/Robotics-Research-Skill \
  --purpose use \
  --mode SAFE_STAGED_WORKTREE
```

Build formal release assets only from a clean worktree. The builder emits a sub-5 MiB `dist/runtime.zip` and sub-20 MiB `dist/developer.zip`, excluding PDFs, `.git`, `agent/`, extracted corpora, and bytecode:

```bash
python3 scripts/build_release_bundle.py
```

For a pinned remote archive:

```bash
python3 scripts/install_local_skills.py \
  --archive-url https://github.com/YakarifromCN/Robotics-Research-Skill/releases/latest/download/runtime.zip \
  --purpose use \
  --mode DIRECT_DOWNLOAD
```

The default destination is `${CODEX_HOME:-$HOME/.codex}/skills`; override it with `--dest`. `--skills all` installs every discovered sibling Skill, while a comma-separated list selects a subset. The installer never overwrites an existing directory; `--replace-owned-symlink` is required to replace a symlink created by this installer.

If a Robotics-AR session root is already known, repeat `--active-session-root /path/to/session` during installation. A tracked update is blocked while that root contains `.robotics-ar/session.lock`.

Each installation writes `.robotics-research-install.json` in the destination. The receipt records the mode, purpose, source clone, branch, commit, Skill-file hashes, archive hash, and update policy. It does not record manuscript contents, experiment data, or a whole-workspace snapshot.

Refresh a tracked clone and run fast checks with:

```bash
python3 scripts/update_local_skills.py \
  --install-receipt "$HOME/.codex/skills/.robotics-research-install.json" \
  --ff-only \
  --fetch \
  --run-fast-checks
```

Use `--no-fetch` when the desired remote refs are already available locally. `SAFE_STAGED_WORKTREE` copies and checks a new release directory before switching links; branch divergence, uncommitted changes, an active `.robotics-ar/session.lock`, or failed checks stop the update. `SYMLINK_TRACKED_CLONE` remains live by design: the installed links reflect the local branch immediately. `DIRECT_DOWNLOAD` and `COPY_PINNED` are pinned snapshots and are not auto-updatable.

Diagnose drift with:

```bash
python3 scripts/doctor_local_skills.py \
  --install-receipt "$HOME/.codex/skills/.robotics-research-install.json"
```

The doctor reports `PASS`/`FAIL`, link drift, Skill-file digest changes, source-clone availability, and the current HEAD. It never scans a manuscript PDF, a LaTeX workspace, or the user's general project workspace.

## Artifact flow

```text
Research Card → Experiment Contract → Trial/Measurement Logs
              → Result Bundle → Claim Ledger → Audited LaTeX

Target Fit Snapshot → packaging and submission constraints only
Project Manifest    → deterministic artifact index only
```

Artifacts reference upstream scientific objects through stable IDs and canonical SHA-256 digests. The target snapshot can be refreshed during writing without invalidating the scientific claim.

## Evidence and experiment model

Claim Shape, explicit Evidence Obligations, and conditionally loaded Domain Packs form the scientific model. Evidence requirements separately describe regime, coverage, duration, independence, experimental unit, unit count, and site count.

The experiment contract freezes conditions, metrics, contrasts, exclusions, denominators, abort handling, and decision rules before outcomes are interpreted. Complex external analyses must bind both scripts and outputs by SHA-256.

## Public corpus and regression cases

The offline corpus pipeline retains full-text receipts and model-simulated
ResearchStudio analysis as auditable build inputs. Runtime consumes only the
derived summary and preserves the boundaries that the pattern analysis is
descriptive, not a statistical factor fit or acceptance estimate. Public
awards and community adoption are discovery signals only.

The raw index, paper-level signatures, PDFs, extracted text, embeddings,
model-subagent intermediates, and temporary downloads remain ignored local
caches. GitHub contains the compact runtime, public manifests, provenance
receipts, generators, validators, and reusable Skill knowledge. Synthetic
golden cases exercise the end-to-end contracts without exposing user data.

Versioned corpus artifacts may use repository-relative POSIX paths only. For input outside the repository, the generator stores a content SHA-256 reference instead of `E:`, `/mnt`, `/home`, or another host path. `scripts/check_portable_corpus_paths.py` runs as part of the release checks.

## Validation

Run the complete local suite with:

```bash
python3 scripts/run_all_checks.py
python3 scripts/run_all_checks_corpus_first.py
```

The command runs the sibling skill test suites, the installation-mode regression tests, cross-stage contract checks, and bilingual-layout validation. Each skill can also be validated independently with the scripts documented in its `SKILL.md`.

## Privacy

This repository contains no private user projects or experimental data. Regression cases are synthetic, public sources are referenced by metadata and URLs, and real project artifacts remain in the user's own project workspace.

## Sources and references

The following public projects were read as method, distillation, or interface references. They are not runtime dependencies of this repository and do not imply an outcome, quality judgment, or acceptance-probability estimate:

- [ARIS / auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/auto-claude-code-research-in-sleep): only domain-neutral lifecycle, gate, receipt, trace, isolation, and pause/resume ideas were distilled; the pinned commit is `3e49e63aae6a653067f9e2101d50457f1f7d6a2f`.
- [HKUSTDial/Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills): supervision, stage orchestration, and human-checkpoint organization.
- [ResearchStudio](https://arxiv.org/abs/2607.04439): interpretable research-strategy analysis from public outcomes, with the boundary that this is descriptive rather than an acceptance model.
- [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills-codex): reusable academic search, reading, writing, and review workflows.
- [Awesome-Journal-Skills](https://github.com/brycewang-stanford/Awesome-Journal-Skills): cross-venue submission preparation and workflow organization; shared invariants are consolidated here instead of copied into ten internal Skills.
- [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills): auditable literature search, citation verification, data logging, figures, and paper-preparation steps.
- Publicly searchable conference and journal papers, official scope pages, and author-posted versions: an analysis corpus for robotics research-submanifold axes, prior-work collision checks, evidence obligations, writing, and venue routing. Corpus and award/presentation records are discovery and descriptive-comparison inputs only; they do not encode acceptance probability or quality judgments and cannot support statistical causal conclusions.

Please check each upstream project's current license, version, and official policy when reusing a source. This repository keeps only necessary attribution, content hashes, and explicit capability boundaries.

## License and attribution

Released under the MIT License. See `SOURCE_SNAPSHOTS.json` for reproducible upstream snapshots and `THIRD_PARTY_NOTICES.md` for attribution details.
