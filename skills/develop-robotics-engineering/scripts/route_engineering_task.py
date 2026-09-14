#!/usr/bin/env python3
"""确定机器人工程轴、开发模式、风险和专家需求。

Route a robotics engineering request to axes, development modes, risk, and expert use.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any


AXIS_RULES = {
    "E": ("urdf", "mjcf", "morphology", "contact", "kinematic", "gripper", "具身", "接触", "运动学"),
    "P": ("camera", "lidar", "sensor", "perception", "estimat", "calibrat", "相机", "传感", "感知", "估计", "标定"),
    "C": ("control", "controller", "mpc", "impedance", "dynamics", "solver", "optimizer", "gain", "控制", "动力学", "优化", "增益"),
    "L": ("dataset", "training", "trainer", "model", "checkpoint", "inference", "学习", "训练", "模型", "推理"),
    "D": ("planner", "planning", "state machine", "scheduler", "规划", "状态机", "调度"),
    "H": ("teleop", "haptic", "xr", "operator", "遥操作", "触觉", "人机"),
    "A": ("deploy", "lifecycle", "recovery", "autonomy", "monitor", "部署", "自主", "恢复", "监控"),
    "S": ("ros", "node", "topic", "service", "action", "tf", "realtime", "firmware", "driver", "build", "实时", "固件", "驱动", "构建"),
}

MODE_RULES = (
    ("EMBEDDED_FIRMWARE", ("firmware", "stm32", "esp32", "flash", "固件", "烧录")),
    ("ROS_REALTIME_INTERFACE", ("ros realtime", "real-time ros", "control rate", "watchdog", "实时控制", "控制频率")),
    ("CONVEX_OPTIMIZER", ("convex", "qp", "quadratic program", "infeasible", "solver", "constraint", "凸优化", "求解器", "约束")),
    ("MODEL_DEPLOYMENT", ("model deploy", "inference deploy", "onnx", "tensorrt", "模型部署", "推理部署")),
    ("ML_TRAINING", ("training", "trainer", "loss", "backward", "训练", "损失")),
    ("ML_DATA_PIPELINE", ("dataset", "dataloader", "data pipeline", "数据集", "数据管道")),
    ("SENSOR_DRIVER", ("sensor driver", "camera driver", "lidar driver", "传感器驱动", "相机驱动")),
    ("SIMULATOR_EXTENSION", ("simulator", "gazebo", "mujoco", "isaac", "仿真")),
    ("HARDWARE_INTERFACE", ("hardware interface", "actuator interface", "hardware sdk", "硬件接口", "执行器接口")),
    ("STATE_MACHINE", ("state machine", "lifecycle", "状态机")),
    ("SYSTEM_TUNING", ("tuning", "gain", "parameter", "调参", "增益", "参数调整")),
    ("ROS_NODE", ("ros", "node", "topic", "service", "action", "launch", "节点")),
    ("CONTROL_LOOP", ("control", "controller", "mpc", "impedance", "控制器", "控制")),
    ("BUILD_TOOLING", ("build", "cmake", "bazel", "container", "tooling", "构建", "工具链")),
)


def _matches(text: str, tokens: tuple[str, ...]) -> bool:
    # 否定只作用于所在子句，路由不授予权限。 / Clause-local negation grants no execution authority.
    clauses = re.split(r"[,;.!?，；。！？]|\bbut\b|但是|但|而是", text)
    for clause in clauses:
        for token in tokens:
            for match in re.finditer(re.escape(token), clause):
                if not re.search(r"\b(?:no|not|never|without|avoid|don't)\b|不要|不修改|不涉及|不运行|无需|禁止|不使用", clause[:match.start()]):
                    return True
    return False


def route(request: str) -> dict[str, Any]:
    text = re.sub(r"\s+", " ", request.casefold()).strip()
    axes = [axis for axis, tokens in AXIS_RULES.items() if _matches(text, tokens)]
    modes = [mode for mode, tokens in MODE_RULES if _matches(text, tokens)]
    if not modes:
        modes = ["BUILD_TOOLING"]
    if not axes:
        axes = ["S"]
    high_risk = _matches(text, ("real robot", "hardware run", "flash", "erase", "firmware", "真实机器人", "烧录", "擦除", "固件"))
    t2_modes = {"CONTROL_LOOP", "CONVEX_OPTIMIZER", "ML_TRAINING", "MODEL_DEPLOYMENT", "ROS_NODE", "ROS_REALTIME_INTERFACE", "SENSOR_DRIVER", "SIMULATOR_EXTENSION", "HARDWARE_INTERFACE", "STATE_MACHINE"}
    risk = "T3" if high_risk or "EMBEDDED_FIRMWARE" in modes else ("T2" if set(modes) & t2_modes else "T1")
    expert_required = risk == "T3" or (risk == "T2" and len(axes) >= 2)
    return {
        "primary_axis": axes[0],
        "secondary_axes": axes[1:3],
        "development_modes": modes[:3],
        "risk_tier": risk,
        "expert_required": expert_required,
        "expert_contract": "bounded_combined_axis_brief" if expert_required else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request")
    args = parser.parse_args()
    print(json.dumps(route(args.request), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
