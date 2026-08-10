---
task_id: "ENG-001"
artifact: "TASK"
status: "FROZEN"
language: "zh-CN"
axes: ["C", "S"]
development_modes: ["ROS_REALTIME_INTERFACE"]
risk_tier: "T2"
original_request: "<用户原始工程需求>"
allowed_paths: ["path/to/component"]
forbidden_scope: ["科研主张变化", "无关重构", "未授权真实设备操作"]
steps: ["定位最小修改点", "实现根因修复", "运行冻结测试"]
tests: [{"command": "python3 -m unittest test_component"}]
stop_conditions: ["需要扩大 allowed paths", "安全边界不明确", "冻结测试连续失败"]
safeguards: ["preserve timeout and finite checks"]
expert_required: true
expert_brief: {"affected_call_path": ["entry -> component"], "critical_interfaces": ["existing public interface"], "invariants": ["units, frames, limits and fallback remain unchanged"], "smallest_change_locus": ["path/to/component"], "mandatory_safeguards": ["preserve timeout and finite checks"], "minimal_tests": ["python3 -m unittest test_component"], "blockers": []}
device_actions: []
real_device_authorized: false
---

# <任务名称>执行任务

主实现 Agent 接收用户原始需求、本 Task、必要 expert brief 和直接相关文件。仅执行冻结范围；遇到 stop condition 立即停止。
