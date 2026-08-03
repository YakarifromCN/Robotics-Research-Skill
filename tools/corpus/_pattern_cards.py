"""Build the robotics-adapted ResearchStudio pattern-card library.

The upstream paper supplies the 15 reusable operator names and the
cluster-to-card workflow.  This file keeps those names stable while adding a
robotics-specific, transparent adaptation layer.  The 31 tactical cards are
not claimed to be a re-run of the upstream ML clustering; they are seeded
cards whose status stays explicit until full-text robotics signatures are
available.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "corpus" / "researchstudio-pattern-cards.v1.json"


def _parent(
    pattern_id: str,
    name: str,
    alias: str,
    definition: str,
    operational_signature: str,
    when_to_apply: str,
    success_conditions: list[str],
    failure_modes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "pattern_id": pattern_id,
        "level": 1,
        "name": name,
        "plain_language_alias": alias,
        "definition": definition,
        "operational_signature": operational_signature,
        "when_to_apply": when_to_apply,
        "success_conditions": success_conditions,
        "failure_modes": failure_modes or ["The proposed change is not load-bearing or its evidence cannot separate it from a simpler explanation."],
        "source_kind": "researchstudio_parent_operator",
        "status": "transferable_operator_seed",
        "selection_rule": "structural_fit_to_gap_only",
    }


def _sub(
    subpattern_id: str,
    parent_id: str,
    name: str,
    tactical_move: str,
    when_to_apply: str,
    success_conditions: list[str],
    failure_modes: list[str] | None = None,
    upstream_reference: str | None = None,
) -> dict[str, Any]:
    return {
        "subpattern_id": subpattern_id,
        "level": 2,
        "parent_pattern_id": parent_id,
        "name": name,
        "tactical_move": tactical_move,
        "when_to_apply": when_to_apply,
        "success_conditions": success_conditions,
        "failure_modes": failure_modes or ["The proposed change is not load-bearing or its evidence cannot separate it from a simpler explanation."],
        "upstream_reference": upstream_reference,
        "source_kind": "robotics_adapted_tactical_seed",
        "status": "seed_card_requires_full_text_induction",
        "citation_policy": "cite_parent_card_and_current_retrieved_papers; do_not_invent_paper_ids",
    }


PARENTS = [
    _parent("P01", "Audit and Pivot an Assumption", "审计并转向承重假设", "Expose a convention that the field treats as fixed, then replace it with a weaker, testable or structurally different condition.", "Name the inherited assumption; show why it is load-bearing; pivot its locus, strength or representation; test the changed condition.", "Use when several recent methods inherit the same unexamined prerequisite and the proposed change can produce a qualitatively new result.", ["The relaxed condition is exhibited and measurable.", "A tightness, counterexample or mechanism test shows the pivot matters."], ["The result is unchanged after the relaxation.", "An equally strong or unverifiable assumption is smuggled back in."]),
    _parent("P02", "Substitute the Operator or Representation", "替换算子或表示", "Replace the operator, state representation or computational object that carries the bottleneck while preserving the task contract.", "Identify where the old object loses information or creates cost; substitute a new object; isolate the changed object from all other components.", "Use when the task is adequate but the current operator or representation is the binding limitation.", ["The substituted object is load-bearing and mechanistically justified.", "Controls show the gain is not only a larger model or a tuned implementation."]),
    _parent("P03", "Liberate a Fixed Generative Component", "释放固定的生成组件", "Redesign a fixed generator, policy, actuation primitive or synthesis process so it can express the missing behavior.", "Find a component whose output space is fixed; change its generation process or factorization; preserve the surrounding evaluation contract.", "Use when a fixed policy, generator or actuation primitive prevents a desired behavior despite adequate supervision or data.", ["The new process adds a reachable capability rather than another wrapper.", "The component-level change is isolated and its new behavior is characterized."]),
    _parent("P04", "Design a Confound-Isolating Diagnostic", "设计隔离混杂因素的诊断", "Construct a measurement or intervention that separates a claimed mechanism from plausible confounds.", "Name one load-bearing variable; perturb it while holding the remaining interface fixed; predict a downstream outcome and include a semantic control.", "Use when a system result can be explained by sensing, compute, data, tuning, human adaptation or another non-mechanistic confound.", ["The diagnostic changes the downstream outcome, not only a definition of the manipulated variable.", "The negative control is matched in cost and preserves the same surface signal."]),
    _parent("P05", "Unify Heterogeneous Inputs into One Space", "将异质输入统一到一个空间", "Build a shared representation or interface that makes previously incompatible information jointly usable.", "Identify the incompatible modalities, embodiments or agents; define a common state or message space; demonstrate the information is used by the decision or control loop.", "Use when the gap is caused by modality, embodiment, sensor or agent fragmentation rather than a missing predictor alone.", ["The common space preserves task-relevant information across conditions.", "Cross-modal or cross-embodiment controls show that alignment is causal."]),
    _parent("P06", "Reframe as a Solvable Object", "把不可解问题重构成可解对象", "Change the problem object, constraint, state or decomposition so the unresolved question becomes a tractable, falsifiable object.", "State the native intractable formulation; define a solvable surrogate with a conservation or approximation argument; test the gap between the two.", "Use when the native robot problem is underconstrained, combinatorial, long-horizon or physically inaccessible in its current form.", ["The reframe retains the decision-relevant property.", "The approximation error or scope boundary is explicit and measured."]),
    _parent("P07", "Manufacture the Supervisory Signal", "制造监督信号", "Create a trustworthy training or adaptation signal from structure, interaction or outcomes when direct labels are unavailable or misaligned.", "Locate the missing supervisory information; derive it from demonstrations, contrasts, physics, human feedback or self-consistency; validate that it changes the target behavior.", "Use when data exist but the available label, reward or feedback is too sparse, delayed, unsafe or semantically misaligned.", ["The signal is tied to the target mechanism rather than a proxy metric alone.", "A signal-removal or misplacement control returns performance toward baseline."]),
    _parent("P08", "Encode Structure by Construction", "通过构造编码结构", "Put geometry, symmetry, contact, safety, timing or interface structure into the mechanism so it is available before optimization or tuning.", "Name the invariant or constraint; encode it in morphology, representation, controller, architecture or protocol; test behavior outside the construction examples.", "Use when a structural law is known and repeatedly rediscovered by data, or when deployment requires a guarantee that tuning cannot provide.", ["The encoded structure is identifiable and survives held-out conditions.", "A matched unstructured or post-hoc-regularized control shows why construction matters."]),
    _parent("P09", "Prove Equivalence to Unify", "用等价性证明实现统一", "Prove that two apparently different objectives, representations or system formulations are equivalent or linked under explicit conditions.", "State the two objects; derive the mapping and its assumptions; use the equivalence to remove duplicated machinery or expose a new controllable quantity.", "Use when parallel literatures optimize the same object under different names or when a proof can collapse an apparent trade-off.", ["The equivalence is exact in the claimed regime.", "The practical consequence is more than a renamed formulation."]),
    _parent("P10", "Decompose for Differentiated Treatment", "分解并差异化处理", "Split a heterogeneous task, population, trajectory or operating regime and treat its parts according to their distinct constraints.", "Identify the hidden heterogeneity; partition it by a measurable criterion; allocate distinct mechanisms or policies; test the partition boundary.", "Use when one policy, model or controller is forced to average across regimes with incompatible requirements.", ["The partition corresponds to a causal or operational distinction.", "The per-regime treatment beats a single compromise under matched budget."]),
    _parent("P11", "Decompose and Delegate to Solvers", "分解并委托给求解器", "Break a complex decision into typed subproblems and delegate them to specialized planners, learned modules, agents or tools.", "Define the subproblem interfaces; assign each solver a responsibility; verify composition and recovery when a solver fails.", "Use when a long-horizon or multi-agent problem contains reusable subproblems with different algorithmic structure.", ["Interfaces expose enough state for the delegated solver.", "End-to-end gain remains after accounting for coordination and failure recovery."]),
    _parent("P12", "Relax Discrete Search to Continuous", "把离散搜索松弛为连续搜索", "Replace an intractable discrete search with a continuous surrogate that preserves the decision-relevant objective and can be rounded or recovered.", "Specify the discrete object; build a continuous relaxation; characterize the relaxation gap and recovery procedure.", "Use when planning, allocation or design is combinatorial but its geometry admits a meaningful continuous proxy.", ["The recovered solution respects the original constraints.", "The relaxation gives a measurable benefit without hiding an exponential post-process."]),
    _parent("P13", "Adapt by Conditioning, Not Retraining", "通过条件化而非重训练实现适应", "Adapt behavior through context, system identification or conditioning while keeping the core model or policy fixed.", "Expose the changing context; encode it as a condition or online estimate; test adaptation under distribution shift and frozen-core controls.", "Use when online changes are real but full retraining is too slow, unsafe, data hungry or difficult to certify.", ["The condition captures the shift that matters.", "The frozen-core control and recovery test separate adaptation from memorization."]),
    _parent("P14", "Characterize a Limit, Then Surpass It", "刻画极限后超越它", "First establish a boundary imposed by a current formulation, then show a principled mechanism that exceeds or exactly meets it.", "State the old limit; prove or measure it under the same regime; introduce one change; show a strict and reproducible improvement.", "Use when a field has a sharp stability, planning, sample, sensing, bandwidth or safety boundary that can be made explicit.", ["The limit is real under a matched baseline.", "The improvement is outside uncertainty and the mechanism explains why the boundary moved."]),
    _parent("P15", "Design a Property-Targeting Pretext Objective", "设计针对性质的预训练目标", "Construct a pretext or auxiliary objective that targets a property the downstream robot must preserve, rather than generic prediction alone.", "Name the downstream property; create a pretext that makes it observable; verify transfer and remove the auxiliary objective as a control.", "Use when the desired property is latent, expensive to label or poorly represented by generic self-supervision.", ["The pretext predicts the property that matters downstream.", "A matched generic pretext does not explain the transfer gain."]),
]


SUBPATTERNS = [
    _sub("R01", "P01", "Relocate the load-bearing locus", "Move the enforcement, sensing or control locus to an overlooked state, interface or representation.", "Use when every prior method assumes the same location contains the decisive signal.", ["The new locus is structurally distinct and observable.", "An informed adversary or disturbance cannot erase the signal at the same cost."], ["The new locus was already used by a close paper.", "The move only changes implementation vocabulary."], "ResearchStudio Appendix C01"),
    _sub("R02", "P01", "Remove a fixed model assumption", "Replace a required model, calibration or distributional assumption with a weaker observable condition.", "Use when the robot must operate under unknown contact, friction, terrain or dynamics.", ["The weaker condition occurs in the target operating envelope.", "A tightness or failure-case analysis shows the removed assumption was binding."], ["An equally strong hidden model is reintroduced."]),
    _sub("R03", "P01", "Replace a distributional condition with a structural one", "Move from a fragile statistical prior to a geometric, architectural or interface constraint.", "Use when data coverage is insufficient but physical or system structure is reliable.", ["The structural condition is independently testable.", "The replacement transfers across environments without copying a distribution."], ["The structural condition is merely a renamed distributional assumption."]),
    _sub("R04", "P01", "Characterize the adversarial boundary", "Treat a claimed safety, robustness or imperceptibility property as a budget that can be challenged.", "Use when the operating or threat model is stronger than the paper's nominal test.", ["The strongest relevant disturbance or operator is included.", "The boundary yields a reusable design constraint."], ["Only a static or weak adversary is tested."]),
    _sub("R05", "P01", "Pivot the system interface", "Move the load-bearing computation across a sensing, communication, human or actuation interface.", "Use when interface latency, bandwidth or authority is the inherited bottleneck.", ["The interface change is isolated from downstream tuning.", "The new interface changes end-to-end behavior."], ["The interface is changed without a causal account."]),
    _sub("R06", "P01", "Isolate a failure-causing convention", "Turn a field convention into an intervention and measure the failure it causes.", "Use when benchmark success hides a known deployment failure.", ["The intervention reproduces the failure and its repair.", "The result generalizes beyond one example."], ["The failure is anecdotal or benchmark-specific."]),
    _sub("R07", "P02", "Low-sensitivity operator substitution", "Replace an operator whose output is overly sensitive to noise, contact or discretization.", "Use when the same task has a brittle operator-level failure.", ["Sensitivity is measured at matched compute.", "The replacement preserves the task interface."], ["The gain is only a larger or more heavily tuned model."], "ResearchStudio C09 Low-Sensitivity Operator Substitution"),
    _sub("R08", "P02", "Curvature-object substitution", "Substitute a scalar or local object with curvature, geometry or distributional structure that preserves the missing signal.", "Use when point estimates discard the signal needed for robust state or control.", ["The extra object has a mechanistic interpretation.", "A point-estimate control loses the claimed downstream benefit."], ["The richer object is used only as an unexamined feature."], "ResearchStudio C30 Curvature-Object Substitution"),
    _sub("R09", "P02", "Representation-level state substitution", "Replace the state representation used by estimation, planning or learning.", "Use when the raw state is not invariant to embodiment, viewpoint or contact.", ["The representation removes a named nuisance without deleting the task signal.", "Held-out conditions test invariance."], ["The representation is an opaque embedding with no failure boundary."]),
    _sub("R10", "P02", "Contact and geometry operator substitution", "Replace a contact, collision or geometry operation with one that exposes the relevant physical object.", "Use when contact-rich manipulation or non-Euclidean planning is bottlenecked by a standard operator.", ["The operation is validated on the physical boundary cases.", "A geometric or force control explains the improvement."], ["The operator is a cosmetic reparameterization."]),
    _sub("R11", "P03", "Generative process redesign", "Change how actions, trajectories or forces are generated instead of adding a downstream correction.", "Use when a fixed policy or generator cannot express the required behavior.", ["The reachable behavior set expands.", "Equal-data and equal-compute controls isolate the generator change."], ["The generator is only wrapped by off-the-shelf modules."], "ResearchStudio generative process redesign"),
    _sub("R12", "P03", "Residual mechanism liberation", "Expose the physical or modeling residual that a fixed generator cannot explain.", "Use when sim-to-real, friction, contact or dynamics residuals dominate the error.", ["The residual is measurable and closed by the mechanism.", "A residual-removal control returns performance toward baseline."], ["The residual model becomes a generic error-corrector with no mechanism."]),
    _sub("R13", "P03", "Policy-generation substrate redesign", "Change the substrate or factorization from which a policy generates actions.", "Use when policy expressivity or long-horizon composition is limiting deployment.", ["The factorization matches the action horizon or morphology.", "The policy remains stable under perturbation."], ["Scaling or data alone explains the result."]),
    _sub("R14", "P04", "Controlled diagnostic construction", "Build a one-variable-isolated intervention or measurement instrument.", "Use when a robot claim can be explained by hardware, data, tuning or human adaptation confounds.", ["The intervention has a downstream prediction.", "Controls are matched in cost and information."], ["Only the intermediate metric changes, not the task outcome."], "ResearchStudio C02 Controlled Diagnostic Construction"),
    _sub("R15", "P05", "Cross-modal shared representation", "Align vision, touch, language, proprioception or force into a task-usable state.", "Use when modalities are complementary but not jointly actionable.", ["Each modality has a leave-one-out test.", "Alignment improves a downstream decision rather than only retrieval similarity."], ["The common space is a concatenation with no causal use."]),
    _sub("R16", "P06", "Sequential-control re-casting", "Recast long-horizon control as a sequence of measurable subgoals or phases.", "Use when a single objective dilutes credit or hides the decisive phase.", ["The phase boundaries are observable.", "The re-casting improves the long-horizon outcome."], ["The phases are arbitrary labels with no mechanism."], "ResearchStudio C21 Sequential-Control Re-Casting"),
    _sub("R17", "P06", "Intractable-problem re-casting", "Turn a native intractable planning or contact problem into a solvable object with a bounded gap.", "Use when direct optimization is combinatorial, discontinuous or physically inaccessible.", ["The solvable object preserves the decision-relevant property.", "The approximation or recovery error is characterized."], ["The reframe is a renamed heuristic."], "ResearchStudio C27 Intractable-Problem Re-Casting"),
    _sub("R18", "P06", "Feasibility-object re-casting", "Replace an open-ended deployment goal with an explicit operating envelope and feasibility object.", "Use when field performance fails because the target was never bounded.", ["The envelope is measurable before deployment.", "The resulting claim is falsifiable and transferable."], ["The envelope is selected after seeing the result."]),
    _sub("R19", "P07", "Self-supervised signal engineering", "Derive supervision from temporal, geometric, cross-view or task consistency.", "Use when robot labels are expensive but structure is observable.", ["The pretext signal is tied to the downstream property.", "Signal removal degrades the intended behavior."], ["The pretext is generic and unrelated to the task."]),
    _sub("R20", "P07", "Residual and latent supervisory signal", "Use model residuals, uncertainty or latent disagreement as the training/adaptation signal.", "Use when the error itself identifies where the policy or estimator must change.", ["The residual predicts the downstream correction.", "A shuffled or detached residual is a negative control."], ["Residual magnitude is optimized as a proxy with no task effect."]),
    _sub("R21", "P07", "Human or environment feedback as supervision", "Convert intervention, preference, success/failure or contact feedback into a stable learning signal.", "Use when direct reward or labels are absent but the robot already interacts.", ["Feedback cost and operator burden are measured.", "The signal improves behavior without eroding safety or trust."], ["The system treats feedback as free or ignores operator adaptation."]),
    _sub("R22", "P08", "Symmetry-group construction", "Encode a symmetry or invariance into the state, model or controller.", "Use when changes of frame, viewpoint, embodiment or ordering should not change the decision.", ["The symmetry is tested outside training transforms.", "Breaking the symmetry produces the predicted failure."], ["The claimed symmetry is not present in the physical task."], "ResearchStudio C16 Symmetry-Group Construction"),
    _sub("R23", "P08", "Relational topology encoded as structure", "Encode contact, graph, topology or relational geometry as a structural prior.", "Use when relations, not individual observations, determine the robot outcome.", ["The relation is identifiable over standard alternatives.", "A topology-free control fails on the same boundary cases."], ["A topology-as-prior architecture is presented without isolating its work."], "ResearchStudio C13 Relational-Topology Encoded as Structure"),
    _sub("R24", "P08", "Embodiment and contact constraint by construction", "Build morphology, compliance, contact or actuator constraints directly into the robot mechanism or controller.", "Use when embodiment is the source of the capability, not merely a test platform.", ["The body–task mechanism is explicit.", "A matched embodiment or post-hoc control baseline isolates the construction."], ["One hardware instance is generalized to all embodiments without evidence."]),
    _sub("R25", "P09", "Equivalence-based objective unification", "Prove that two control, learning or planning objectives are equivalent in a named regime.", "Use when a duplicated objective or apparent trade-off blocks a simpler design.", ["The assumptions are explicit.", "The equivalence yields a simpler or more powerful robot procedure."], ["The proof only renames the objective."], "ResearchStudio C06 Probabilistic-Objective Unification via Equivalence Proof"),
    _sub("R26", "P10", "Heterogeneous regime decomposition", "Split contact, terrain, object, user or agent regimes and allocate distinct treatment.", "Use when a single controller or policy averages incompatible regimes.", ["The partition variable is measurable online or at design time.", "A single-policy control fails under the same budget."], ["The partition is tuned after results or has no operational meaning."]),
    _sub("R27", "P11", "Decompose and delegate to solvers", "Give typed subproblems to specialized planners, learned policies, agents or tools.", "Use when planning or coordination contains separable subproblems.", ["Interfaces and failure recovery are explicit.", "Coordination cost is included in the end-to-end evaluation."], ["A pipeline of modules is called a contribution without a unifying interface."]),
    _sub("R28", "P12", "Discrete-search relaxation to continuous", "Relax combinatorial planning or allocation into a differentiable or continuous object with recovery.", "Use when a discrete robot decision has exploitable geometry.", ["Rounded decisions remain feasible.", "The relaxation gap is measured."], ["The post-process secretly solves the original problem at full cost."]),
    _sub("R29", "P13", "Adapt by conditioning", "Condition a frozen core on the current robot, environment, user or task state.", "Use when the shift is local, recurrent and observable online.", ["The condition is causally tied to the shift.", "Frozen-core, no-adaptation and recovery tests are included."], ["The method retrains while calling it conditioning."]),
    _sub("R30", "P14", "Limit characterization and strict surpass", "Establish a stability, safety, bandwidth, sample or planning boundary, then exceed it with a named mechanism.", "Use when a matched baseline has a sharp and reproducible boundary.", ["The boundary is measured under the same regime.", "The improvement exceeds uncertainty and has a mechanism."], ["Only an empirical improvement is shown with no boundary or tightness."]),
    _sub("R31", "P15", "Property-targeting pretext objective", "Train on the robot property that must transfer: contact, invariance, uncertainty, affordance or safety.", "Use when generic self-supervision does not represent the property needed downstream.", ["The pretext targets a measurable task property.", "A generic-pretext control and property-removal control are both present."], ["The property is named after the result or is not observable."], "ResearchStudio targeted self-supervised objective"),
]


AXIS_PROFILES: dict[str, dict[str, Any]] = {
    "E": {
        "axis_name": "embodiment_contact",
        "axis_name_zh": "具身形态与接触",
        "strategy_signature_template": "Encode the load-bearing body, material and contact constraint into the mechanism, then isolate its contribution against matched embodiment and control alternatives.",
        "keyword_terms": ["mechanism-to-body mapping", "contact or morphology condition", "hardware boundary", "morphology", "compliance", "contact", "mechanics", "embodied"],
        "pattern_scores": {"P08": {"prior": 1.00, "terms": ["mechanism-to-body mapping", "contact or morphology condition", "hardware boundary", "morphology", "compliance", "contact", "mechanics", "embodied"]}, "P02": {"prior": 0.86, "terms": ["operator", "representation", "residual physics", "geometry", "force", "model"]}, "P04": {"prior": 0.78, "terms": ["stress", "failure", "boundary", "validation", "contact"]}},
        "preferred_pattern_ids": ["P08", "P02", "P04"],
        "preferred_subpattern_ids": ["R24", "R10", "R14"],
        "evidence_recipe": ["mechanism-to-body map", "matched non-embodied or post-hoc-control comparator", "contact/morphology stress sweep", "cross-platform or boundary test"],
        "failure_guard": "Do not generalize from one morphology or hardware instance without a mechanism boundary and an explicit transfer test.",
        "venue_scope_tags": ["robotics", "mechatronics", "manipulation", "bioinspired", "hardware", "contact"],
        "claim_altitude": "embodied mechanism or morphology-to-task principle",
    },
    "P": {
        "axis_name": "perception_state",
        "axis_name_zh": "感知与状态估计",
        "strategy_signature_template": "Design a confound-isolating sensing-to-state diagnostic, and use calibrated or shared representations only when they change a downstream robot decision.",
        "keyword_terms": ["sensor-to-state pipeline", "calibration or representation choice", "perception failure case", "observability", "identifiability", "uncertainty", "multimodal", "sensing", "mapping"],
        "pattern_scores": {"P04": {"prior": 1.00, "terms": ["sensor-to-state pipeline", "calibration or representation choice", "perception failure case", "observability", "identifiability", "uncertainty", "failure", "diagnostic"]}, "P05": {"prior": 0.92, "terms": ["multimodal", "vision and touch", "shared", "sensor", "mapping", "representation", "lidar"]}, "P08": {"prior": 0.80, "terms": ["manifold", "graph", "geometry", "topology", "structure"]}},
        "preferred_pattern_ids": ["P04", "P05", "P08"],
        "preferred_subpattern_ids": ["R14", "R15", "R23"],
        "evidence_recipe": ["sensor-to-state causal diagram", "leave-one-sensor-out and calibration controls", "failure-case stratification", "held-out scene/robot/domain test"],
        "failure_guard": "Do not report a perception metric gain as a robotics contribution unless the changed state alters task, control or safety outcomes.",
        "venue_scope_tags": ["perception", "computer_vision", "3d_perception", "sensing", "multisensor", "localization", "uncertainty"],
        "claim_altitude": "state representation, observability or perception-to-action mechanism",
    },
    "C": {
        "axis_name": "control_dynamics",
        "axis_name_zh": "控制、动力学与安全",
        "strategy_signature_template": "Audit the inherited model, stability or safety assumption, characterize its boundary, and show a matched mechanism-level improvement under disturbance.",
        "keyword_terms": ["dynamics or controller mechanism", "stability/safety condition", "stress or disturbance test", "uncertainty", "risk", "barrier", "fault", "disturbance", "control"],
        "pattern_scores": {"P01": {"prior": 1.00, "terms": ["dynamics or controller mechanism", "stability/safety condition", "unknown", "uncertainty", "risk", "model-less", "fault", "assumption", "barrier"]}, "P14": {"prior": 0.95, "terms": ["tight", "bound", "limit", "stability", "safety", "optimal", "barrier", "formal"]}, "P04": {"prior": 0.84, "terms": ["stress or disturbance test", "fault", "uncertainty", "test", "failure"]}},
        "preferred_pattern_ids": ["P01", "P14", "P04"],
        "preferred_subpattern_ids": ["R02", "R30", "R14"],
        "evidence_recipe": ["assumption-to-equation map", "stability/safety proof or certificate", "matched disturbance and uncertainty sweep", "semantic negative control on the load-bearing variable"],
        "failure_guard": "Do not call a controller safe or robust from nominal trajectories; identify the boundary and test the intervention on downstream failure.",
        "venue_scope_tags": ["control", "dynamics", "stability", "optimization", "safety", "guidance_navigation_control", "networked_control"],
        "claim_altitude": "dynamical mechanism, stability/safety certificate or control law",
    },
    "L": {
        "axis_name": "learning_adaptation",
        "axis_name_zh": "学习、表示与适应",
        "strategy_signature_template": "Manufacture a task-relevant supervisory signal or redesign the policy-generation substrate, then prove transfer with signal-removal and held-out embodiment or task tests.",
        "keyword_terms": ["training or adaptation loop", "data/representation dependency", "held-out or transfer test", "self-supervision", "residual", "policy", "adaptation", "feedback", "learning"],
        "pattern_scores": {"P07": {"prior": 1.00, "terms": ["training or adaptation loop", "self-supervision", "supervisory", "residual", "feedback", "help", "uncertainty", "learning"]}, "P03": {"prior": 0.92, "terms": ["generative", "diffusion", "residual", "policy", "behavior", "action generation"]}, "P05": {"prior": 0.90, "terms": ["language", "multimodal", "correspondence", "feature", "cross robot", "shared", "representation"]}},
        "preferred_pattern_ids": ["P07", "P03", "P05"],
        "preferred_subpattern_ids": ["R19", "R12", "R15"],
        "evidence_recipe": ["signal provenance and mechanism map", "signal-removal or shuffled-signal control", "same-data/compute baseline", "held-out task, embodiment or environment transfer"],
        "failure_guard": "Do not present scale, data or a benchmark gain as a learning mechanism without isolating the supervisory signal or policy substrate that caused it.",
        "venue_scope_tags": ["robot_learning", "learning", "reinforcement_learning", "imitation_learning", "representation_learning", "foundation_model", "vla", "world_model"],
        "claim_altitude": "learning signal, policy-generation mechanism or transfer principle",
    },
    "D": {
        "axis_name": "planning_decision_coordination",
        "axis_name_zh": "规划、决策与协同",
        "strategy_signature_template": "Decompose heterogeneous long-horizon decision structure into typed subproblems, delegate or relax them with explicit interface and recovery guarantees.",
        "keyword_terms": ["planning/decision decomposition", "task or coordination constraint", "long-horizon failure case", "decomposition", "coordination", "multi-robot", "solver", "sampling", "planning"],
        "pattern_scores": {"P10": {"prior": 1.00, "terms": ["planning/decision decomposition", "task or coordination constraint", "decomposition", "multi-robot", "coordination", "long horizon", "heterogeneous"]}, "P11": {"prior": 0.90, "terms": ["delegate", "solver", "symbolic", "blackbox", "multi-agent", "communication", "coordination"]}, "P06": {"prior": 0.86, "terms": ["intractable", "mapless", "generalization", "single demonstration", "recast", "unknown"]}},
        "preferred_pattern_ids": ["P10", "P11", "P06"],
        "preferred_subpattern_ids": ["R26", "R27", "R18"],
        "evidence_recipe": ["task/decision decomposition", "typed state and solver interfaces", "coordination and recovery tests", "long-horizon or multi-agent stress cases"],
        "failure_guard": "Do not call a pipeline a planning contribution when the subproblem interfaces, coordination cost or failure recovery are unspecified.",
        "venue_scope_tags": ["planning", "task_motion_planning", "reasoning", "multi_agent", "multi_robot", "coordination", "scheduling", "decision"],
        "claim_altitude": "planning decomposition, coordination protocol or long-horizon decision mechanism",
    },
    "H": {
        "axis_name": "human_interaction",
        "axis_name_zh": "人机交互、触觉与 XR",
        "strategy_signature_template": "Construct a confound-isolating interaction or haptic diagnostic whose load-bearing interface changes human–robot behavior, workload, trust or physical safety.",
        "keyword_terms": ["human or haptic interaction mechanism", "participant/operator measure", "interface or workload boundary", "human factors", "cognitive load", "trust", "operator", "feedback", "participant"],
        "pattern_scores": {"P04": {"prior": 1.00, "terms": ["human or haptic interaction mechanism", "participant/operator measure", "interface or workload boundary", "human factors", "cognitive load", "trust", "operator", "participant"]}, "P05": {"prior": 0.86, "terms": ["shared", "haptic", "multimodal", "human robot", "language", "preference", "feedback"]}, "P01": {"prior": 0.78, "terms": ["delay", "uncertainty", "safety", "control barrier", "failure", "boundary"]}},
        "preferred_pattern_ids": ["P04", "P05", "P01"],
        "preferred_subpattern_ids": ["R14", "R15", "R05"],
        "evidence_recipe": ["interaction mechanism and authority map", "counterbalanced participant/operator study", "matched workload/trust/safety measures", "delay, novice, expert and failure-boundary tests"],
        "failure_guard": "Do not submit a robot method plus a small user demo to an HRI/HCI venue; the interaction mechanism and human measure must be the contribution.",
        "venue_scope_tags": ["hri", "haptics", "force_feedback", "teleoperation", "human_factors", "user_study", "virtual_reality", "augmented_reality", "social_robotics"],
        "claim_altitude": "interaction mechanism, haptic channel or human-factor effect",
    },
    "A": {
        "axis_name": "autonomy_deployment",
        "axis_name_zh": "自主系统与部署运行",
        "strategy_signature_template": "Recast an open deployment goal as a measurable operating envelope, then adapt or diagnose the autonomy loop under real field constraints and recovery failures.",
        "keyword_terms": ["autonomy loop", "operating-envelope condition", "deployment or field failure", "mapless", "field", "deployment", "operating", "unknown", "autonomy"],
        "pattern_scores": {"P06": {"prior": 1.00, "terms": ["autonomy loop", "operating-envelope condition", "deployment or field failure", "mapless", "field", "deployment", "operating", "unknown", "reframe"]}, "P13": {"prior": 0.90, "terms": ["online adaptation", "on the job", "conditioned", "human in the loop", "transfer", "adaptation"]}, "P04": {"prior": 0.86, "terms": ["risk", "occlusion", "failure", "safety", "test", "operating envelope"]}},
        "preferred_pattern_ids": ["P06", "P13", "P04"],
        "preferred_subpattern_ids": ["R18", "R29", "R14"],
        "evidence_recipe": ["explicit operating-envelope definition", "closed-loop field or simulator-to-real test", "recovery and failure logging", "frozen-core or no-adaptation control"],
        "failure_guard": "Do not equate a single successful run with autonomy; bound the envelope, report recoveries and expose the deployment failure mode.",
        "venue_scope_tags": ["autonomy", "autonomous_systems", "navigation", "field", "deployment", "intelligent_vehicle", "unmanned_systems", "industrial_robotics"],
        "claim_altitude": "autonomy loop, operating envelope or deployment mechanism",
    },
    "S": {
        "axis_name": "systems_realtime",
        "axis_name_zh": "系统集成、实时与基础设施",
        "strategy_signature_template": "Encode the software–hardware, timing and reproducibility contract into the system architecture, then diagnose end-to-end latency, failure propagation and deployment behavior.",
        "keyword_terms": ["software/hardware contract", "latency or resource measure", "reproduction/deployment artifact", "architecture", "middleware", "runtime", "contract", "reproducibility", "security"],
        "pattern_scores": {"P08": {"prior": 1.00, "terms": ["software/hardware contract", "latency or resource measure", "reproduction/deployment artifact", "architecture", "middleware", "runtime", "contract", "reproducibility"]}, "P04": {"prior": 0.91, "terms": ["runtime verification", "security", "failure", "latency", "monitor", "diagnostic"]}, "P11": {"prior": 0.82, "terms": ["modular", "distributed", "framework", "cloud", "fog", "component", "delegation"]}},
        "preferred_pattern_ids": ["P08", "P04", "P11"],
        "preferred_subpattern_ids": ["R24", "R14", "R27"],
        "evidence_recipe": ["component and interface contract", "end-to-end latency/resource/fault propagation trace", "reproducible artifact or deployment recipe", "failure injection and recovery test"],
        "failure_guard": "Do not present an architecture diagram as a systems contribution without reproducible artifacts and load-bearing end-to-end measurements.",
        "venue_scope_tags": ["systems", "real_time", "embedded", "middleware", "distributed", "robotics_software", "hardware_software", "automation", "reproducibility"],
        "claim_altitude": "integrated system, real-time contract or reproducible infrastructure",
    },
}


def build_library() -> dict[str, Any]:
    return {
        "schema_version": "researchstudio-robotics-pattern-cards.v1",
        "library_id": "ROBOTICS-RESEARCHSTUDIO-15-31",
        "provenance": {
            "method_source": "assets/ResearchStudio.pdf",
            "method_paper": "https://arxiv.org/abs/2607.04439v1",
            "upstream_operator_count": 15,
            "upstream_tactical_cluster_count": 31,
            "adaptation_note": "Parent operator names and workflow are transferred; tactical cards and axis profiles are robotics adaptations, not a claim of upstream robotics clustering.",
        },
        "selection_contract": {
            "pattern_role": "diagnostic operator and evidence recipe",
            "selection": "fit the diagnosed structural gap before considering frequency or venue context",
            "composition": {"min": 1, "max": 3, "default": 2},
            "outcome_signal": "descriptive audit context only; no acceptance probability",
            "directness_weight": "optional venue-routing prior only; no rating or prestige field",
        },
        "main_patterns": PARENTS,
        "subpatterns": SUBPATTERNS,
        "axis_profiles": AXIS_PROFILES,
        "validation_expectations": {
            "required_for_full_induction": ["full-text or abstract-backed Stage-1 fields", "domain-agnostic Stage-2 rewrites", "embedding manifest", "UMAP/HDBSCAN run metadata", "cluster audit", "outcome labels with provenance"],
            "current_corpus_status": "metadata_adapter_only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the robotics ResearchStudio pattern-card library.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_library(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
