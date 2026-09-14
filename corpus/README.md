# 科研资源与运行依赖

## 中文

普通 Skill 调用读取紧凑资源，不读取原始论文索引、PDF、抽取文本、embedding 或历史会话。完整论文材料是维护者的本地离线输入，不是新用户安装后的必需准备。

| 类别 | 文件 |
| --- | --- |
| 当前运行必需 | `robotics-research-runtime.v1.json`、`robotics-submanifold.v1.json`、`researchstudio-pattern-cards.v1.json`、`venue-catalog.v2.json` |
| 可选校准 | `robotics-submanifold-calibration.v1.json` |
| 离线归纳与来源审计 | `researchstudio-pattern-induction.v2.json`、`robotics-axis-strategy-analysis.v2.json`、`researchstudio-outcome-contrast.v1.json`、公开全文与覆盖收据 |
| 测试输入 | `golden/synthetic-cases.json` |
| 历史版本 | `../archive/legacy-v1/corpus/` |

文件名的版本号属于各自 schema。当前 runtime、模型和模式卡的 v1 没有对应的 v2 替代品；v2 归纳产物承担另一种用途。载体目录则已经使用 v2，旧目录只留在归档。

紧凑 runtime 提供来源摘要、策略问题和模式上下文。来源收据记录构建时的证据状态，不保证外部链接现在仍可用。模式归纳是描述性分析，不代表实际执行过统计 PCA、embedding 或 UMAP/HDBSCAN，也不估计录用概率。公开论文或奖项只用于发现与比较，不能替代用户实验。

维护者显式构建时使用：

```bash
python3 tools/corpus/validate_public_paper_index.py <local-corpus>
python3 tools/corpus/build_robotics_research_runtime.py --input <local-corpus>
python3 tools/corpus/validate_robotics_research_runtime.py
```

从仓库根执行。来源路径应使用仓库相对 POSIX 路径；仓库外输入只保留内容摘要，不提交个人绝对路径。详见 [离线工具](../tools/corpus/README.md)。

# English

## Research resources and runtime dependencies

Normal invocation reads compact resources, not raw indexes, papers, extracted text, embeddings or session history. Full paper material is a maintainer's local offline input, not a new user's prerequisite.

| Category | Files |
| --- | --- |
| Required runtime | `robotics-research-runtime.v1.json`, `robotics-submanifold.v1.json`, `researchstudio-pattern-cards.v1.json`, `venue-catalog.v2.json` |
| Optional calibration | `robotics-submanifold-calibration.v1.json` |
| Offline induction and provenance | `researchstudio-pattern-induction.v2.json`, `robotics-axis-strategy-analysis.v2.json`, `researchstudio-outcome-contrast.v1.json`, public full-text and coverage receipts |
| Test input | `golden/synthetic-cases.json` |
| Historical versions | `../archive/legacy-v1/corpus/` |

Version suffixes identify separate schemas. The v1 runtime, model and pattern cards remain current; v2 induction artifacts serve another purpose. The venue catalog uses v2, with its predecessor archived.

Runtime provides source summaries, strategy questions and pattern context. Provenance receipts describe the build-time evidence state, not current URL availability. Descriptive pattern analysis does not establish measured PCA, embeddings, UMAP/HDBSCAN or acceptance estimates. Public papers and awards aid discovery, not proof of a user's claim.

Run the explicit build commands above from the repository root. Use repository-relative POSIX source paths, or content digests for external inputs. Keep personal absolute paths out of public artifacts. See [offline tooling](../tools/corpus/README.md).
