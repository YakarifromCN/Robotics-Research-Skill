# 100 篇公开机器人论文语料契约

`corpus/public-paper-index.json` 由 `scripts/build_public_paper_index_v2.py` 生成，当前 schema 为 `robotics-public-corpus.v2`。

硬约束：

- 总计 100 篇；期刊 50 篇、会议 50 篇；
- 会议记录必须有 `oral`、`spotlight` 或更高的 presentation level；
- `award.qualifies_for_quota=true` 至少 51 篇；状态保留为 `winner`、`finalist`、`nominee` 或 `award`，finalist 不改写成 winner；
- 八条主轴按总量均匀采样：E/P/C/L 为 13，D/H/A/S 为 12，最大差 1；
- 期刊内部为 E/P/C/L/D/H/A/S = 7/7/6/6/6/6/6/6，会议内部为 6/6/7/7/6/6/6/6，最大差均为 1；
- 每篇记录同时保存公开预印本/accepted manuscript/open full-text record、final venue record、八轴向量、可抽取模式和禁止外推边界。

奖项约束是“award recognition” quota，不是统计学标签，也不是论文质量或录用概率。严格 winner 数量由 `scripts/calibrate_robotics_submanifold.py` 另外报告。语料用于校准证据模式和子流形覆盖，不复制论文正文，不估计学科 prevalence，不拟合 PCA/因子模型。

## 全文来源与混合保真签名

`scripts/fetch_public_paper_sources.py`、`extract_public_paper_text.py` 和
`audit_public_paper_text_coverage.py` 将公开来源解析为可审计收据。当前 100 篇
记录中，81 篇为 `DOWNLOADED`、19 篇为 `UNRESOLVED`；文本覆盖为 78 篇具有
章节标记、3 篇不完整、19 篇无本地全文。未解析记录必须保留候选来源和失败
状态，不能被静默删除或伪装成全文证据。

`corpus/researchstudio-paper-signatures.v2.json` 采用混合保真合同：

- 81 篇 `FULLTEXT_EXTRACTED`，签名字段绑定抽取文本与哈希；
- 19 篇 `METADATA_FALLBACK`，明确限制为题名、摘要或索引元数据；
- 每个模型归纳字段保存 provenance，不把模型模拟输出写成论文原文事实。

模型子代理可以模拟 embedding、聚类审计和模式归纳，但必须标记
`MODEL_SIMULATED`，不得声称运行了真实 UMAP/HDBSCAN。可注入 Skill 的只有
可解释的能力簇、模式族、子模式和路由问题。

## 开源与本地缓存边界

PDF、抽取正文、embedding、模型子代理分块 JSON 和临时下载只作为本地缓存，
由 `.gitignore` 排除。公开仓库跟踪来源 manifest、覆盖收据、内容哈希、
生成器、验证器和可复用归纳结果，从而允许审计而不提交内部或临时材料。

验证：

```text
python scripts/build_public_paper_index_v2.py
python scripts/validate_public_paper_index.py
python scripts/calibrate_robotics_submanifold.py
python scripts/validate_researchstudio_signatures_v2.py
python scripts/validate_simulated_researchstudio.py
python scripts/run_all_checks_corpus_first.py
```
