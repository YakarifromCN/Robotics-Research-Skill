---
task_id: "ENG-001"
artifact: "HANDOFF"
status: "DONE"
language: "zh-CN"
axes: ["C", "S"]
risk_tier: "T2"
changed_files: ["path/to/component/controller.py"]
task_contract_sha256: "<与 Report 相同的冻结 Task hash>"
tests: [{"command": "python3 -m unittest test_component", "result": "PASS", "executed": true, "exit_code": 0, "receipt_sha256": "<run_engineering_tests.py 输出>"}]
resume_command: null
---

# <任务名称> Handoff

## 最后稳定状态与风险
冻结 Task 已完成；下一 Agent 可用 task hash、修改文件和测试 receipt 重建状态。DONE/NO_CODE_CHANGE 不编造恢复命令。
