# 脚本入口

## 中文

日常使用从已安装 Skill 的 `SKILL.md` 进入。`scripts/` 保存共享路由、安装和发布工具；各 Skill 的专用校验器位于自己的 `scripts/`。

| 用途 | 入口 |
| --- | --- |
| 科研上下文 | `route_robotics_research.py`、`route_robotics_submanifold.py` |
| 安装、更新、诊断 | `install_local_skills.py`、`update_local_skills.py`、`doctor_local_skills.py` |
| 发布检查 | `run_stable_checks.py` |
| 完整检查与兼容入口 | `run_all_checks.py`、`run_all_checks_v2.py`、`run_all_checks_corpus_first.py` |
| 发布打包 | `build_release_bundle.py` |
| 历史工件迁移 | `migrate_v1.py` |
| 路径和文档检查 | `check_portable_corpus_paths.py`、`check_bilingual_layout.py` |

安装相关入口共享 `local_skill_install.py`，检查入口共享 `run_all_checks.py`。从其他 cwd 执行时使用脚本绝对路径，不依赖 `python` 别名。迁移结果需要人工审计，不能成为事前预注册证据。

普通路由读取紧凑 runtime、当前子流形模型、模式卡、载体目录和可选校准。安装排除测试、缓存、原始语料、`tools/` 和 `archive/`。COPY_PINNED 通过固定版本目录投影保留共享依赖；不要拆散投影与其发布目录。

JSON 路径使用标准库。YAML 输入及 Engineering 多行 frontmatter 需要可选 PyYAML；运行时不自动下载。Writing 内含 Humanizer 学术适配。

```bash
python3 scripts/route_robotics_research.py profile.json --stage idea
python3 scripts/route_robotics_research.py profile.json --stage idea --ideate
python3 -B scripts/run_stable_checks.py
python3 -B -m unittest discover -s tests -p test_local_skill_install.py -v
```

离线构建见 [tools/corpus](../tools/corpus/README.md)，历史文件见 [archive](../archive/README.md)。这些工具不属于首次使用初始化。

# English

## Script entry points

Start normal work from the installed Skill's `SKILL.md`. This directory contains shared routing, installation and release tooling; specialized validators live under their owning Skill.

| Purpose | Entry points |
| --- | --- |
| Research context | `route_robotics_research.py`, `route_robotics_submanifold.py` |
| Install, update, diagnose | `install_local_skills.py`, `update_local_skills.py`, `doctor_local_skills.py` |
| Release checks | `run_stable_checks.py` |
| Checks and compatibility facades | `run_all_checks.py`, `run_all_checks_v2.py`, `run_all_checks_corpus_first.py` |
| Release packaging | `build_release_bundle.py` |
| Legacy migration | `migrate_v1.py` |
| Path and document checks | `check_portable_corpus_paths.py`, `check_bilingual_layout.py` |

Installation CLIs share `local_skill_install.py`; check CLIs share `run_all_checks.py`. Use absolute script paths from other working directories. Migration outputs require human audit and cannot establish prospective registration.

Normal routing uses compact runtime, the current manifold model, pattern cards, venue catalog and optional calibration. Installs omit tests, caches, raw corpus, offline tools and archives. COPY_PINNED preserves shared dependencies through a fixed release projection; keep its release directory intact.

JSON uses the standard library. YAML input and multiline Engineering frontmatter require optional PyYAML. No runtime dependency downloads occur. Writing includes an academic Humanizer adaptation.

Run the commands in the Chinese section from the repository root. [Offline corpus tools](../tools/corpus/README.md) and [historical archives](../archive/README.md) are not first-run setup.
