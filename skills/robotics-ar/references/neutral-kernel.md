# Neutral kernel / 领域中立 Kernel

## 中文

Kernel 对象是 `ResearchQuestion`、`Charter`、`Hypothesis`、`Unknown`、`CandidateAction`、
`ExecutionRequest`、`Evidence`、`Constraint`、`Budget`、`Decision`、`Claim`、
`StageInput`、`StagePackage`、`StageReceipt` 和 `StageDecision`。它们只保存 generic
ID、状态、摘要 hash、路径、预算、证据状态和 `domain_payload`。

核心 schema 的 required 字段不得要求任何机器人、机器学习、论文、venue、指标或
baseline 词；领域 schema 通过 envelope 外置。canonical JSON 拒绝非有限数，所有
hash 使用 UTF-8、排序 key 和紧凑分隔符。

# English

Kernel objects are generic research questions, charters, hypotheses, unknowns, candidate
actions, execution requests, evidence, constraints, budgets, decisions, claims, stage
inputs/packages/receipts, and stage decisions. They contain generic IDs, state, hashes,
paths, budgets, evidence status, and `domain_payload`. Required core fields never require
robotics, ML, publication, venue, metric, or baseline terms. Canonical JSON rejects
non-finite values and hashes UTF-8 sorted-key compact bytes.
