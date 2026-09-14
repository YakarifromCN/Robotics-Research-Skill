# Robotics Research Skill

## 中文

Robotics Research Skill 为机器人科研提供六个并列 Skill：研究构思、实验设计、工程实现、论文写作、同行评审，以及显式开启的自动研究编排。你可以只使用其中一个，也可以通过稳定 ID 和证据工件衔接多个阶段。

它根据研究主张、资源、风险和证据缺口选择工作深度。目标会议或期刊用于调整读者定位、篇幅与提交格式，不决定科学主张。适用领域包括控制、学习、感知、硬件、仿生、软体机器人、人机交互、工业自动化、现场系统和多机器人；相关载体包括 SII、Humanoids、ROBIO、AIM、ICRA、IROS、RA-L、RAP、T-RO、IJRR、RSS、CoRL、CASE、RoboSoft、Soft Robotics 和 Science Robotics 等。具体投稿政策仍需在使用时向官方核验。

缝合了很多好用的开源科研skill，还会继续缝合。

### 选择 Skill

| Skill | 适合的任务 | 主要产物 |
| --- | --- | --- |
| `develop-robotics-idea` | 构思、先例碰撞、既有主张审计或迁移 | Research Card、证据来源、候选审计链 |
| `design-robotics-experiment` | 条件、基线、指标、分母、统计与结果封装 | Experiment Contract、试验与测量表、Result Bundle |
| `develop-robotics-engineering` | 控制、优化、ROS、学习、部署等代码任务 | 代码、聚焦测试、Plan/Task/Report/Handoff |
| `write-robotics-paper` | 起草、仅写作、修订、rebuttal 与主张审计 | Claim Ledger、LaTeX 稿件、修订审计 |
| `review-robotic-feedback` | 在指定稿件范围内进行多视角同行评审 | 专项报告、Meta Review、修改路线 |
| `robotics-ar` | 用户明确要求的跨阶段自动研究或中途接管 | 批准、执行与结果回执、暂停恢复工件 |

Engineering 不替代实验设计；Writing 不自动新增实验；Review 不获得整个项目的访问权。Robotics-AR 是可选编排器，其他 Skill 不依赖它启动。

### 安装

从仓库克隆后安装：

```bash
git clone https://github.com/YakarifromCN/Robotics-Research-Skill.git
cd Robotics-Research-Skill
python3 scripts/install_local_skills.py --source-root "$PWD" --purpose use
```

安装目标默认为 `${CODEX_HOME:-$HOME/.codex}/skills`。可用 `--dest` 指定目录，或用 `--skills write-robotics-paper,review-robotic-feedback` 选择子集。安装器不覆盖已有用户目录。

| 模式 | 适用情况 | 更新方式 |
| --- | --- | --- |
| `SYMLINK_TRACKED_CLONE` | 参与开发；`--purpose development` 的默认值 | 安装链接即时反映本地工作树修改 |
| `SAFE_STAGED_WORKTREE` | 从 clone 使用；`--purpose use` 的默认值 | 用户触发更新，检查后切换版本快照 |
| `DIRECT_DOWNLOAD` | 从发行包使用 | 归档摘要固定；新版本由用户重新选择 |
| `COPY_PINNED` | 固定版本使用 | 固定目录投影，内部链接到同一运行闭包；不自动更新 |

开发安装：

```bash
python3 scripts/install_local_skills.py --source-root "$PWD" --purpose development
```

若发行页提供了 `runtime.zip`，可安装该归档：

```bash
python3 scripts/install_local_skills.py \
  --archive-url https://github.com/YakarifromCN/Robotics-Research-Skill/releases/latest/download/runtime.zip \
  --purpose use --mode DIRECT_DOWNLOAD
```

手动更新与检查：

```bash
python3 scripts/update_local_skills.py \
  --install-receipt "$HOME/.codex/skills/.robotics-research-install.json" \
  --ff-only --fetch --run-fast-checks
python3 scripts/doctor_local_skills.py \
  --install-receipt "$HOME/.codex/skills/.robotics-research-install.json"
```

