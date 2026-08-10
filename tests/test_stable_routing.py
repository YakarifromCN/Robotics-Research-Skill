import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("stable_router", ROOT / "scripts/route_skill_request.py")
ROUTER = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(ROUTER)


class StableRoutingTests(unittest.TestCase):
    def test_forty_canonical_routes(self):
        cases = (
            ("帮我设计验证 TMIR 的负控制实验", "design-robotics-experiment"),
            ("帮我实现 TMIR controller", "develop-robotics-engineering"),
            ("修复这个 ROS subscriber", "develop-robotics-engineering"),
            ("这个结果够不够支持 mechanism claim？", "review-robotic-feedback"),
            ("把现有实验写进论文", "write-robotics-paper"),
            ("这个 idea 是否已有工作覆盖？", "develop-robotics-idea"),
            ("修改 convex QP solver", "develop-robotics-engineering"),
            ("比较 SQP 和 QP 哪个能形成科研贡献", "develop-robotics-idea"),
            ("按照已有 plan 开发 SQP solver", "develop-robotics-engineering"),
            ("design the primary metric for the experiment", "design-robotics-experiment"),
            ("define the trial estimand", "design-robotics-experiment"),
            ("设计随机化实验", "design-robotics-experiment"),
            ("验证 claim 的实验条件怎么设", "design-robotics-experiment"),
            ("fix the impedance controller", "develop-robotics-engineering"),
            ("implement a ROS2 node", "develop-robotics-engineering"),
            ("debug firmware watchdog", "develop-robotics-engineering"),
            ("modify model deployment code", "develop-robotics-engineering"),
            ("修复训练代码的 loss", "develop-robotics-engineering"),
            ("给 ROS node 加一个 timeout 参数", "develop-robotics-engineering"),
            ("修复相机驱动", "develop-robotics-engineering"),
            ("tune controller gains", "develop-robotics-engineering"),
            ("write the paper from frozen results", "write-robotics-paper"),
            ("润色论文但不要改 claim", "write-robotics-paper"),
            ("audit LaTeX numbers in the manuscript", "write-robotics-paper"),
            ("组织 camera-ready 论文", "write-robotics-paper"),
            ("peer review this robotics manuscript", "review-robotic-feedback"),
            ("审稿并标出 critical findings", "review-robotic-feedback"),
            ("审查这个结果的证据是否充分", "review-robotic-feedback"),
            ("reviewer says the claim is too broad", "review-robotic-feedback"),
            ("find prior art for this idea", "develop-robotics-idea"),
            ("这个研究问题是否有 novelty", "develop-robotics-idea"),
            ("形成一个机器人科研贡献", "develop-robotics-idea"),
            ("audit the idea against prior art", "develop-robotics-idea"),
            ("run an overnight autonomous loop", "robotics-ar"),
            ("长时间自动执行已有研究合同", "robotics-ar"),
            ("无人值守持续运行实验迭代", "robotics-ar"),
            ("autonomous loop within the approved task", "robotics-ar"),
            ("开发 ROS realtime controller", "develop-robotics-engineering"),
            ("设计 controller 的 safety 实验", "design-robotics-experiment"),
            ("实现 negative-control ROS node", "develop-robotics-engineering"),
        )
        self.assertEqual(len(cases), 40)
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(ROUTER.route(prompt)["skill"], expected)

    def test_unknown_request_abstains(self):
        self.assertEqual(ROUTER.route("hello there")["decision"], "ABSTAIN")


if __name__ == "__main__":
    unittest.main()
