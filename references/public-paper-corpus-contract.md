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

验证：

```text
python scripts/build_public_paper_index_v2.py
python scripts/validate_public_paper_index.py
python scripts/calibrate_robotics_submanifold.py
```