自定义安装目录时相应修改回执路径。更新不作为每次 Skill 调用的前置步骤。跟踪开发 clone 会即时暴露未提交改动；希望稳定使用时选择 staged 模式。目录投影依赖符号链接；进程清理与写锁的新增实现面向 POSIX，其他平台不能假定具有同样保障。共享文件系统需要另行验证锁语义。

### 依赖与轻量运行

核心 JSON 工具使用 Python 3.8+ 标准库。多行 YAML 或 YAML 工件需要可选 PyYAML：

```bash
python3 -m pip install PyYAML
```

Engineering 同时支持 JSON 工件和 YAML frontmatter。工具不会在运行时联网安装依赖。

Writing 每次起草或修改正文都执行 Humanizer 的标记、改写和复查。它优先使用兼容的本地 Humanizer，否则读取随包发布的轻量学术适配；适配有版本、摘要和许可证，不需要额外下载。该步骤清理冗余和模板化表达，保留公式、数字、引用、技术定义、必要限定和作者风格。依赖解析成功不等于已经完成语言审阅。

普通调用不读取原始论文、PDF、embedding 缓存或历史会话。论文相关信息来自紧凑的 `corpus/robotics-research-runtime.v1.json`，配合当前路由模型、模式卡和载体目录。离线构建工具与历史归档不进入普通安装。资源边界见 [corpus/README.md](corpus/README.md) 和 [scripts/README.md](scripts/README.md)。

在其他项目目录调用脚本时，使用已安装 Skill 的绝对路径；文档中的 `<installed-skill-dir>` 指包含该 Skill 的 `SKILL.md` 的目录，不是稿件目录。

### 使用示例

```text
使用 $develop-robotics-idea 审计这个方向；如果已有工作覆盖核心机制，允许停止。
使用 $design-robotics-experiment 设计实验，冻结分母、排除规则和主指标。
使用 $develop-robotics-engineering 执行这份已批准任务，只修改指定代码。
使用 $write-robotics-paper 修改这份稿件，只改写作，不新增实验。
使用 $review-robotic-feedback 审阅 paper.pdf，目标语言为 en+zh。
使用 $robotics-ar 接管现有项目，在批准的预算与范围内推进。
```

既有项目可以从审计、微调实验、结果导入或仅写作进入。模板中的 `null` 表示待解决的问题，不代表有效科研判断。

### 主张与证据如何衔接

```text
Research Card → Experiment Contract → Trial Registry + Measurement Log
             → Result Bundle → Claim Ledger → Manuscript

Target Fit Snapshot → 读者、篇幅和提交格式
Project Manifest    → 阶段与工件索引
```

科学对象描述主张形态、证据义务和按需领域规则。Claim Lock 固定科学主张与反证对象；Design Lock 固定实验条件、指标和分析规则；校准、人员和日志位置等操作细节可以记录理由后细化。

证据分别描述运行条件、覆盖范围、持续时间、独立性和实验单位。仿真、实机、现场、跨条件和独立复现的充分性按主张逐项判断，不合并成一个总分。参与者、示范、机器人、session 和 trial 的层级必须保留。

结构化规则可机械计算 `SUPPORTED`、`NOT_SUPPORTED` 或 `INCONCLUSIVE`。复杂分析必须绑定脚本和结果摘要。写作不能把不确定结果升级为支持结论，也不应把充分支持的贡献改成不必要的自我削弱。

Trial Registry 每次尝试一行；Measurement Log 保存指标、阶段与窗口。abort policy 在合同中冻结，包括计为失败、保留在分母或仅排除事先声明的硬件故障。负对照以稳定变量和条件 ID 表达，能够检验基线回归、反向效应、通道损失和替代机制。

`DO_NOT_GENERATE`、`ABANDON`、`NO_RUN`、`CHANGE_REQUEST_TO_IDEA` 和 `EVIDENCE_GAPS` 都是合法输出。`--ready` 用于区分结构有效与可交接；工具通过不等于科学结论自动成立。

### 论文评审

