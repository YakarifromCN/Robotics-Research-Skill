# 评审输出契约

每个代理从零开始，只读取 context 的 `allowed_files`，不使用项目记忆、旧评审或其他代理报告，并按启动时给出的目标语言输出 `assets/review-report.template.json` 对应的 JSON。目标语言可以是任意单语，也可以是 `en+任意语言`。`summary` 必须简洁概括负责维度；`strengths` 使用 `review-strength.v1` 对象记录真实优点；`findings` 只写带锚点的问题；`evidence_gaps` 和 `not_assessable` 使用对象数组解释不能评估的原因；`recommendation` 是该维度建议，不是最终编辑决定。

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
  "evidence_state": "INCONCLUSIVE",
  "role": "primary",
  "critical_basis": null,
  "action_kind": "revise",
  "resolution_note": null
}
```

`CRITICAL` 必须提供 `critical_basis`；`state=resolved` 必须使用 `action_kind=preserve|monitor|none` 并写 `resolution_note`。`report_id` 必须非空，推荐 `<review_id>::<reviewer_id>`。不得把已解决强项放入普通 `findings`。

---

# English

Each fresh reviewer emits the JSON defined by `assets/review-report.template.json` in the requested output language. Read only `allowed_files`; do not use project memory, prior reviews, or other agents' reports. Summaries describe the assigned dimension; strengths use `review-strength.v1`; findings require typed anchors; `evidence_gaps` and `not_assessable` are object arrays; recommendations remain dimension-local. `CRITICAL` needs a documented basis, and resolved strengths must not remain ordinary findings. Meta Review may cite only report and finding IDs.
