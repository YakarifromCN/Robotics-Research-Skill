# 证据约束型机器人论文修订

用于修订、rebuttal、camera-ready 压缩或防御性写作审计。先读取共享七原则，
再以 Claim Ledger ceiling 而不是原句强度为上限；允许把 underclaim 增强到
冻结上限，同时阻止 overclaim。D/K 词法线索只产生候选，最终 disposition
必须根据上下文、证据功能和 author authority 决定。

保护 scope、source status、negative result、rival、method、safety、稳定
claim/result/number/citation ID 的语义功能，不保护重复原句。未经授权只诊断；
完成修改后运行 revision audit、Claim Ledger validator 与 LaTeX audit。

---

# English

Read this reference for revision, rebuttal, camera-ready compression, or an
explicit defensive-writing audit. Do not use it to admit new evidence or change
the frozen scientific object. Apply `common/evidence-bound-revision.md` first.

## Classification and dispositions

- `D1` apology/self-deprecation; `D2` phantom-objection defence; `D3` stacked
  hedge; `D4` non-evidentiary work log; `D5` buried contribution; `D6`
  volunteered loss; `D7` negative judgment broader than evidence; `D8` caution
  in the wrong rhetorical position.
- `K1` scope condition; `K2` evidence/source-status distinction; `K3` rival,
  contradiction, failure, delay, reversal, or negative result; `K4` ethical,
  provenance, reproducibility, method, or safety boundary.
- Use `KEEP`, `TIGHTEN`, `REFRAME`, `RELOCATE`, `DEDUPLICATE`, `CUT`, or `QUERY`.
  A K-class sentence may move or be deduplicated only when its evidentiary
  function is preserved at a replacement anchor or by another decision.

For each candidate answer: What function does it serve? What proposition,
boundary, or stable evidence object would disappear? Does the revision remain
within the frozen ledger ceiling? Put the supported scoped contribution before
qualifications. Do not preserve redundant wording merely because it contains a
caution, citation, number, or result; preserve its semantic and trace roles.

## Robotics evidence-status distinctions

| status | may support | must not silently become |
| --- | --- | --- |
| `DESIGN_INTENT` | planned mechanism or objective | delivered behavior |
| `ANALYTIC_RESULT` | derivation under stated assumptions | robot execution |
| `OFFLINE_PROXY` | recorded-data or surrogate result | closed-loop outcome |
| `SIMULATION_RESULT` | simulated regime finding | real-robot evidence |
| `REAL_ROBOT_EXECUTION` | observed execution on named hardware/tasks | formal guarantee or cross-embodiment law |
| `TASK_OUTCOME` | outcome under evaluated denominator | mechanism proof |
| `STATISTICAL_RESULT` | scoped estimate and uncertainty | universal effect |
| `MECHANISM_DIAGNOSTIC` | intervention/negative-control evidence | theorem |
| `MECHANISTIC_INTERPRETATION` | bounded causal account | identified mechanism without diagnostics |
| `FORMAL_GUARANTEE` | theorem within explicit assumptions | unrestricted safety or robustness |

Examples: a real-robot safety guard is not a safety guarantee; measured latency
is not a real-time guarantee; one robot is not cross-embodiment generalization.
Conversely, 15/15 evaluated real-robot runs are not merely a preliminary
simulation observation. Repair both overclaim and underclaim.

## Regression

After authorized edits, verify the frozen ceiling, evidence status, scope
coverage, stable claim/result/number/citation roles, conceptual hierarchy, and
contribution-first placement. Run the revision-audit validator and normal Claim
Ledger/LaTeX validators. An unresolved meaning-dependent query blocks only the
affected edit; it must never be silently resolved.