启动评审时明确指定任意单语或 `en+任意语言`。评审只读取指定 PDF，或发现快照列出的 LaTeX 文件。子代理采用新稿件上下文，不继承项目记忆，也不访问未列出的工作区文件。

按稿件需要组合 proofreading、contribution calibration、robotics contribution、control/optimization、robot learning、hardware、evidence audit 和 venue compliance，随后由 meta-review 汇总。专项采用 1–5 分，分数不能代替证据判断或转换为录用概率。

```text
reviews/
  review-<YYYYMMDDHHMM>/
    markdowns/
    jsons/
```

重复运行使用独立时间戳目录。原始论文审稿与作者提供旧意见后的修订核对是不同任务，应明确选择模式。

### 自动模式与故障恢复

Robotics-AR 支持 `NEW_RESEARCH` 和 `MIDSTREAM_TAKEOVER`。先核对项目核心、历史、环境和基线，再在批准的合同中执行；研究方向、主要指标或真实设备权限变化需要新的用户决定。

```bash
python3 skills/robotics-ar/scripts/robotics_ar.py init \
  --project-root /path/to/project --entry-mode MIDSTREAM_TAKEOVER --mode EXECUTION_ENABLED
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-init --project-root /path/to/project
python3 skills/robotics-ar/scripts/robotics_ar.py doctor --project-root /path/to/project
```

审计默认有文件数、内容字节和扫描时间上限。达到上限会返回 `PARTIAL`，不是完整通过；CLI 输出摘要和产物位置。审计要求的 reconciliation 不能在历史导入阶段取消。基线需要先 `baseline-compile`，再 `baseline-select --reason ...`；执行前还需要绑定批准与预算的 reservation。

`reserve-execution`、`start-execution` 和 `register-external-execution` 分别登记预留、启动和结果；`import-execution` 只导入回顾性证据，不补造执行授权。启动记录阻止同一执行被直接重跑，lease token 限制过期写者。外部进程的实际运行仍由相应环境负责，不能由本地回执宣称分布式 exactly-once。未知运行状态必须先核对。

事件追加使用单机协作锁；已提交的状态转移可恢复中断的状态投影。历史事件损坏由 doctor 诊断，不自动重排。终态 resume 不重复启动工作。多仓库恢复可通过显式授权的文件快照核对内容；未提供快照时保留原有 Git 清洁检查。

自动执行尚需针对用户环境验收，尤其是跨主机租约、共享盘锁和真实设备。它不能仅凭单元测试标为稳定。默认不开启遥测；`--invocation-receipt` 只记录本地 CLI 调用的有限元数据，不记录 prompt 或命令参数。

### 常用验证

从仓库根目录运行：

```bash
python3 skills/develop-robotics-idea/scripts/validate_research_card.py research-card.json --ready
python3 skills/design-robotics-experiment/scripts/validate_experiment_contract.py experiment-contract.json --card research-card.json --ready
python3 skills/design-robotics-experiment/scripts/validate_result_bundle.py result-bundle.json experiment-contract.json --ready
python3 skills/write-robotics-paper/scripts/validate_claim_ledger.py claim-ledger.json --result result-bundle.json --card research-card.json --ready
python3 skills/write-robotics-paper/scripts/render_numbers.py manuscript.tex claim-ledger.json --output manuscript.rendered.tex
python3 skills/write-robotics-paper/scripts/audit_latex.py manuscript.rendered.tex claim-ledger.json
python3 -B scripts/run_stable_checks.py
```

语言修订可另用 `audit_prose_invariants.py before.txt after.txt` 检查数量、引用、数学片段和状态变化。这是机械差异检查，仍需人工核对语义。

发布版本由 `VERSION` 管理。正式发行前运行完整检查，再从干净 checkout 构建：

```bash
python3 scripts/build_release_bundle.py
```

发布构建器要求 `runtime.zip` 小于 5 MiB、`developer.zip` 小于 20 MiB，并排除本地会话、PDF、缓存和 Git 元数据。未执行的检查记录为 `NOT_RUN`。

