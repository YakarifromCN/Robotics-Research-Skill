# 离线语料工具

## 中文

本目录供维护者显式构建和审计论文衍生资源。工具读取本地输入，生成紧凑 JSON 和来源收据；普通 Skill 调用不导入本目录，也不执行这些构建步骤。

| 功能组 | 主要入口 |
| --- | --- |
| 来源与全文 | `fetch_public_paper_sources.py`、`extract_public_paper_text.py`、`audit_public_paper_text_coverage.py` |
| 索引 | `build_public_paper_index.py`、`build_public_paper_index_v2.py`、`validate_public_paper_index.py` |
| 归纳 | `merge_researchstudio_signature_chunks.py`、`build_researchstudio_pattern_induction_v2.py` |
| 模式与研究轴 | `build_researchstudio_pattern_cards.py`、`build_robotics_axis_strategy_v2.py` |
| 运行摘要 | `build_robotics_research_runtime.py`、`validate_robotics_research_runtime.py` |
| 校准与边界 | `calibrate_robotics_submanifold.py`、`validate_researchstudio_outcome_contrast.py`、`validate_simulated_researchstudio.py` |

对应的 `validate_*` 入口用于检查已有工件。`_pattern_cards.py` 保存模式卡构建实现，其公开入口是薄封装。

从仓库根运行：

```bash
python3 tools/corpus/validate_public_paper_index.py <local-corpus>
python3 tools/corpus/build_robotics_research_runtime.py --input <local-corpus>
python3 tools/corpus/validate_robotics_research_runtime.py
```

运行前检查具体工具的输入与外部程序要求。下载和全文抽取不是普通 JSON 路由的依赖。原始 PDF、文本、embedding、论文级签名和个人路径不得进入公开运行包；外部输入使用内容摘要标识。

# English

## Offline corpus tools

Maintainers explicitly run these builders and auditors to derive compact JSON and provenance receipts from local paper inputs. Normal Skill invocation neither imports this directory nor runs these steps.

| Group | Main entry points |
| --- | --- |
| Sources and full text | `fetch_public_paper_sources.py`, `extract_public_paper_text.py`, `audit_public_paper_text_coverage.py` |
| Indexes | `build_public_paper_index.py`, `build_public_paper_index_v2.py`, `validate_public_paper_index.py` |
| Induction | `merge_researchstudio_signature_chunks.py`, `build_researchstudio_pattern_induction_v2.py` |
| Patterns and axes | `build_researchstudio_pattern_cards.py`, `build_robotics_axis_strategy_v2.py` |
| Runtime summary | `build_robotics_research_runtime.py`, `validate_robotics_research_runtime.py` |
| Calibration and boundaries | `calibrate_robotics_submanifold.py`, `validate_researchstudio_outcome_contrast.py`, `validate_simulated_researchstudio.py` |

Related `validate_*` commands audit existing artifacts. `_pattern_cards.py` contains the builder implementation behind its public facade.

Run the commands above from the repository root after checking each tool's input and external-program requirements. Download and text extraction are not dependencies of normal JSON routing. Keep raw PDFs, text, embeddings, paper-level signatures and personal paths out of public runtime packages; identify external input by content digest.
