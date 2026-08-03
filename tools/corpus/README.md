# 离线语料工具

本目录保存仍然有效、但不属于日常 Skill 运行时的语料构建与审计工具。它们只把本地论文
材料压缩为可提交的紧凑 JSON 工件；正常路由不得导入本目录，也不得读取原始论文全文。

## 功能组

| 组 | 入口 |
| --- | --- |
| 来源与全文收据 | `fetch_public_paper_sources.py`、`extract_public_paper_text.py`、`audit_public_paper_text_coverage.py`、`apply_public_paper_web_fulltext_receipts.py`、`validate_public_paper_fulltext_receipts.py` |
| 100 篇索引 | `build_public_paper_index.py`、`build_public_paper_index_v2.py`、`validate_public_paper_index.py` |
| ResearchStudio 归纳 | `merge_researchstudio_signature_chunks.py`、`validate_researchstudio_signatures_v2.py`、`build_researchstudio_pattern_induction_v2.py`、`validate_researchstudio_pattern_induction_v2.py` |
| 模式与轴策略 | `build_researchstudio_pattern_cards.py`、`validate_researchstudio_pattern_library.py`、`build_robotics_axis_strategy_v2.py`、`validate_robotics_axis_strategy_analysis_v2.py` |
| 紧凑运行工件 | `build_robotics_research_runtime.py`、`validate_robotics_research_runtime.py`、`calibrate_robotics_submanifold.py` |
| 边界审计 | `validate_researchstudio_outcome_contrast.py`、`validate_simulated_researchstudio.py` |

`_pattern_cards.py` 是 pattern-card builder 的唯一实现；同名无下划线文件只是稳定 CLI/API
门面。不存在 `.source` 动态执行链。

## 输入和依赖

工具使用 Python 3.8+ 标准库。输入 PDF、抽取文本、embedding、`public-paper-index.json` 和
论文级 signature 默认是本地私有中间工件，已由 `.gitignore` 排除。构建器必须记录仓库
相对 POSIX 路径或内容 SHA-256，不能写入 `E:`、`/mnt`、`/home` 等主机绝对路径。

```bash
python3 tools/corpus/validate_public_paper_index.py <local-corpus>
python3 tools/corpus/build_robotics_research_runtime.py --input <local-corpus>
python3 tools/corpus/validate_robotics_research_runtime.py
```

这些命令是维护者显式操作，不是安装后第一次使用 Skill 的初始化步骤。

---

# English

## Offline corpus tools

This directory contains current corpus builders and auditors that are not part
of normal Skill runtime. They compress local paper material into compact,
committable JSON artifacts. Normal routing must neither import this directory
nor read raw paper full text.

## Functional groups

| Group | Entry points |
| --- | --- |
| Sources and full-text receipts | `fetch_public_paper_sources.py`, `extract_public_paper_text.py`, `audit_public_paper_text_coverage.py`, `apply_public_paper_web_fulltext_receipts.py`, `validate_public_paper_fulltext_receipts.py` |
| 100-paper index | `build_public_paper_index.py`, `build_public_paper_index_v2.py`, `validate_public_paper_index.py` |
| ResearchStudio induction | `merge_researchstudio_signature_chunks.py`, `validate_researchstudio_signatures_v2.py`, `build_researchstudio_pattern_induction_v2.py`, `validate_researchstudio_pattern_induction_v2.py` |
| Patterns and axis strategies | `build_researchstudio_pattern_cards.py`, `validate_researchstudio_pattern_library.py`, `build_robotics_axis_strategy_v2.py`, `validate_robotics_axis_strategy_analysis_v2.py` |
| Compact runtime artifacts | `build_robotics_research_runtime.py`, `validate_robotics_research_runtime.py`, `calibrate_robotics_submanifold.py` |
| Boundary audits | `validate_researchstudio_outcome_contrast.py`, `validate_simulated_researchstudio.py` |

`_pattern_cards.py` is the sole pattern-card builder implementation. The file
without the leading underscore is a stable CLI/API facade. No `.source`
dynamic-execution chain remains.

## Inputs and dependencies

The tools require Python 3.8+ and the standard library. Input PDFs, extracted
text, embeddings, `public-paper-index.json`, and paper-level signatures are
local private intermediates ignored by Git. Builders must record repository-
relative POSIX paths or content SHA-256 values, never host paths such as `E:`,
`/mnt`, or `/home`.

```bash
python3 tools/corpus/validate_public_paper_index.py <local-corpus>
python3 tools/corpus/build_robotics_research_runtime.py --input <local-corpus>
python3 tools/corpus/validate_robotics_research_runtime.py
```

These commands are explicit maintainer operations, not first-run setup for an
installed Skill.