### 仓库与来源

| 目录 | 内容 |
| --- | --- |
| `skills/` | 六个 Skill 的入口、脚本和按需参考 |
| `common/`、`assets/`、`schemas/` | 共享合同、模板、摘要和结构化校验 |
| `corpus/` | 紧凑运行资源、公开来源收据、合成回归样例 |
| `scripts/` | 路由、安装、验证和发布 |
| `tools/corpus/` | 维护者显式使用的离线构建工具 |
| `archive/` | 仅供历史追溯；不进入运行依赖 |
| `tests/` | 跨阶段、安装与轻量运行回归 |

原始论文与个人项目数据留在用户自己的工作区。公开 Golden Suite 使用合成案例和公开来源；它检验工作流，不证明 Skill 已提升科研成果。模型辅助的策略归纳不等于真实 embedding、UMAP/HDBSCAN 或录用预测。

方法参考包括 [ResearchStudio](https://arxiv.org/abs/2607.04439)、[Academic Research Skills](https://github.com/Imbad0202/academic-research-skills-codex)、[Awesome-Journal-Skills](https://github.com/brycewang-stanford/Awesome-Journal-Skills)、[ARIS](https://github.com/wanshuiyin/auto-claude-code-research-in-sleep)、[Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills)、[nature-skills](https://github.com/Yuan1z0825/nature-skills) 和 [Humanizer](https://github.com/blader/humanizer)。通用科研与写作方法经过机器人任务适配，外部项目整体不是运行依赖。

本项目采用 [MIT License](LICENSE)。来源快照见 [SOURCE_SNAPSHOTS.json](SOURCE_SNAPSHOTS.json)，第三方归属与适配许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

# English

## Robotics Research Skill

This repository provides six sibling Skills for robotics research: ideation, experiment design, engineering, writing, peer review and explicitly requested autonomous orchestration. Use them independently or connect stages through stable IDs and evidence artifacts.

Research claims, resources, risks and evidence gaps determine the work needed. Target venues affect readership, length and submission requirements without rewriting the scientific claim. The framework covers control, learning, perception, hardware, bio-inspired and soft robotics, human interaction, industrial automation, field systems and multi-robot research. Relevant outlets include SII, Humanoids, ROBIO, ICRA, IROS, RA-L, RAP, T-RO, IJRR, RSS, CoRL, CASE, RoboSoft, Soft Robotics and Science Robotics. Verify submission policies with current official sources.

## Choose a Skill

| Skill | Task | Main output |
| --- | --- | --- |
| `develop-robotics-idea` | Ideation, prior-work collisions, adoption or migration | Research Card and candidate audit chain |
| `design-robotics-experiment` | Conditions, comparators, metrics, denominators and analysis | Experiment Contract, trial logs and Result Bundle |
| `develop-robotics-engineering` | Scoped implementation and focused testing | Code and Plan/Task/Report/Handoff |
| `write-robotics-paper` | Drafting, writing-only revision, rebuttal and claim audit | Claim Ledger, manuscript and revision audit |
| `review-robotic-feedback` | Manuscript-scoped specialist review | Specialist reports, Meta Review and revision roadmap |
| `robotics-ar` | Explicit cross-stage automation or project takeover | Approvals, execution receipts and resumable state |

Engineering does not substitute for scientific experiment design. Writing does not authorize new experiments. Review does not grant access to a whole project. Robotics-AR is optional.

## Install and update

```bash
git clone https://github.com/YakarifromCN/Robotics-Research-Skill.git
cd Robotics-Research-Skill
python3 scripts/install_local_skills.py --source-root "$PWD" --purpose use
```

The default destination is `${CODEX_HOME:-$HOME/.codex}/skills`. Use `--dest` to override it and `--skills` with comma-separated names to select a subset. Existing user directories are not overwritten.

| Mode | Intended use | Updates |
| --- | --- | --- |
| `SYMLINK_TRACKED_CLONE` | Default for `--purpose development` | Local working-tree changes become immediately visible |
| `SAFE_STAGED_WORKTREE` | Default for use from a clone | User-triggered, checked snapshot switches |
| `DIRECT_DOWNLOAD` | Released archive | Fixed archive digest; explicitly choose another version |
| `COPY_PINNED` | Fixed version | Directory projection with internal links to the same runtime closure |

For development, replace `--purpose use` with `--purpose development`. If a release provides `runtime.zip`, it can be installed without a development clone:

```bash
python3 scripts/install_local_skills.py \
  --archive-url https://github.com/YakarifromCN/Robotics-Research-Skill/releases/latest/download/runtime.zip \
  --purpose use --mode DIRECT_DOWNLOAD
python3 scripts/update_local_skills.py \
  --install-receipt "$HOME/.codex/skills/.robotics-research-install.json" \
  --ff-only --fetch --run-fast-checks
python3 scripts/doctor_local_skills.py \
  --install-receipt "$HOME/.codex/skills/.robotics-research-install.json"
```

Adjust receipt paths for custom destinations. Updates are not a prerequisite for every invocation. Development links expose uncommitted changes; staged mode is preferable for fixed use. Directory projections require symlinks. The new process cleanup and writer lock target POSIX; shared filesystems need separate lock qualification.

## Dependencies and lightweight runtime

Core JSON tools use Python 3.8+ and its standard library. YAML input and multiline Engineering frontmatter require optional PyYAML:

```bash
python3 -m pip install PyYAML
```

Engineering also accepts JSON artifacts. Runtime never installs dependencies from the network.

Writing performs Humanizer's mark, rewrite and recheck pass for drafting and prose revision. It resolves a compatible installed version or the bundled, versioned academic adaptation. Preserve equations, numbers, citations, definitions, necessary qualifications and author voice. Resolving the dependency does not complete the language pass.

Normal invocation does not load raw papers, PDFs, embeddings or session history. Paper-derived context comes from the compact `corpus/robotics-research-runtime.v1.json`, together with the current routing model, pattern cards and venue catalog. Offline tooling and historical archives are excluded from normal installs. See [corpus/README.md](corpus/README.md) and [scripts/README.md](scripts/README.md).

From another working directory, call the installed script by absolute path. `<installed-skill-dir>` means the directory containing that Skill's `SKILL.md`, not the manuscript directory.

## Use and evidence flow

Ask for one Skill and its intended scope, for example: “Use $write-robotics-paper to revise this manuscript; prose only, no new experiments.” Existing projects can enter through audit, limited experimental adjustment, result import or writing-only modes. Template nulls represent unresolved decisions.

```text
Research Card → Experiment Contract → Trial Registry + Measurement Log
             → Result Bundle → Claim Ledger → Manuscript
Target Fit Snapshot → readership, length and submission format
Project Manifest    → stage and artifact index
```

Claim Shape, Evidence Obligations and on-demand Domain Packs describe the scientific object. Claim Lock preserves scientific claims and falsification targets; Design Lock preserves experimental conditions and analysis rules. Operational details can be refined with recorded reasons.

Evidence separately records regime, coverage, duration, independence and experimental units. Preserve participant, demonstration, robot, session and trial nesting. Structured rules can derive `SUPPORTED`, `NOT_SUPPORTED` and `INCONCLUSIVE`; external analyses bind scripts and results by digest. Writing must neither upgrade uncertainty nor unnecessarily weaken supported contributions.

The Trial Registry records every attempt; the Measurement Log records metrics, phases and windows. Freeze abort handling in the contract. Negative controls use stable variable and condition IDs to test baseline return, reversed effects, channel loss or alternative mechanisms.

`DO_NOT_GENERATE`, `ABANDON`, `NO_RUN`, `CHANGE_REQUEST_TO_IDEA` and `EVIDENCE_GAPS` are valid outcomes. Use `--ready` to distinguish structural validity from handoff readiness. Passing a validator does not establish a scientific conclusion.

## Peer review

Specify any output language or `en+another language`. Reviewers read only the supplied PDF or the allowed files in a LaTeX discovery snapshot. Fresh reviewer contexts do not inherit project memory.

Select relevant proofreading, contribution-calibration, robotics-contribution, control/optimization, learning, hardware, evidence and venue-compliance perspectives, then synthesize a Meta Review. Specialist scores use a 1–5 scale and do not estimate acceptance probability. Each run writes `reviews/review-<YYYYMMDDHHMM>/{markdowns,jsons}/`. Distinguish fresh review from author-requested comparison with previous feedback.

## Automatic mode and recovery

Robotics-AR supports `NEW_RESEARCH` and `MIDSTREAM_TAKEOVER`. Verify the project core, history, environment and baseline before executing an approved contract. Changes to research direction, primary metrics or device authority require a new user decision.

```bash
python3 skills/robotics-ar/scripts/robotics_ar.py init \
  --project-root /path/to/project --entry-mode MIDSTREAM_TAKEOVER --mode EXECUTION_ENABLED
python3 skills/robotics-ar/scripts/robotics_ar.py takeover-init --project-root /path/to/project
python3 skills/robotics-ar/scripts/robotics_ar.py doctor --project-root /path/to/project
```

Audit discovery has file, content-byte and elapsed-time limits. Incomplete scans return `PARTIAL`; the CLI emits a summary and artifact paths. History import cannot discard a reconciliation requirement. Compile and explicitly select a baseline with a reason, then reserve approved execution resources before launch.

`reserve-execution`, `start-execution` and `register-external-execution` record reservation, launch and completion. `import-execution` imports retrospective evidence without retroactive authority. Launch records and lease tokens reject direct relaunches and stale writers. Local receipts do not guarantee exactly-once external effects; reconcile uncertain execution before retrying.

A local cooperative lock protects event append. Committed transitions can recover interrupted state projections; doctor reports damaged history without reordering it. Terminal resume is a no-op. Explicit authorized file snapshots support multi-repository content checks; without them, resume retains its Git-cleanliness check.

Qualify automatic execution in the actual environment, particularly remote leases, shared filesystems and physical devices. Unit tests alone do not establish stable deployment. Telemetry is off by default. Optional local `--invocation-receipt` records limited CLI metadata without prompts or command arguments.

## Validate and release

Representative commands are listed in the Chinese section and each Skill entry point. Run the repository release gate with:

```bash
python3 -B scripts/run_stable_checks.py
python3 scripts/build_release_bundle.py
```

Build formal releases from a clean checkout. The builder enforces a runtime archive below 5 MiB and developer archive below 20 MiB, excluding local sessions, papers, caches and Git metadata. Record unexecuted checks as `NOT_RUN`. The `VERSION` file identifies the release.

`audit_prose_invariants.py before.txt after.txt` compares quantities, citations, inline mathematics and evidence states. It is a mechanical check, not a semantic-equivalence proof.

## Repository, privacy and sources

`skills/` contains the six entry points and their scoped resources. `common/`, `assets/` and `schemas/` provide shared contracts and templates. `corpus/` contains compact resources, provenance and synthetic fixtures. `scripts/` holds installation, routing and checks; `tools/corpus/` holds explicit offline builds; `archive/` is historical only.

Keep raw papers and private project data in their own workspaces. Synthetic Golden cases test workflow behavior, not improved research outcomes. Model-assisted pattern analysis is not measured embedding, UMAP/HDBSCAN or an acceptance model.

Method references include [ResearchStudio](https://arxiv.org/abs/2607.04439), [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills-codex), [Awesome-Journal-Skills](https://github.com/brycewang-stanford/Awesome-Journal-Skills), [ARIS](https://github.com/wanshuiyin/auto-claude-code-research-in-sleep), [Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills), [nature-skills](https://github.com/Yuan1z0825/nature-skills) and [Humanizer](https://github.com/blader/humanizer). Their methods are adapted to robotics; the complete upstream projects are not runtime dependencies.

Released under the [MIT License](LICENSE). See [SOURCE_SNAPSHOTS.json](SOURCE_SNAPSHOTS.json) for provenance and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and adaptation licenses.
