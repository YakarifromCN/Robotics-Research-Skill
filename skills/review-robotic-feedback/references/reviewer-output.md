# 评审输出契约

每个代理输出 `assets/review-report.template.json` 对应的 JSON。`summary` 必须简洁概括负责维度；`strengths` 记录真实优点；`findings` 只写带锚点的问题；`unassessed` 解释为何不能评估；`recommendation` 是该维度建议，不是最终编辑决定。

finding 的最小结构：

```json
{
  "finding_id": "F001",
  "severity": "MAJOR",
  "category": "claim_evidence_mismatch",
  "location": {"file": "main.tex", "anchor": "Section 4, paragraph 2"},
  "evidence_anchor": {"type": "quote", "value": "short exact quote"},
  "issue": "可核验的问题",
  "impact": "对主张或复现的影响",
  "action": "最小可行修改或新增证据",
  "state": "open",
  "claim_ids": ["C001"],
  "evidence_state": "INCONCLUSIVE"
}
```

---

# English

Each reviewer emits the JSON defined by `assets/review-report.template.json`. Summaries describe the assigned dimension; strengths must be genuine; findings require typed anchors; unassessed items explain missing evidence; recommendations remain dimension-local. Meta Review may cite only report and finding IDs.
