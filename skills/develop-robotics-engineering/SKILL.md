---
name: develop-robotics-engineering
description: Execute scoped robotics engineering work with the minimum necessary plan, code change, focused tests, and validated plan/task/report/handoff artifacts. Use for control, optimization, learning, perception, ROS, embedded, simulation, hardware-interface, deployment, tuning, tooling code, or an existing engineering plan or handoff. Do not use for scientific experiment design, research ideation, paper writing or review, or autonomous cross-stage research orchestration.
---

# Robotics Engineering

完整理解受影响路径，只实现最小充分改动；输出使用用户当前语言。

## 执行

1. 识别直接执行、既有文档执行、恢复、Bug fix、调参或仅计划；优先读取用户指定的 plan/handoff/设计稿。
2. 运行 `scripts/route_engineering_task.py` 或按 `references/engineering-modes.md` 分别选择机器人轴、开发模式与 T0–T3 风险。
3. T0/T1 或单文件局部修复由当前 Agent 直接完成；T2 多轴或 T3 只创建一个组合轴专家，并将其限定为 reference 中的七字段 brief，专家不改代码、不扩目标。
4. 用 `assets/` 模板生成同一 `task_id` 的最小 Plan/Task。Task 冻结用户原始需求、allowed/forbidden scope、3–7 步、0–3 条原样测试命令、stop conditions 和安全边界。
5. 主实现 Agent 只接收用户需求、Task、必要 expert brief 与直接相关文件；复用现有 helper，修改最少文件，不做无关清理、未来抽象或依赖扩张。
6. 用 `scripts/run_engineering_tests.py` 原样执行冻结测试并保存 receipt；失败只在原范围内修复两次。不得删除测试、放宽断言、伪造 receipt 或把未运行写成 PASS。
7. 生成 Report/Handoff，运行 `scripts/validate_engineering_artifacts.py`。只有工件交叉校验通过才完成。

## 最小性与安全

按已有行为 → helper/config → 标准库/ROS/SDK → 已装依赖 → 局部修改 → 最少新代码选择方案。默认不要求 TDD、worktree、branch、commit、push、review swarm、RFC、ADR 或多 Agent。

- T0：解析/格式；T1：一个 targeted check；T2：targeted + integration smoke；T3：offline/replay/sim + boundary/fallback。
- 保留单位、frame、sign、limit、watchdog、timeout、calibration、shape/timestamp、finite check、solver status、可行性与安全 fallback。
- 真实硬件、flash、erase 或风险升级必须获得明确授权；失败停止，不自动重试。
- 调参一次只改一组参数并记录 before/after，不生成科研结论。

## 边界与 Robotics-AR

Idea/Claim Lock → `develop-robotics-idea`；科学条件、指标、统计 → `design-robotics-experiment`；论文 → `write-robotics-paper`；评审 → `review-robotic-feedback`；显式自治循环 → `robotics-ar`。

当请求为 `AUTONOMOUS_WITHIN_APPROVED_TASK`，继承已批准 Task/Trial Contract、路径、预算与安全边界，自主实现、测试和写回执；不增加 plan/code/stage 审批。仅合同越界、新真实设备权限、安全或预算停止时返回 Robotics-AR。

需要模式、专家 brief 时读取 `references/engineering-modes.md`；创建工件时读取 `references/artifact-contract.md`。

# English

Apply the same numbered contract above using the user's language: separate robotics axes from development modes, use one bounded expert only for multi-axis T2 or T3 work, freeze allowed paths and exact test commands, implement the smallest sufficient change, validate all four artifacts, and preserve real-device authorization and safety boundaries. Robotics-AR invocation remains autonomous inside the already approved task.
