# 证据约束型机器人论文修订

用于修订、rebuttal、camera-ready 压缩或防御性写作审计。先读取共享七原则，
再以 Claim Ledger ceiling 而不是原句强度为上限；允许把 underclaim 增强到
冻结上限，同时阻止 overclaim。D/K 词法线索只产生候选，最终 disposition
必须根据上下文、证据功能和 author authority 决定。

保护 scope、source status、negative result、rival、method、safety、稳定
claim/result/number/citation ID 的语义功能，不保护重复原句。未经授权只诊断；
完成修改后运行 revision audit、Claim Ledger validator 与 LaTeX audit。

## Anti 防御性写作蒸馏：起草与修订

来源：Adkid-Zephyr/anti-defensive-writing-Skill，固定版本
`e65bd9d8bf8ed8b9af809e5aff8237d76370876d`，MIT；许可见根目录 THIRD_PARTY_NOTICES.md。
这是证据约束下的改编，不是上游全部规则的照搬，无外部运行依赖。

1. 先找已有证据最清楚支持的贡献：新能力、机制、成本、效率或有价值的权衡。
   摘要与引言尽早串起问题、缺口、方法和关键结果；结论重述成立的贡献，不突然扩大自我否定。
2. 按论证关系组织，不按研究尝试的时间顺序汇报。每个图表或实验说明其职责：
   效果、机制、场景价值、替代解释或失败边界。失败边界本身是必要证据，不能因不利而删除。
3. 把“遗憾的是”“只是初步尝试”等作为审阅候选，不设禁词清单。检查删去后是否丢失
   条件、事实或不确定性；丢失则 KEEP 或换为准确的限定，纯粹姿态则 TIGHTEN/REFRAME。
4. 局部落后不要推导为整体无价值。保留落后的指标、数值与条件，同时陈述已验证的收益；
   只有两方面都有证据，才称为权衡。未测量的补偿收益不能编造。
5. 原叙事站不住时，可在 change envelope 内调整篇章或收窄主张；不得为了显优势换掉
   冻结的主指标、基线、分母、排除规则或核心科学对象。超出授权则 QUERY/返回上游阶段。
   新评价维度属于明确标注的探索性分析，不能冒充原定主要终点。
6. 压缩重复内容按论证功能决定，不按结果正负决定。报告所有影响核心结论的反例、
   负结果和安全事件；必要的方法或证据不得全藏进补充材料。准确的“不优于”不是写作错误。

机器人示例：将“遗憾的是，我们仅在单臂平台验证，因此方法价值有限”改为
“方法在所评估的单臂任务中保持接触；跨平台适用性尚未验证”，前提是两项事实均有依据。
若能耗确实增加，应保留“成功率提高，但能耗增加”及其数值，不能改成笼统的“全面提升”。
仿真不能润色为实机，测得低延迟不能润色为实时保证，急停机制不能润色为安全证明。

先进行贡献与证据校准，再进行 Humanizer 语言检查；复查数字、引文、结果状态及必要限定。
脚本只提名词法候选，不替代语义评审。默认交付修订正文，不另生成 anti 写作报告；
需要的既有审计状态按项目分类维护，不生成一任务一文件的重复总结。

---

# English

## Anti-defensive-writing distillation for drafting and revision

Adapted from Adkid-Zephyr/anti-defensive-writing-Skill at commit
`e65bd9d8bf8ed8b9af809e5aff8237d76370876d` (MIT; see root THIRD_PARTY_NOTICES.md).
This evidence-bound adaptation does not adopt every upstream rule and has no external runtime dependency.

1. Identify the contribution best supported by existing evidence: capability, mechanism,
   cost, efficiency, or a useful trade-off. Introduce problem, gap, method and key result
   early; conclude with established contributions rather than new sweeping self-criticism.
2. Organize the argument, not the chronology of attempts. Give figures and experiments a
   role: effect, mechanism, application value, alternative explanation, or failure boundary.
   Failure boundaries are evidence, not disposable distractions.
3. Treat apologies and self-deprecation as review candidates, never forbidden words.
   Preserve conditions, facts and uncertainty; KEEP or rewrite necessary qualifications,
   and TIGHTEN/REFRAME empty rhetorical posture.
4. Do not infer global worthlessness from a local loss. Retain the adverse metric, values
   and conditions alongside verified benefits. Call it a trade-off only when both sides
   are evidenced; never invent compensating benefits.
5. Reorder the story or narrow claims within the change envelope. Do not switch frozen
   primary metrics, baselines, denominators, exclusions or the scientific object to look
   stronger. QUERY or return upstream when authority is missing. Label new evaluation
   dimensions exploratory; do not present them as the original primary endpoint.
6. Compress by argumentative function, not result sign. Disclose counterexamples,
   negative results and safety events material to the core conclusion. Keep load-bearing
   methods and evidence accessible in the main text. Accurate inferiority is not a style error.

Example: replace an unsupported global dismissal after single-arm testing with the supported
task-level contact result and the untested cross-platform boundary. If success improves but
energy use rises, retain both measurements, not a claim of improvement everywhere. Simulation
does not become real-robot evidence, low latency a real-time guarantee, or an emergency stop
a safety proof. Calibrate the contribution before Humanizer; recheck numbers, citations,
result states and necessary qualifications afterward. Lexical scripts nominate candidates,
not semantic verdicts. Deliver revised prose by default, not a separate anti-writing report;
reuse categorized audit state where needed without per-task narrative summaries.

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
