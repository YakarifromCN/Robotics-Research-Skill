# 科研监督层 / Research supervision layer

本文件将 Supervisor-Skills 的通用科研监督逻辑蒸馏为机器人研究约束。它不替代机器人 Research Card、Experiment Contract、Claim Ledger 或 Meta Review，而是在它们之间增加早期门控、论证链锁定和证据收口。

---

# English

This file distils the domain-neutral supervision logic from Supervisor-Skills into robotics constraints. It does not replace the robotics Research Card, Experiment Contract, Claim Ledger, or Meta Review; it adds early gates, argument-chain locking, and evidence closure between them.

## Shared gates

1. **Scope and type gate.** Classify the project as a technique, new problem/setting, benchmark/evaluation, or mixed robotics paper. A venue name never resolves an unclear scientific type.
2. **Fatal-flaw gate.** Check novelty collision, a data-refuted core mechanism, a non-falsifiable claim, missing task/evidence, unsafe or inaccessible execution, and lifecycle/resource mismatch before scoring or polishing. A CRITICAL flaw short-circuits the run.
3. **Argument-chain gate.** Keep at most three load-bearing limitations and challenges unless the user explicitly justifies more. Require `limitations -> goal/key idea -> challenges -> modules -> contributions -> sections` to be one-to-one where the scientific object demands it.
4. **Evidence gate.** Every load-bearing claim points to a result, citation, figure/table, or explicit evidence gap. Experiments must test the headline claim; mechanism attribution needs a control or ablation; negative, failed, aborted, and inconclusive outcomes remain visible.
5. **Integrity gate.** Check source provenance, claim altitude, venue scope, figure/table traceability, and reproducibility. A gate failure becomes a concrete finding or a stopping state, not a reassuring score.

## Idea-stage distillation

Before creating or revising a Research Card, write a one-sentence story and classify the paper type. Run the fatal-flaw gate first. Then use the five directional prompts `Higher`, `Faster`, `Stronger`, `Cheaper`, and `Broader` as innovation probes, not as a total score or acceptance model. Each score must cite user evidence or a labelled mechanism argument and name a validation experiment. Also check lifecycle, compute, data, engineering, and timeline fit. A high directional score cannot override a CRITICAL flaw.

The next handoff after a viable idea is experiment design or writing, according to whether the evidence contract is ready. Argument-chain checks stay inside the Idea and Writing skills; a separate planning skill is not required. The handoff carries the immutable Claim Lock, active robotics axes, collision findings, evidence obligations, and unresolved gates.

## Experiment-stage distillation

Translate the locked argument into a table with one row per challenge: mechanism intervention, comparator or negative control, metric and independent unit, expected falsification signature, failure log, and artifact. For benchmark/evaluation work, additionally audit five pillars: research gap, construction pipeline, evaluation framework, empirical capability boundaries, and optional companion method. Organise experiments by research question and report findings as bounded, actionable statements. Do not let venue preference add post hoc conditions or change denominators.

## Writing-stage distillation

Reconstruct the paper argument chain from the Research Card and experiment artifacts before drafting. Build an Evidence Map and then the Claim Ledger. For technical papers, use the six-part Introduction logic: background/running example, limitations, goal, challenges, solution overview, contributions. Do not fabricate a running example. For benchmark papers, use the distinct benchmark chain: background/example, evaluation limitations, research questions, design considerations, proposal, contributions. Keep factual prose limited to user materials, verified retrieval, or field common knowledge; never use placeholders to hide unsupported claims. Treat the motivated example, solution overview, and results figures as load-bearing narrative objects, not decoration.

## Review-stage distillation

Start with paradigm and official venue scope. Review macro logic, writing details, grammar, LaTeX, and figure quality, while preserving the robotics axis-specific evidence panels. Every finding needs a real quote, file line, artifact ID, contract path, or source URL. Use `CRITICAL`, `MAJOR`, and `MINOR` honestly; unresolved CRITICAL findings block readiness. Check headline-result attribution, missing canonical or recent works, baseline fairness, running-example consistency, captions, vector export, legibility, honest axes, and AI-tone/format violations. Recommend the next action, not a fabricated acceptance probability.

## Behavioural boundary

The researcher owns direction, problem framing, mechanism, experiment design, interpretation, and final factual verification. AI may search, organise, audit, implement, visualise, and phrase the author's locked substance. No distilled rule may turn the runtime corpus, awards, factor fit, reviewer scores, or venue label into evidence, prestige, or a true acceptance probability.
