# 公开机器人证据语料

该目录只保存公开论文元数据、可核验来源、设计模式标签与合成回归案例，不保存私人项目，也不复制论文正文。获奖或高复用标签只是“值得抽取什么”的采样线索，不代表充分证据。

公开全文工作流使用 `scripts/fetch_public_paper_sources.py` 将 PDF 放入被 Git
忽略的 `corpus/papers/`，用 `scripts/extract_public_paper_text.py` 生成被忽略的
`corpus/extracted/`，并把 URL、日期、字节数、SHA-256 和解析状态写入受版本控制的
`public-paper-fulltext-manifest.v1.json`。对禁止无人值守缓存、但可在公开网页完整
读取的 19 篇论文，另用 `public-paper-web-fulltext-receipts.v1.json` 保存独立收据。
当前核心语料为 81 篇本地抽取全文加 19 篇公开网页全文，合计 100/100 可用全文；
网页收据不会被冒充为本地 PDF 或本地文本哈希。

模拟 embedding、模拟聚类和审计只保存于被忽略的 `agent/internal/`；它们必须标记
`SIMULATED_NOT_MODEL_EMBEDDING` 或 `SIMULATED_NOT_REAL_UMAP_HDBSCAN`，不能作为真实
ResearchStudio 统计结果。

开源运行时使用 `researchstudio-paper-signatures.v2.json` 的混合保真度签名、
`researchstudio-pattern-induction.v2.json` 的 15/31 能力映射、
`robotics-axis-strategy-analysis.v2.json` 的八轴策略，以及
`researchstudio-outcome-contrast.v1.json` 的关闭式 outcome 合同。它们用于 Skill
路由与审计，不把模拟簇、奖项或 presentation 转成科学结果或录用概率。

---

# Public robotics evidence corpus

This directory stores only public-paper metadata, verifiable sources, pattern labels, and synthetic regression cases. It contains no private projects or copied paper text. Awards or community reuse are sampling signals, never proof of sufficient evidence.

The public-full-text workflow keeps downloaded PDFs and extracted text in ignored local
caches (`corpus/papers/` and `corpus/extracted/`). The tracked manifest records 81 locally
extracted papers, while `public-paper-web-fulltext-receipts.v1.json` records 19 complete
public web texts whose hosts block unattended caching. The core corpus therefore has
100/100 usable full texts, while web receipts are never represented as local PDF or text
hashes. Model-simulated embedding, clustering, and audit artifacts stay under
ignored `agent/internal/` and are not real UMAP/HDBSCAN evidence.

The open runtime uses the mixed-fidelity v2 signature index, the complete
15/31 capability-induction receipt, the regenerated eight-axis strategy
report, and a closed-by-design outcome contract. These artifacts support Skill
routing and audit only; simulated clusters, awards, and presentation traces
are not scientific outcomes or acceptance estimates.
