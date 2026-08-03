# 运行与维护脚本

`scripts/` 只保留普通用户或发布流程会直接调用的入口。离线论文语料构建已移到
[`tools/corpus/`](../tools/corpus/README.md)，被当前实现替代的 v1 链位于
[`archive/legacy-v1/`](../archive/README.md)。正常 Skill 调用不会扫描这两个目录。

## 运行入口

| 入口 | 用途 | 是否进入 staged 安装 |
| --- | --- | --- |
| `route_robotics_research.py` | 构建 Idea、Experiment、Writing 或 Review 的紧凑上下文；加 `--ideate` 可运行带停止门的 Idea 链 | 是 |
| `route_robotics_submanifold.py` | 直接生成非序数子流形、证据压力与 target-fit 候选 | 是 |
| `validate_researchstudio_idea_card.py` | 校验统一路由产生的 ResearchStudio Idea 工件 | 否 |

路由只读取以下紧凑工件：

- `corpus/robotics-research-runtime.v1.json`；
- `corpus/robotics-submanifold.v1.json`；
- `corpus/researchstudio-pattern-cards.v1.json`；
- `corpus/venue-catalog.v2.json`；
- 可选的 `corpus/robotics-submanifold-calibration.v1.json`。

四个科研阶段 Skill 的本地 `scripts/`、`assets/`、`references/`，以及 Robotics-AR 的
`scripts/`、`schemas/`、`assets/`，分别属于对应 Skill 的独立运行闭包。

## 安装与更新

`local_skill_install.py` 是安装、更新和 doctor 的唯一实现。下面三个文件只是按动作分开的
稳定 CLI，不复制安装逻辑：

- `install_local_skills.py`；
- `update_local_skills.py`；
- `doctor_local_skills.py`。

`SAFE_STAGED_WORKTREE`、`COPY_PINNED` 和 `DIRECT_DOWNLOAD` 只复制运行闭包，排除
`tests/`、`__pycache__/`、`.pyc`、`tools/` 与 `archive/`。参与开发时使用
`SYMLINK_TRACKED_CLONE`，由本地分支直接驱动已安装 Skill。

## 校验与迁移

- `run_all_checks.py` 是唯一检查实现，支持 `default`、`extended` 和 `corpus-first` profile；
- `run_all_checks_v2.py` 与 `run_all_checks_corpus_first.py` 是兼容薄入口；
- `check_bilingual_layout.py`、`check_portable_corpus_paths.py` 与 `validate_*` 是明确调用的发布校验器；
- `migrate_v1.py` 将旧项目提取为待人工审计的 V2 草稿，不重写科学语义。

## 依赖边界

核心运行要求 Python 3.8+ 且只使用标准库。JSON 是默认结构化格式。只有用户主动提供
YAML 输入时，Robotics-AR 才需要可选依赖 PyYAML：

```bash
python3 -m pip install PyYAML
```

运行时不会联网安装依赖。原始 PDF、抽取文本、embedding、论文级 signature 和本地 agent
状态均由 `.gitignore` 排除；它们不应为了“完整”而复制到 staged 安装或 Git archive。

## 常用命令

```bash
python3 scripts/route_robotics_research.py profile.json --stage idea
python3 scripts/route_robotics_research.py profile.json --stage idea --ideate
python3 scripts/run_all_checks.py
python3 scripts/run_all_checks_corpus_first.py
python3 -m unittest tests/test_local_skill_install.py -v
```

---

# English

## Runtime and maintenance scripts

`scripts/` contains only entry points directly used by normal users or the
release workflow. Offline paper-corpus tooling lives in
[`tools/corpus/`](../tools/corpus/README.md), while the superseded v1 chain is
kept in [`archive/legacy-v1/`](../archive/README.md). Normal Skill invocations
do not scan either directory.

## Runtime entry points

| Entry point | Purpose | Included in staged installs |
| --- | --- | --- |
| `route_robotics_research.py` | Build compact Idea, Experiment, Writing, or Review context; `--ideate` runs the gated Idea chain | Yes |
| `route_robotics_submanifold.py` | Produce the non-ordinal submanifold, evidence pressures, and target-fit candidates | Yes |
| `validate_researchstudio_idea_card.py` | Validate ResearchStudio Idea artifacts emitted by the unified route | No |

Routing reads only these compact artifacts:

- `corpus/robotics-research-runtime.v1.json`;
- `corpus/robotics-submanifold.v1.json`;
- `corpus/researchstudio-pattern-cards.v1.json`;
- `corpus/venue-catalog.v2.json`;
- optional `corpus/robotics-submanifold-calibration.v1.json`.

Each of the four research-stage Skills owns its local `scripts/`, `assets/`,
and `references/`. Robotics-AR independently owns its `scripts/`, `schemas/`,
and `assets/` runtime closure.

## Installation and updates

`local_skill_install.py` is the only implementation for install, update, and
doctor operations. The following files are stable action-specific CLIs and do
not duplicate the implementation:

- `install_local_skills.py`;
- `update_local_skills.py`;
- `doctor_local_skills.py`.

`SAFE_STAGED_WORKTREE`, `COPY_PINNED`, and `DIRECT_DOWNLOAD` copy only the
runtime closure and omit `tests/`, `__pycache__/`, `.pyc`, `tools/`, and
`archive/`. Contributors should use `SYMLINK_TRACKED_CLONE`, which exposes
local branch updates directly to installed Skills.

## Validation and migration

- `run_all_checks.py` is the single check implementation with `default`,
  `extended`, and `corpus-first` profiles;
- `run_all_checks_v2.py` and `run_all_checks_corpus_first.py` are thin
  compatibility entry points;
- `check_bilingual_layout.py`, `check_portable_corpus_paths.py`, and the
  `validate_*` files are explicitly invoked release validators;
- `migrate_v1.py` extracts old projects into human-audited V2 drafts without
  rewriting scientific meaning.

## Dependency boundary

The core runtime requires Python 3.8+ and uses only the standard library. JSON
is the default structured format. PyYAML is optional and needed by Robotics-AR
only when a user actively supplies YAML input:

```bash
python3 -m pip install PyYAML
```

The runtime never installs dependencies from the network. Raw PDFs, extracted
text, embeddings, paper-level signatures, and local agent state are ignored by
Git and must not be copied into staged installs or a Git archive merely for
completeness.

## Common commands

```bash
python3 scripts/route_robotics_research.py profile.json --stage idea
python3 scripts/route_robotics_research.py profile.json --stage idea --ideate
python3 scripts/run_all_checks.py
python3 scripts/run_all_checks_corpus_first.py
python3 -m unittest tests/test_local_skill_install.py -v
```
