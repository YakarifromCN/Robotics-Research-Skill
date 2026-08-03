# Active Task

## User Instruction Verbatim

保留当前实现，只比较 initialization 和 lazy repair。

## Interpreted Objective

Test one local hypothesis without changing the objective.

## Allowed Changes

- `src/controller/initialization.py`
- `src/controller/lazy_repair.py`

## Forbidden Changes

- objective
- primary metric
- raw evidence

## Budget

最多 20 个 episode；遇到核心变化、环境失败或无信息增益时停止。

# English

# Active Task

Preserve the current implementation and compare only initialization and lazy repair.
The compiled task must include the exact user instruction, allowed and forbidden paths,
tests, metrics, budget, completion criteria, and stop/escalation conditions.
