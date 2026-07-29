# Idea 阶段的子流形路由

在生成或审计 Research Card 前，调用根目录 `scripts/route_robotics_submanifold.py`（catalog 使用 `corpus/venue-catalog.v2.json`），或读取 `corpus/robotics-submanifold-calibration.v1.json`。记录 E/P/C/L/D/H/A/S 的 0–3 向量、`active_axes`、`research_intensity`、`proposed_evidence_pressures` 和指定 venue 的官方范围待核验项。

这些字段是候选审计的输入，不是自动生成的 Claim Lock。若向量显示跨轴系统，只能提出更高证据负担的审计问题；只有用户/研究者明确冻结后才能写入 Claim Lock。评级字段不参与 Idea 路由。

---

# English

Before generating or auditing a Research Card, call the root `scripts/route_robotics_submanifold.py` with `corpus/venue-catalog.v2.json`, or read the calibration report. Record the E/P/C/L/D/H/A/S vector, active axes, research intensity, proposed evidence pressures, and official-scope items to refresh for a specified venue.

These fields are audit inputs, not an automatic Claim Lock. A cross-axis vector may propose a higher evidence burden, but only the researcher may explicitly freeze the resulting claim. Rating fields do not participate in Idea routing.
