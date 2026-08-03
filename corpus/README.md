# 机器人科研语料与运行时

完整的 100 篇论文索引是仅供本地使用的离线构建输入。正常 Skill 调用不需要它，
也不会将它提交到 Git。

```text
本地语料 -> 离线验证/构建 -> robotics-research-runtime.v1.json
                         -> 正常路由只读取 runtime
```

## 已跟踪的紧凑资源

- `robotics-research-runtime.v1.json`：紧凑论文先例、来源摘要、八轴策略行、模式系统摘要和非主张边界；
- `robotics-submanifold.v1.json`：透明的研究子流形轴模型；
- `venue-catalog.v2.json`：载体范围与 directness 先验；
- `researchstudio-pattern-cards.v1.json`：15 个父模式和 31 个子模式卡；
- `researchstudio-pattern-induction.v2.json`、`robotics-axis-strategy-analysis.v2.json`、
  `researchstudio-outcome-contrast.v1.json`：可审计的 ResearchStudio 聚合结果。
- `golden/synthetic-cases.json`：合成回归案例描述，不是运行时语料；只有被测试入口实际
  加载时才应继续保留。

## 运行时依赖闭包

- 必需：`robotics-research-runtime.v1.json`、`robotics-submanifold.v1.json`、
  `researchstudio-pattern-cards.v1.json`、`venue-catalog.v2.json`；
- 可选的紧凑校准：`robotics-submanifold-calibration.v1.json`；
- 仅用于离线构建或审计：全文收据、signature index、
  `researchstudio-pattern-induction.v2` 与 `robotics-axis-strategy-analysis.v2`；
- 已归档：旧版 `venue-catalog.v1` 位于 `archive/legacy-v1/corpus/`，当前代码不得读取。

`submanifold` 模型、pattern library 和 runtime 使用 v1 后缀是有意的：它们是当前
有效 schema，目前没有对应的 v2 替代品。v2 induction 和 axis-analysis 是来源/审计
产物，不替代 v1 pattern library 或 runtime schema。v2 venue catalog 才是当前路由
目录；v1 catalog 只保留在历史归档中。

## 本地语料与中间产物

本地专用内容包括 `public-paper-index.json`、论文级 signature index、PDF、抽取文本、
embedding 和 agent 内部模拟文件。来源清单和全文收据可以继续被跟踪，因为它们不含
语料记录或论文正文。

## 显式构建或审计

```bash
python tools/corpus/validate_public_paper_index.py <local-corpus>
python tools/corpus/build_robotics_research_runtime.py --input <local-corpus>
python tools/corpus/validate_robotics_research_runtime.py
```

runtime 是描述性科研基础设施，不声称执行了统计 PCA、潜变量拟合、真实 UMAP/HDBSCAN、
流行度估计、质量判断或录用概率建模。

---

# English

## Robotics research corpus and runtime

The complete 100-paper index is a local-only offline build input. A normal
Skill invocation does not require it, and it is not committed to Git.

```text
local corpus -> offline validation/build -> robotics-research-runtime.v1.json
                                      -> normal routing reads runtime only
```

## Tracked compact resources

- `robotics-research-runtime.v1.json`: compact exemplars, source digest, eight
  axis strategy rows, pattern-system summary, and non-claims;
- `robotics-submanifold.v1.json`: transparent axis model;
- `venue-catalog.v2.json`: venue scope and directness priors;
- `researchstudio-pattern-cards.v1.json`: 15 parent and 31 subpattern cards;
- `researchstudio-pattern-induction.v2.json`,
  `robotics-axis-strategy-analysis.v2.json`, and
  `researchstudio-outcome-contrast.v1.json`: auditable aggregate ResearchStudio
  results.

## Runtime dependency closure

- Required: `robotics-research-runtime.v1.json`,
  `robotics-submanifold.v1.json`, `researchstudio-pattern-cards.v1.json`, and
  `venue-catalog.v2.json`;
- Optional compact calibration:
  `robotics-submanifold-calibration.v1.json`;
- Offline build or audit only: full-text receipts, signature indexes,
  `researchstudio-pattern-induction.v2`, and
  `robotics-axis-strategy-analysis.v2`;
- Archived: legacy `venue-catalog.v1` lives under
  `archive/legacy-v1/corpus/` and current code must not read it.

`golden/synthetic-cases.json` describes synthetic regression cases rather than
runtime corpus data. Keep it only while a test entry actually consumes it.

The v1 suffix on the submanifold model, pattern library, and runtime is
intentional: these are the current schemas and no v2 replacement is available.
The v2 induction and axis-analysis files are provenance artifacts, not runtime
replacements for the v1 pattern library or runtime schema. The v2 venue catalog
is the active catalog; the v1 catalog is retained only in the historical
archive.

## Local-only corpus and intermediates

Local-only content includes `public-paper-index.json`, paper-level signature
indexes, PDFs, extracted text, embeddings, and agent-internal simulation files.
Provenance manifests and full-text receipts may remain tracked because they do
not contain corpus records or paper text.

## Explicit build or audit

```bash
python tools/corpus/validate_public_paper_index.py <local-corpus>
python tools/corpus/build_robotics_research_runtime.py --input <local-corpus>
python tools/corpus/validate_robotics_research_runtime.py
```

The runtime is descriptive research infrastructure. It does not claim
statistical PCA, latent-factor fitting, real UMAP/HDBSCAN, prevalence, quality
judgment, or acceptance-probability modeling.
