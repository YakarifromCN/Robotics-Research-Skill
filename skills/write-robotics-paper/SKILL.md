---
name: write-robotics-paper
description: 面向机器人论文的证据约束写作、修订、回复与主张审计 Skill；以 Claim Ledger 控制主张、数字、引文、图链和证据状态，支持 Markdown 与 LaTeX。
---
# 机器人论文写作 / Robotics Paper Writing

## 边界

只表达已锁定的方法和已有结果，不补造 Idea、实验、数字或引文。先读 `references/core-contract.md` 和 `references/claim-evidence-writing.md`；只按激活领域读取仓库级 `references/packs/*.md`。

## 模式

`FULL_DRAFT`、`WRITING_ONLY`、`REVISION_ONLY`、`REBUTTAL`、`CLAIM_AUDIT`。既有项目必须携带 `change_envelope`，例如只允许 prose、figure order、claim narrowing。

## 工作流

1. OUTLINE 前更新独立的 `target-fit-snapshot.json`，核验篇幅、匿名、格式与补充材料约束；它只影响包装。
2. 建立 Claim Ledger：每个句级主张连接结果、数字、引文和图；遵守 `INCONCLUSIVE` 不得升级的单调性。
3. 先组织 C→R→X→T：主张、结果、反证/边界、任务意义，再写段落。
4. 数字用 `{{N001}}` 占位并由 renderer 注入；不要手工复制冻结数值。
5. 审计夸大、泛化、因果、实时/安全/轻量等措辞。只有承重方法或证据完全缺失正文时才判定非自包含。
6. 投稿前再次实时核验 target snapshot；不得借包装变化扩大科学主张。

## 命令

```bash
python3 skills/write-robotics-paper/scripts/validate_claim_ledger.py claim-ledger.json --ready
python3 skills/write-robotics-paper/scripts/render_numbers.py manuscript.tex claim-ledger.json --output manuscript.rendered.tex
python3 skills/write-robotics-paper/scripts/audit_latex.py manuscript.rendered.tex claim-ledger.json
```

证据缺口输出 `EVIDENCE_GAPS`，不以流畅措辞掩盖。

---

# English

Write only from frozen claims and observed evidence. Keep venue adaptation mutable and separate. Track sentence claims, results, numbers, citations, and figures in the ledger; render frozen numbers automatically; audit Markdown or LaTeX without upgrading inconclusive evidence.
