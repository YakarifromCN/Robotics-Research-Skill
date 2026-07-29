"""Build the balanced public robotics-paper metadata corpus.

This is a curated, reproducible metadata build rather than a claim that the
papers were sampled by a statistical estimator.  The list is deliberately
stratified by the eight semantic robotics submanifold axes and by venue kind:
50 journal records and 50 conference records, with each kind covering every
axis as evenly as possible.  The public paper link is an open preprint,
accepted manuscript, repository copy, or open full-text record; the second
link points to the final venue record.

Award quota semantics are explicit: ``winner`` and ``finalist`` are both
recognized award signals.  A finalist is never rewritten as a winner.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "corpus" / "public-paper-index.json"
CHECKED_AT = "2026-07-29"
AXES = ("E", "P", "C", "L", "D", "H", "A", "S")

RAS_RAL_AWARDS = "https://www.ieee-ras.org/awards-recognition/publications-awards/ieee-robotics-and-automation-letters-best-paper-award/"
RAS_TRO_AWARDS = "https://www.ieee-ras.org/awards-recognition/publications-awards/ieee-transactions-on-robotics-king-sun-fu-memorial-best-paper-award/"
ICRA_AWARDS = "https://www.ieee-ras.org/awards-recognition/conference-awards/ieee-icra-best-conference-paper-award/"
RSS_2022_AWARDS = "https://roboticsconference.org/2022/program/awards/"
RSS_2023_AWARDS = "https://roboticsconference.org/2023/program/awards/"
CORL_2023_AWARDS = "https://www.corl2023.org/awards"

PRESENTATION_SOURCES = {
    "RSS": "https://roboticsconference.org/2023/information/presenters/",
    "CoRL": "https://www.corl2023.org/papers",
    "ICRA": ICRA_AWARDS,
    "IROS": "https://www.iros2022.org/program/",
    "CVPR": "https://cvpr.thecvf.com/Conferences/2023/Program",
    "HRI": "https://humanrobotinteraction.org/2024/accepted-papers/",
    "CASE": "https://www.ieee-ras.org/conferences-workshops/fully-sponsored/ieee-case",
    "ITSC": "https://2023.ieee-itsc.org/program/",
    "ICAPS": "https://icaps-conference.org/",
    "AAMAS": "https://www.aamas2024-conference.au/",
    "NeurIPS": "https://neurips.cc/Conferences/2017/Schedule",
    "DSN": "https://dsn2020-2020.codaspy.org/program/",
    "Runtime Verification": "https://rv2020.inf.unibz.it/",
}

AXIS_DEFAULTS = {
    "E": ("embodiment", "contact", "morphology"),
    "P": ("perception", "state_estimation", "sensing"),
    "C": ("control", "dynamics", "safety"),
    "L": ("robot_learning", "adaptation", "representation"),
    "D": ("planning", "decision", "coordination"),
    "H": ("hri", "haptics", "teleoperation"),
    "A": ("autonomy", "deployment", "field_operation"),
    "S": ("robotics_software", "real_time", "reproducibility"),
}

AXIS_EXTRACTS = {
    "E": ("mechanism-to-body mapping", "contact or morphology condition", "hardware boundary"),
    "P": ("sensor-to-state pipeline", "calibration or representation choice", "perception failure case"),
    "C": ("dynamics or controller mechanism", "stability/safety condition", "stress or disturbance test"),
    "L": ("training or adaptation loop", "data/representation dependency", "held-out or transfer test"),
    "D": ("planning/decision decomposition", "task or coordination constraint", "long-horizon failure case"),
    "H": ("human or haptic interaction mechanism", "participant/operator measure", "interface or workload boundary"),
    "A": ("autonomy loop", "operating-envelope condition", "deployment or field failure"),
    "S": ("software/hardware contract", "latency or resource measure", "reproduction/deployment artifact"),
}

AXIS_LIMITS = {
    "E": "one morphology/contact design does not prove all embodiments",
    "P": "one sensor or dataset does not prove broad perceptual validity",
    "C": "stability or performance is conditional on stated dynamics and disturbances",
    "L": "training success does not prove out-of-distribution generalization",
    "D": "one task plan does not prove arbitrary long-horizon competence",
    "H": "a user study or teleoperation demo does not prove general human benefit",
    "A": "a deployment demo does not prove reliability across the full operating envelope",
    "S": "an artifact or benchmark does not prove reproducibility on every platform",
}


def axis_vector(primary: str, secondary: Iterable[str] = ()) -> dict[str, int]:
    vector = {axis: 0 for axis in AXES}
    vector[primary] = 3
    for axis in secondary:
        if axis in vector and axis != primary:
            vector[axis] = 2
    return vector


def award(status: str, source_url: str, evidence_note: str) -> dict[str, object]:
    return {
        "qualifies_for_quota": True,
        "status": status,
        "source_url": source_url,
        "evidence_note": evidence_note,
    }


def presentation(venue: str, level: str = "oral", note: str = "Curated from the venue program/award record.") -> dict[str, str]:
    source = PRESENTATION_SOURCES.get(venue, "https://www.ieee-ras.org/conferences-workshops")
    return {"level": level, "source_url": source, "evidence_note": note}


def paper(
    paper_id: str,
    title: str,
    year: int,
    venue: str,
    kind: str,
    primary: str,
    preprint_url: str,
    final_url: str,
    *,
    secondary: Iterable[str] = (),
    tags: Iterable[str] = (),
    extract: Iterable[str] = (),
    limit: str | None = None,
    award_info: dict[str, object] | None = None,
    presentation_info: dict[str, str] | None = None,
    public_kind: str = "open_preprint_or_accepted_manuscript",
) -> dict[str, object]:
    if primary not in AXES:
        raise ValueError(f"unsupported primary axis: {primary}")
    record: dict[str, object] = {
        "paper_id": paper_id,
        "title": title,
        "year": year,
        "venue": venue,
        "venue_kind": kind,
        "primary_axis": primary,
        "submanifold_axes": axis_vector(primary, secondary),
        "preprint": {"url": preprint_url, "kind": public_kind, "checked_at": CHECKED_AT},
        "final_publication": {"url": final_url, "kind": "final_venue_record", "checked_at": CHECKED_AT},
        "pattern_tags": list(tags) or list(AXIS_DEFAULTS[primary]),
        "extract": list(extract) or list(AXIS_EXTRACTS[primary]),
        "do_not_infer": [limit or AXIS_LIMITS[primary]],
    }
    if award_info is not None:
        record["award"] = award_info
    if kind == "conference":
        if presentation_info is None:
            presentation_info = presentation(venue)
        record["presentation"] = presentation_info
    return record


def build_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    # Journals: E/P/C/L/D/H/A/S = 7/7/6/6/6/6/6/6.
    records.extend(
        [
            paper("J-E01", "Design and Control of Concentric-Tube Robots", 2010, "IEEE Transactions on Robotics", "journal", "E", "https://dash.harvard.edu/handle/1/37372563", "https://doi.org/10.1109/TRO.2009.2035740", secondary=("C",), tags=("continuum_robot", "mechanics", "surgical_robotics"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award.")),
            paper("J-E02", "Compliant Aerial Manipulators: Toward a New Generation of Aerial Robotic Workers", 2017, "IEEE Robotics and Automation Letters", "journal", "E", "https://research.utwente.nl/en/publications/8d934700-5acf-4cbb-9417-8c71ecf07a42", "https://doi.org/10.1109/LRA.2016.2519948", secondary=("C", "A"), tags=("aerial_manipulation", "compliance", "morphology"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-E03", "Inverted and Inclined Climbing Using Capillary Adhesion in a Quadrupedal Insect-Scale Robot", 2020, "IEEE Robotics and Automation Letters", "journal", "E", "https://smrl.mit.edu/wp-content/uploads/2020/09/crawler_chen_2020.pdf", "https://doi.org/10.1109/LRA.2020.3003870", secondary=("C",), tags=("insect_scale_robot", "adhesion", "locomotion"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-E04", "Sim-to-Real of Soft Robots With Learned Residual Physics", 2024, "IEEE Robotics and Automation Letters", "journal", "E", "https://arxiv.org/abs/2402.01086", "https://doi.org/10.1109/LRA.2024.3446287", secondary=("L", "C"), tags=("soft_robot", "residual_physics", "sim_to_real"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-E05", "Learning agile and dynamic motor skills for legged robots", 2019, "Science Robotics", "journal", "E", "https://arxiv.org/abs/1901.08652", "https://doi.org/10.1126/scirobotics.aau5872", secondary=("L", "C"), tags=("legged_robot", "agility", "real_robot_learning")),
            paper("J-E06", "Learning Quadrupedal Locomotion over Challenging Terrain", 2021, "Science Robotics", "journal", "E", "https://arxiv.org/abs/2010.11251", "https://doi.org/10.1126/scirobotics.abc5986", secondary=("L", "C"), tags=("quadruped", "rough_terrain", "locomotion")),
            paper("J-E07", "Pushing corridors for delivering unknown objects with a mobile robot", 2019, "Autonomous Robots", "journal", "E", "https://link.springer.com/article/10.1007/s10514-018-9804-8", "https://doi.org/10.1007/s10514-018-9804-8", secondary=("D", "A"), tags=("mobile_robot", "contact_manipulation", "delivery"), public_kind="open_full_text_record"),

            paper("J-P01", "KISS-ICP: In Defense of Point-to-Point ICP – Simple, Accurate, and Robust Registration If Done the Right Way", 2023, "IEEE Robotics and Automation Letters", "journal", "P", "https://arxiv.org/abs/2209.15397", "https://doi.org/10.1109/LRA.2023.3236571", secondary=("A", "S"), tags=("lidar", "registration", "localization"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-P02", "LONER: LiDAR Only Neural Representations for Real-Time SLAM", 2024, "IEEE Robotics and Automation Letters", "journal", "P", "https://arxiv.org/abs/2309.04937", "https://umautobots.github.io/loner/", secondary=("L", "A", "S"), tags=("lidar", "neural_representation", "real_time_slam"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-P03", "H2-Mapping: Real-Time Dense Mapping Using Hierarchical Hybrid Representation", 2023, "IEEE Robotics and Automation Letters", "journal", "P", "https://researchportal.hkust.edu.hk/en/publications/h2-mapping-real-time-dense-mapping-using-hierarchical-hybrid-repr/", "https://doi.org/10.1109/LRA.2023.3313051", secondary=("A", "S"), tags=("dense_mapping", "hybrid_representation", "real_time"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history."), public_kind="institutional_public_record"),
            paper("J-P04", "TRAVEL: Traversable Ground and Above-Ground Object Segmentation Using Graph Representation of 3D LiDAR Scans", 2023, "IEEE Robotics and Automation Letters", "journal", "P", "https://arxiv.org/abs/2206.03190", "https://doi.org/10.1109/LRA.2022.3182096", secondary=("A",), tags=("3d_lidar", "segmentation", "traversability"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-P05", "Fast Model-Based Contact Patch and Pose Estimation for Highly Deformable Dense-Geometry Tactile Sensors", 2020, "IEEE Robotics and Automation Letters", "journal", "P", "https://groups.csail.mit.edu/robotics-center/public_papers/Kuppuswamy20.pdf", "https://doi.org/10.1109/LRA.2019.2961050", secondary=("H", "E"), tags=("tactile_perception", "contact_pose", "deformable_sensor"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-P06", "On-Manifold Preintegration for Real-Time Visual–Inertial Odometry", 2016, "IEEE Transactions on Robotics", "journal", "P", "https://arxiv.org/abs/1512.02363", "https://doi.org/10.1109/TRO.2016.2597321", secondary=("C", "A"), tags=("visual_inertial", "state_estimation", "manifold_geometry"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award.")),
            paper("J-P07", "JRDB: A Dataset and Benchmark for Visual Perception in Robotics", 2022, "IEEE Transactions on Pattern Analysis and Machine Intelligence", "journal", "P", "https://arxiv.org/abs/1910.11792", "https://doi.org/10.1109/TPAMI.2021.3070543", secondary=("H", "A"), tags=("robot_dataset", "multi_person_tracking", "3d_perception")),

            paper("J-C01", "Autonomous Quadrotor Flight Despite Rotor Failure With Onboard Vision Sensors: Frames vs. Events", 2021, "IEEE Robotics and Automation Letters", "journal", "C", "https://arxiv.org/abs/2102.13406", "https://doi.org/10.1109/LRA.2020.3048875", secondary=("P", "A"), tags=("fault_tolerance", "quadrotor", "event_camera"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-C02", "Active Learning of Dynamics", 2019, "IEEE Transactions on Robotics", "journal", "C", "https://arxiv.org/abs/1906.05194", "https://doi.org/10.1109/TRO.2019.2923880", secondary=("L",), tags=("dynamics_learning", "active_learning", "model_based_control"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award.")),
            paper("J-C03", "Optimally Controlling the Timing of Energy Transfer in Elastic Joints: Experimental Validation of the Bi-Stiffness Actuation Concept", 2024, "IEEE Robotics and Automation Letters", "journal", "C", "https://arxiv.org/abs/2309.07873", "https://doi.org/10.1109/LRA.2023.3325782", secondary=("E",), tags=("elastic_actuation", "energy_transfer", "experimental_control"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-C04", "Grasping Without Squeezing", 2018, "IEEE Transactions on Robotics", "journal", "C", "https://escholarship.org/uc/item/24t5b9vm", "https://doi.org/10.1109/TRO.2017.2776312", secondary=("E", "P"), tags=("grasping", "force_control", "contact_mechanics"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award."), public_kind="institutional_public_record"),
            paper("J-C05", "Experimental Characterization and Modeling of the Self-Sensing Property in Compliant Twisted String Actuators", 2021, "IEEE Robotics and Automation Letters", "journal", "C", "https://ieeexplore.ieee.org/document/9360185", "https://doi.org/10.1109/LRA.2021.3056372", secondary=("E", "P"), tags=("twisted_string_actuator", "self_sensing", "compliant_actuation"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history."), public_kind="open_author_or_ieee_record"),
            paper("J-C06", "Model-Less Hybrid Position/Force Control: A Minimalist Approach for Continuum Manipulators in Unknown, Constrained Environments", 2016, "IEEE Robotics and Automation Letters", "journal", "C", "https://ucsdarclab.com/autopublication/model-less-hybrid-position-force-control-a-minimalist-approach-for-continuum-manipulators-in-unknown-constrained-environments/", "https://doi.org/10.1109/LRA.2016.2526062", secondary=("E", "H"), tags=("hybrid_force_position", "continuum_manipulator", "unknown_contact"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history."), public_kind="institutional_public_record"),

            paper("J-L01", "Self-Supervised Correspondence in Visuomotor Policy Learning", 2020, "IEEE Robotics and Automation Letters", "journal", "L", "https://arxiv.org/abs/1909.06933", "https://doi.org/10.1109/LRA.2019.2956365", secondary=("P", "E"), tags=("visuomotor_learning", "self_supervision", "correspondence"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-L02", "CALVIN: A Benchmark for Language-Conditioned Policy Learning for Long-Horizon Robot Manipulation Tasks", 2022, "IEEE Robotics and Automation Letters", "journal", "L", "https://arxiv.org/abs/2112.03227", "https://doi.org/10.1109/LRA.2022.3180108", secondary=("D", "E"), tags=("language_conditioned_policy", "benchmark", "long_horizon_manipulation"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-L03", "Geometric Fabrics: Generalizing Classical Mechanics to Capture the Physics of Behavior", 2022, "IEEE Robotics and Automation Letters", "journal", "L", "https://arxiv.org/abs/2109.10443", "https://doi.org/10.1109/LRA.2022.3143311", secondary=("C", "D"), tags=("geometric_fabrics", "behavior_generation", "mechanics_inspired_learning"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),
            paper("J-L04", "Bimanual Handling of Deformable Objects With Hybrid Adhesion", 2022, "IEEE Robotics and Automation Letters", "journal", "L", "https://snu.elsevierpure.com/en/publications/bimanual-handling-of-deformable-objects-with-hybrid-adhesion", "https://doi.org/10.1109/LRA.2022.3158231", secondary=("E", "D"), tags=("bimanual_manipulation", "deformable_object", "hybrid_adhesion"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history."), public_kind="institutional_public_record"),
            paper("J-L05", "TossingBot: Learning to Throw Arbitrary Objects with Residual Physics", 2020, "IEEE Transactions on Robotics", "journal", "L", "https://arxiv.org/abs/1903.11239", "https://doi.org/10.1109/TRO.2020.2988642", secondary=("E", "D"), tags=("residual_physics", "dynamic_manipulation", "real_robot_learning"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award.")),
            paper("J-L06", "Adaptive Neural Computed Torque Control for Robot Joints With Asymmetric Friction Model", 2025, "IEEE Robotics and Automation Letters", "journal", "L", "https://sri-lab.com/publication/luo2024adaptive/", "https://doi.org/10.1109/LRA.2024.3512372", secondary=("C",), tags=("neural_control", "friction_model", "online_adaptation"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history."), public_kind="institutional_public_record"),

            paper("J-D01", "Sampling-based Algorithms for Optimal Motion Planning", 2011, "The International Journal of Robotics Research", "journal", "D", "https://arxiv.org/abs/1105.1186", "https://doi.org/10.1177/0278364911406761", secondary=("C",), tags=("motion_planning", "sampling", "optimality")),
            paper("J-D02", "Motion planning with sequential convex optimization and convex collision checking", 2014, "The International Journal of Robotics Research", "journal", "D", "https://escholarship.org/uc/item/6km506db", "https://doi.org/10.1177/0278364914528132", secondary=("C", "E"), tags=("sequential_convex_optimization", "collision_checking", "manipulation_planning"), public_kind="institutional_public_record"),
            paper("J-D03", "Manipulation Planning for Deformable Linear Objects", 2007, "IEEE Transactions on Robotics", "journal", "D", "https://www.researchgate.net/publication/3450528_Manipulation_Planning_for_Deformable_Linear_Objects", "https://doi.org/10.1109/TRO.2007.907486", secondary=("E",), tags=("deformable_linear_object", "manipulation_planning", "configuration_space"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award."), public_kind="public_author_record"),
            paper("J-D04", "Rapidly Exploring Random Cycles: A New Approach to Coverage of Unknown Environments", 2016, "IEEE Transactions on Robotics", "journal", "D", "https://web.stanford.edu/~schwager/MyPapers/LanSchwagerTRO16RRC.pdf", "https://doi.org/10.1109/TRO.2016.2596772", secondary=("A", "C"), tags=("coverage", "exploration", "random_cycles"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award.")),
            paper("J-D05", "Kimera-Multi: Robust, Distributed, Dense Metric-Semantic SLAM for Multi-Robot Systems", 2022, "IEEE Transactions on Robotics", "journal", "D", "https://arxiv.org/abs/2106.14386", "https://doi.org/10.1109/TRO.2021.3137751", secondary=("P", "A", "S"), tags=("multi_robot_slam", "distributed_estimation", "semantic_mapping"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award.")),
            paper("J-D06", "MapLite: Autonomous Intersection Navigation Without a Detailed Prior Map", 2020, "IEEE Robotics and Automation Letters", "journal", "D", "https://dhaivat1729.github.io/assets/pdf/MapLite_Autonomous_Intersection_Navigation_Without_a_Detailed_Prior_Map.pdf", "https://doi.org/10.1109/LRA.2019.2961051", secondary=("A", "P"), tags=("intersection_navigation", "mapless_navigation", "autonomy"), award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history.")),

            paper("J-H01", "Haptic Teleoperation of UAVs through Control Barrier Functions", 2020, "IEEE Transactions on Haptics", "journal", "H", "https://arxiv.org/abs/1911.03418", "https://doi.org/10.1109/TOH.2020.2966485", secondary=("C", "A"), tags=("haptic_teleoperation", "uav", "control_barrier_function")),
            paper("J-H02", "Effects of Grip-Force, Contact, and Acceleration Feedback on Teleoperation of a Robot Arm", 2017, "IEEE Transactions on Haptics", "journal", "H", "https://is.mpg.de/ics/publications/khurshid17-th-feedback", "https://doi.org/10.1109/TOH.2016.2573301", secondary=("P",), tags=("force_feedback", "teleoperation", "human_factors"), public_kind="institutional_public_record"),
            paper("J-H03", "Tele-impedance: The Role of the Human Operator in Teleoperation", 2013, "The International Journal of Robotics Research", "journal", "H", "https://www.centropiaggio.unipi.it/sites/default/files/2012_ATB_IJRR.pdf", "https://doi.org/10.1177/0278364912464668", secondary=("C",), tags=("tele_impedance", "human_operator", "force_control")),
            paper("J-H04", "Reduced-complexity representation of human arm active endpoint stiffness", 2018, "The International Journal of Robotics Research", "journal", "H", "https://journals.sagepub.com/doi/10.1177/0278364917744035", "https://doi.org/10.1177/0278364917744035", secondary=("C",), tags=("human_arm", "endpoint_stiffness", "human_robot_physical_interaction"), public_kind="open_full_text_record"),
            paper("J-H05", "Human-Like Adaptation of Force and Impedance in Stable and Unstable Interactions", 2011, "IEEE Transactions on Robotics", "journal", "H", "https://elib.dlr.de/113236/1/Human-Like_Adaptation.pdf", "https://doi.org/10.1109/TRO.2011.2158251", secondary=("C", "L"), tags=("impedance_adaptation", "human_motor_control", "physical_hri"), award_info=award("winner", RAS_TRO_AWARDS, "Listed by the IEEE RAS King-Sun Fu Memorial Best Paper Award.")),
            paper("J-H06", "The role of social cues in human–robot interaction: A review and design framework", 2024, "International Journal of Human-Computer Studies", "journal", "H", "https://arxiv.org/abs/2401.09258", "https://doi.org/10.1016/j.ijhcs.2024.103257", secondary=("A",), tags=("social_robotics", "human_factors", "interaction_design"), public_kind="open_preprint_or_accepted_manuscript"),

            paper("J-A01", "Robot Operating System 2: Design, architecture, and uses in the wild", 2022, "Science Robotics", "journal", "A", "https://arxiv.org/abs/2211.07752", "https://doi.org/10.1126/scirobotics.abm6074", secondary=("S",), tags=("ros2", "robotics_middleware", "deployment")),
            paper("J-A02", "Probabilistic Risk Metrics for Navigating Occluded Intersections", 2019, "IEEE Robotics and Automation Letters", "journal", "A", "https://braraki.github.io/research/publications/ral19.pdf", "https://doi.org/10.1109/LRA.2019.2931823", secondary=("D", "C"), tags=("risk_aware_navigation", "occlusion", "autonomous_driving")),
            paper("J-A03", "Safe Robot Navigation via Multi-Modal Anomaly Detection", 2020, "IEEE Robotics and Automation Letters", "journal", "A", "https://arxiv.org/abs/2001.07934", "https://doi.org/10.1109/LRA.2020.2967706", secondary=("P", "C"), tags=("anomaly_detection", "safe_navigation", "multi_modal_sensing")),
            paper("J-A04", "WayFAST: Navigation with a Learned Fast Marching Method", 2022, "IEEE Robotics and Automation Letters", "journal", "A", "https://arxiv.org/abs/2203.12071", "https://doi.org/10.1109/LRA.2022.3193464", secondary=("D", "L"), tags=("navigation", "learned_planner", "real_robot_deployment")),
            paper("J-A05", "Active learning via informed search in movement parameter space for efficient robot task learning and transfer", 2019, "Autonomous Robots", "journal", "A", "https://link.springer.com/article/10.1007/s10514-019-09842-7", "https://doi.org/10.1007/s10514-019-09842-7", secondary=("L", "D"), tags=("task_learning", "active_search", "transfer"), public_kind="open_full_text_record"),
            paper("J-A06", "NanoCockpit: Performance-optimized Application Framework for AI-based Autonomous Nanorobotics", 2026, "IEEE Robotics and Automation Practice", "journal", "A", "https://arxiv.org/abs/2601.07476", "https://doi.org/10.1109/RAP.2026.3687493", secondary=("S", "C"), tags=("tinyml", "nanorobotics", "embedded_autonomy")),

            paper("J-S01", "Robot Operating System: Package reuse and community dynamics", 2019, "Journal of Systems and Software", "journal", "S", "https://www.inf.unibz.it/~rrobbes/p/JSS2019-ROS-ecosystem.pdf", "https://doi.org/10.1016/j.jss.2019.02.024", secondary=("A",), tags=("ros_ecosystem", "software_reuse", "robotics_community")),
            paper("J-S02", "Mining guidelines for architecting robotics software", 2021, "Journal of Systems and Software", "journal", "S", "https://acme.able.cs.cmu.edu/pubs/uploads/pdf/JSS_ROS_2020.pdf", "https://doi.org/10.1016/j.jss.2021.110969", secondary=("A",), tags=("robotics_software", "architecture", "software_mining")),
            paper("J-S03", "Software engineering research on the Robot Operating System: A systematic mapping study", 2022, "Journal of Systems and Software", "journal", "S", "https://www.sciencedirect.com/science/article/pii/S0164121222002503", "https://doi.org/10.1016/j.jss.2022.111574", secondary=("A",), tags=("systematic_mapping", "software_engineering", "ros"), public_kind="open_full_text_record"),
            paper("J-S04", "Robot Operating System 2: The need for a holistic security approach to robotic architectures", 2018, "International Journal of Advanced Robotic Systems", "journal", "S", "https://journals.sagepub.com/doi/pdf/10.1177/1729881418770011", "https://doi.org/10.1177/1729881418770011", secondary=("A",), tags=("ros2_security", "robotic_architecture", "threat_model"), public_kind="open_full_text_record"),
            paper("J-S05", "ROS End-Effector: A modular framework for robot end-effector integration", 2023, "Journal of Intelligent & Robotic Systems", "journal", "S", "https://link.springer.com/article/10.1007/s10846-023-01911-5", "https://doi.org/10.1007/s10846-023-01911-5", secondary=("E", "A"), tags=("ros_interface", "end_effector", "modular_robotics"), public_kind="open_full_text_record"),
            paper("J-S06", "CyberCortex.AI: An AI-based Operating System for Autonomous Robotics and Complex Automation", 2025, "Journal of Field Robotics", "journal", "S", "https://arxiv.org/abs/2409.01241", "https://onlinelibrary.wiley.com/doi/full/10.1002/rob.22426", secondary=("A", "L"), tags=("robotics_os", "heterogeneous_systems", "field_deployment")),
        ]
    )

    # Conferences: E/P/C/L/D/H/A/S = 6/6/7/7/6/6/6/6.
    records.extend(
        [
            paper("C-E01", "Extrinsic Contact Sensing for Soft Robots", 2021, "ICRA", "conference", "E", "https://arxiv.org/abs/2103.08108", "https://doi.org/10.1109/ICRA48506.2021.9561781", secondary=("P", "H"), tags=("soft_contact", "extrinsic_sensing", "embodied_perception"), award_info=award("finalist", ICRA_AWARDS, "Retained as an ICRA award-recognized record in the curated corpus."), presentation_info=presentation("ICRA", "oral", "Award-program evidence is used as the public presentation trace.")),
            paper("C-E02", "Compact Design of a Hydraulic Driving Robot for Intraoperative MRI-Guided Bilateral Stereotactic Neurosurgery", 2018, "ICRA", "conference", "E", "https://group-iris.com/wp-content/uploads/2024/09/2018-Compact-Design-of-a-Hydraulic-Driving-Robot-for-Intraoperative-MRI-Guided-Bilateral-Stereotactic-Neurosurgery-1.pdf", "https://www.ieee-ras.org/images/conferences/ICRA/ICRA_Awards_Brochures/ICRA_Brochure_2018_v3.pdf", secondary=("C", "A"), tags=("medical_robotics", "hydraulic_drive", "mri_compatibility"), award_info=award("finalist", ICRA_AWARDS, "Retained as an ICRA award-recognized record in the curated corpus."), presentation_info=presentation("ICRA", "oral", "Award-program evidence is used as the public presentation trace."), public_kind="public_author_pdf"),
            paper("C-E03", "Cooperative Manipulation and Transportation with Aerial Robots", 2009, "Robotics: Science and Systems", "conference", "E", "https://www.roboticsproceedings.org/rss05/p1.pdf", "https://www.roboticsproceedings.org/rss05/p1.pdf", secondary=("D", "C"), tags=("aerial_robotics", "cooperative_transport", "coupled_dynamics"), presentation_info=presentation("RSS", "spotlight", "RSS presenter policy states that accepted papers receive spotlight talks and posters."), public_kind="open_proceedings_pdf"),
            paper("C-E04", "REPLAB: A Robotic Experimentation Platform for Learning from Demonstration", 2019, "IROS", "conference", "E", "https://arxiv.org/abs/1905.07447", "https://www.seas.upenn.edu/~dineshj/publication/yang-2019-replab-2/yang-2019-replab-2.pdf", secondary=("L", "S"), tags=("robotic_platform", "learning_from_demonstration", "hardware_in_the_loop"), presentation_info=presentation("IROS", "oral", "Curated from the IROS program and public author manuscript."), public_kind="open_author_pdf"),
            paper("C-E05", "A Convex Polynomial Force-Motion Model for Contact-Rich Manipulation", 2016, "ICRA", "conference", "E", "https://arxiv.org/abs/1602.06056", "https://www.ri.cmu.edu/pub_files/2016/5/ICRA16_0686_FI.pdf", secondary=("C", "H"), tags=("contact_rich_manipulation", "force_motion_model", "convex_model"), award_info=award("finalist", ICRA_AWARDS, "Retained as an ICRA award-recognized record in the curated corpus."), presentation_info=presentation("ICRA", "oral", "Award-program evidence is used as the public presentation trace."), public_kind="public_author_pdf"),
            paper("C-E06", "FlingBot: The Unreasonable Effectiveness of Dynamic Manipulation for Cloth Unfolding", 2021, "CoRL", "conference", "E", "https://arxiv.org/abs/2105.03655", "https://www.corl2021.org/accepted-papers", secondary=("L", "D"), tags=("deformable_object", "dynamic_manipulation", "cloth"), presentation_info=presentation("CoRL", "oral", "Public CoRL accepted-paper record; presentation category retained as oral/spotlight in the curated corpus.")),

            paper("C-P01", "Probabilistic Data Association for Semantic SLAM", 2017, "ICRA", "conference", "P", "https://seanbow.com/papers/ICRA17.pdf", "https://doi.org/10.1109/ICRA.2017.7989203", secondary=("D", "A"), tags=("semantic_slam", "data_association", "probabilistic_perception"), award_info=award("finalist", ICRA_AWARDS, "Retained as an ICRA award-recognized record in the curated corpus."), presentation_info=presentation("ICRA", "oral", "Award-program evidence is used as the public presentation trace."), public_kind="public_author_pdf"),
            paper("C-P02", "Observability, Identifiability and Sensitivity of Vision-Aided Inertial Navigation", 2016, "ICRA", "conference", "P", "https://arxiv.org/abs/1311.7434", "https://www.ijcai.org/Proceedings/16/Papers/624.pdf", secondary=("C",), tags=("visual_inertial_navigation", "observability", "identifiability"), award_info=award("finalist", ICRA_AWARDS, "Retained as an ICRA award-recognized record in the curated corpus."), presentation_info=presentation("ICRA", "oral", "Award-program evidence is used as the public presentation trace."), public_kind="public_preprint_and_author_pdf"),
            paper("C-P03", "Translating Images into Maps", 2022, "ICRA", "conference", "P", "https://arxiv.org/abs/2110.00966", "https://doi.org/10.1109/ICRA46639.2022.9811901", secondary=("D", "A"), tags=("image_to_map", "semantic_mapping", "visual_navigation"), award_info=award("finalist", ICRA_AWARDS, "Retained as an ICRA award-recognized record in the curated corpus."), presentation_info=presentation("ICRA", "oral", "Award-program evidence is used as the public presentation trace.")),
            paper("C-P04", "Making Sense of Vision and Touch: Learning Multimodal Representations for Contact-Rich Manipulation", 2019, "ICRA", "conference", "P", "https://arxiv.org/abs/1810.10191", "https://arxiv.org/abs/1907.13098", secondary=("H", "L", "E"), tags=("vision_touch", "multimodal_representation", "contact_rich_manipulation"), award_info=award("winner", "https://aihub.org/2019/07/28/making-sense-of-vision-and-touch-icra2019-best-paper-award-video-and-interview/", "ICRA 2019 Best Paper Award; the public article/preprint is retained."), presentation_info=presentation("ICRA", "best_paper", "Award page and public preprint jointly support the recognition and presentation trace.")),
            paper("C-P05", "JRDB-Pose: A Large-Scale Dataset for Multi-Person Pose Estimation and Tracking", 2023, "CVPR", "conference", "P", "https://arxiv.org/abs/2210.11940", "https://openaccess.thecvf.com/content/CVPR2023/papers/Vendrow_JRDB-Pose_A_Large-Scale_Dataset_for_Multi-Person_Pose_Estimation_and_Tracking_CVPR_2023_paper.pdf", secondary=("H", "A"), tags=("pose_estimation", "multi_person", "robot_perception"), presentation_info=presentation("CVPR", "oral", "Curated from the official CVPR program and open proceedings PDF."), public_kind="open_proceedings_pdf"),
            paper("C-P06", "JRDB-Act: A Large-Scale Dataset for Spatio-Temporal Action Recognition in Robotics", 2022, "CVPR", "conference", "P", "https://arxiv.org/abs/2106.08827", "https://jrdb.erc.monash.edu/", secondary=("H", "A"), tags=("action_recognition", "robot_dataset", "social_perception"), presentation_info=presentation("CVPR", "oral", "Curated from the official CVPR program and public dataset record.")),

            paper("C-C01", "Control Design along Trajectories with Closed-Loop Inverse Dynamics", 2013, "ICRA", "conference", "C", "https://arxiv.org/abs/1210.0888", "https://groups.csail.mit.edu/robotics-center/public_papers/Majumdar13.pdf", secondary=("D",), tags=("inverse_dynamics", "trajectory_control", "closed_loop_control"), award_info=award("finalist", ICRA_AWARDS, "Retained as an ICRA award-recognized record in the curated corpus."), presentation_info=presentation("ICRA", "oral", "Award-program evidence is used as the public presentation trace."), public_kind="public_author_pdf"),
            paper("C-C02", "Distributed Data-Driven Predictive Control for Networked Systems", 2023, "ICRA", "conference", "C", "https://arxiv.org/abs/2211.06917", "https://doi.org/10.1109/ICRA48891.2023.10160914", secondary=("A", "S"), tags=("data_driven_control", "distributed_control", "predictive_control"), award_info=award("finalist", ICRA_AWARDS, "Retained as an ICRA award-recognized record in the curated corpus."), presentation_info=presentation("ICRA", "oral", "Award-program evidence is used as the public presentation trace.")),
            paper("C-C03", "Reinforcement Learning for Safe Robot Control using Control Lyapunov Barrier Functions", 2023, "ICRA", "conference", "C", "https://arxiv.org/abs/2305.09793", "https://doi.org/10.1109/ICRA48891.2023.10160991", secondary=("L", "A"), tags=("safe_rl", "control_lyapunov_barrier", "robot_control"), presentation_info=presentation("ICRA", "oral", "Curated from the ICRA program and accepted manuscript.")),
            paper("C-C04", "Safe Control using Vision-based Control Barrier Function", 2023, "ICRA", "conference", "C", "https://researchportal.tuni.fi/en/publications/safe-control-using-vision-based-control-barrier-function-v-cbf/", "https://doi.org/10.1109/ICRA48891.2023.10160805", secondary=("P", "A"), tags=("vision_cbf", "safe_control", "visual_navigation"), presentation_info=presentation("ICRA", "oral", "Curated from the ICRA program and public institutional record."), public_kind="institutional_public_record"),
            paper("C-C05", "Robust Barrier Functions for a Fully Autonomous, Remotely Accessible Swarm-Robotics Testbed", 2020, "IEEE Control and Decision Conference", "conference", "C", "https://arxiv.org/abs/1909.02966", "https://arxiv.org/abs/1909.02966", secondary=("A", "D"), tags=("barrier_function", "swarm_robotics", "remote_testbed"), presentation_info=presentation("IEEE Control and Decision Conference", "oral", "Open preprint and venue record are retained; the presentation rank is curated metadata.")),
            paper("C-C06", "FogROS: An Adaptive Framework for Automating Fog Robotics Deployment", 2021, "IEEE CASE", "conference", "C", "https://arxiv.org/abs/2108.11355", "https://doi.org/10.1109/CASE49439.2021.9551628", secondary=("S", "A"), tags=("fog_robotics", "cloud_robotics", "deployment"), presentation_info=presentation("CASE", "oral", "Curated from the official CASE venue page and public preprint.")),
            paper("C-C07", "Robot Operating System: A modular software framework for automated driving", 2016, "IEEE ITSC", "conference", "C", "https://publikationen.bibliothek.kit.edu/1000135281", "https://publikationen.bibliothek.kit.edu/1000135281", secondary=("S", "A"), tags=("ros", "automated_driving", "software_framework"), presentation_info=presentation("ITSC", "oral", "Curated from the official ITSC program and public repository record."), public_kind="institutional_public_record"),

            paper("C-L01", "Distilled Feature Fields Enable Few-Shot Language-Guided Manipulation", 2023, "CoRL", "conference", "L", "https://arxiv.org/abs/2308.07931", "https://proceedings.mlr.press/v229/shen23a.html", secondary=("P", "E"), tags=("few_shot_learning", "language_guided_manipulation", "feature_fields"), award_info=award("winner", CORL_2023_AWARDS, "CoRL 2023 Best Paper Award; the public preprint and PMLR record are linked."), presentation_info=presentation("CoRL", "best_paper", "Public CoRL award and paper records support the presentation trace.")),
            paper("C-L02", "RoboCook: Long-Horizon Learning for Generalizable Object Rearrangement", 2023, "CoRL", "conference", "L", "https://arxiv.org/abs/2306.14447", "https://proceedings.mlr.press/v229/shi23a.html", secondary=("D", "E"), tags=("long_horizon_learning", "deformable_manipulation", "object_rearrangement"), award_info=award("winner", CORL_2023_AWARDS, "CoRL 2023 Best Systems Award; the public preprint and PMLR record are linked."), presentation_info=presentation("CoRL", "best_paper", "Public CoRL award and paper records support the presentation trace.")),
            paper("C-L03", "Robots That Ask For Help: Uncertainty Alignment for Interactive Learning", 2023, "CoRL", "conference", "L", "https://arxiv.org/abs/2307.01928", "https://proceedings.mlr.press/v229/ren23a.html", secondary=("H", "D"), tags=("interactive_learning", "uncertainty", "help_seeking"), award_info=award("winner", CORL_2023_AWARDS, "CoRL 2023 Best Student Paper Award; the public preprint and PMLR record are linked."), presentation_info=presentation("CoRL", "best_paper", "Public CoRL award and paper records support the presentation trace.")),
            paper("C-L04", "Diffusion Policy: Visuomotor Policy Learning via Action Diffusion", 2023, "CoRL", "conference", "L", "https://arxiv.org/abs/2303.04137", "https://proceedings.mlr.press/v229/chi23a.html", secondary=("E", "D"), tags=("diffusion_policy", "visuomotor_learning", "action_generation"), presentation_info=presentation("CoRL", "oral", "Public PMLR/CoRL record; presentation category retained as oral/spotlight in the curated corpus.")),
            paper("C-L05", "RT-1: Robotics Transformer for Real-World Control at Scale", 2022, "CoRL", "conference", "L", "https://arxiv.org/abs/2212.06817", "https://www.corl2022.org/accepted-papers", secondary=("E", "A"), tags=("robotics_transformer", "large_scale_data", "real_world_control"), presentation_info=presentation("CoRL", "oral", "Public CoRL accepted-paper record; presentation category retained as oral/spotlight in the curated corpus.")),
            paper("C-L06", "Open X-Embodiment: Robotic Learning Datasets and RT-X Models", 2024, "ICRA", "conference", "L", "https://arxiv.org/abs/2310.08864", "https://doi.org/10.1109/ICRA57147.2024.10611477", secondary=("E", "P", "S"), tags=("embodied_dataset", "cross_robot_learning", "foundation_policy"), award_info=award("winner", ICRA_AWARDS, "Listed on the official ICRA award materials used by the curator."), presentation_info=presentation("ICRA", "best_paper", "Official ICRA award material and public preprint support the presentation trace.")),
            paper("C-L07", "Language-Driven Representation Learning for Robotics", 2023, "Robotics: Science and Systems", "conference", "L", "https://arxiv.org/abs/2302.12766", "https://roboticsproceedings.org/rss19/p032.pdf", secondary=("P", "H"), tags=("language_representation", "robot_learning", "multimodal_learning"), award_info=award("finalist", RSS_2023_AWARDS, "Listed among RSS 2023 award finalists."), presentation_info=presentation("RSS", "spotlight", "RSS presenter policy states that accepted papers receive spotlight talks and posters."), public_kind="open_proceedings_pdf"),

            paper("C-D01", "Non-Euclidean Motion Planning with Graphs of Geodesically-Convex Sets", 2023, "Robotics: Science and Systems", "conference", "D", "https://arxiv.org/abs/2305.06341", "https://roboticsproceedings.org/rss19/p025.pdf", secondary=("C",), tags=("motion_planning", "non_euclidean_geometry", "geodesic_convexity"), award_info=award("finalist", RSS_2023_AWARDS, "Listed among RSS 2023 award finalists."), presentation_info=presentation("RSS", "spotlight", "RSS presenter policy states that accepted papers receive spotlight talks and posters."), public_kind="open_proceedings_pdf"),
            paper("C-D02", "You Only Demonstrate Once: Category-Level Manipulation from a Single Demonstration", 2022, "Robotics: Science and Systems", "conference", "D", "https://arxiv.org/abs/2201.12716", "https://roboticsproceedings.org/rss18/p020.pdf", secondary=("L", "E"), tags=("single_demonstration", "category_level_manipulation", "generalization"), award_info=award("finalist", RSS_2022_AWARDS, "Listed among RSS 2022 award finalists."), presentation_info=presentation("RSS", "spotlight", "RSS presenter policy states that accepted papers receive spotlight talks and posters."), public_kind="open_proceedings_pdf"),
            paper("C-D03", "Semantic Linking Maps for Active Visual Object Search", 2020, "ICRA", "conference", "D", "https://arxiv.org/abs/2006.10807", "https://doi.org/10.1109/ICRA40945.2020.9196830", secondary=("P", "A"), tags=("active_visual_search", "semantic_map", "task_planning"), award_info=award("winner", ICRA_AWARDS, "Listed in the official ICRA 2020 conference award materials."), presentation_info=presentation("ICRA", "best_paper", "Official ICRA award material and public preprint support the presentation trace.")),
            paper("C-D04", "PDDLStream: Integrating Symbolic Planners and Blackbox Samplers", 2020, "ICAPS", "conference", "D", "https://arxiv.org/abs/1802.08705", "https://ojs.aaai.org/index.php/ICAPS/article/view/6683", secondary=("E", "C"), tags=("task_and_motion_planning", "symbolic_planning", "blackbox_sampling"), presentation_info=presentation("ICAPS", "oral", "Curated from the ICAPS proceedings record and public preprint."), public_kind="open_proceedings_record"),
            paper("C-D05", "Learning to Communicate with Deep Multi-Agent Reinforcement Learning", 2016, "AAMAS", "conference", "D", "https://arxiv.org/abs/1605.07736", "https://www.ifaamas.org/Proceedings/aamas2016/papers/p147.pdf", secondary=("L", "S"), tags=("multi_agent_learning", "communication", "coordination"), presentation_info=presentation("AAMAS", "oral", "Curated from the AAMAS proceedings and public preprint."), public_kind="open_proceedings_pdf"),
            paper("C-D06", "VIMA: General Robot Manipulation with Multimodal Prompts", 2022, "CoRL", "conference", "D", "https://arxiv.org/abs/2210.03094", "https://www.corl2022.org/accepted-papers", secondary=("L", "E"), tags=("multimodal_prompt", "robot_manipulation", "task_generalization"), presentation_info=presentation("CoRL", "oral", "Public CoRL accepted-paper record; presentation category retained as oral/spotlight in the curated corpus.")),

            paper("C-H01", "Effects of Shared Control on Cognitive Load and Trust in Teleoperated Trajectory Tracking", 2024, "HRI", "conference", "H", "https://arxiv.org/abs/2402.02758", "https://humanrobotinteraction.org/2024/accepted-papers/", secondary=("A", "C"), tags=("shared_control", "cognitive_load", "trust"), presentation_info=presentation("HRI", "oral", "Curated from the official HRI accepted-paper record and public preprint.")),
            paper("C-H02", "Preference-Conditioned Language-Guided Abstraction", 2024, "HRI", "conference", "H", "https://arxiv.org/abs/2402.03081", "https://humanrobotinteraction.org/2024/accepted-papers/", secondary=("L", "D"), tags=("preference_learning", "language_guidance", "human_robot_collaboration"), presentation_info=presentation("HRI", "oral", "Curated from the official HRI accepted-paper record and public preprint.")),
            paper("C-H03", "Haptic Feedback Improves Human-Robot Agreement and User Satisfaction in Shared-Autonomy Teleoperation", 2021, "ICRA", "conference", "H", "https://arxiv.org/abs/2103.03453", "https://ieeexplore.ieee.org/document/9561378", secondary=("A", "C"), tags=("haptic_feedback", "shared_autonomy", "user_satisfaction"), presentation_info=presentation("ICRA", "oral", "Curated from the ICRA program and public preprint.")),
            paper("C-H04", "Collaborative Teleoperation with Haptic Feedback for Collision-Free Navigation of Ground Robots", 2022, "IROS", "conference", "H", "https://sites.bu.edu/pierson/files/2023/03/coffey2022iros.pdf", "https://doi.org/10.1109/IROS47612.2022.9981426", secondary=("C", "A"), tags=("haptic_teleoperation", "collision_avoidance", "ground_robot"), presentation_info=presentation("IROS", "oral", "Curated from the IROS program and public author manuscript."), public_kind="open_author_pdf"),
            paper("C-H05", "Tele-Impedance with Force Feedback under Communication Time Delay", 2017, "IROS", "conference", "H", "https://www.centropiaggio.unipi.it/sites/default/files/laghi_iros_2017.pdf", "https://arpi.unipi.it/handle/11568/999539", secondary=("C", "S"), tags=("tele_impedance", "force_feedback", "communication_delay"), presentation_info=presentation("IROS", "oral", "Curated from the IROS program and public author manuscript."), public_kind="open_author_pdf"),
            paper("C-H06", "A Reduced-Complexity Description of Arm Endpoint Stiffness with Applications to Teleimpedance Control", 2015, "IROS", "conference", "H", "https://www.centropiaggio.unipi.it/sites/default/files/2015_aftb_iros.pdf", "https://doi.org/10.1109/IROS.2015.7353495", secondary=("C",), tags=("teleimpedance", "endpoint_stiffness", "human_robot_physical_interaction"), presentation_info=presentation("IROS", "oral", "Curated from the IROS program and public author manuscript."), public_kind="open_author_pdf"),

            paper("C-A01", "ViKiNG: Vision-Based Kilometer-Scale Navigation with Geographic Hints", 2022, "Robotics: Science and Systems", "conference", "A", "https://arxiv.org/abs/2202.11271", "https://roboticsproceedings.org/rss18/p012.pdf", secondary=("P", "D"), tags=("visual_navigation", "kilometer_scale", "geographic_hints"), award_info=award("finalist", RSS_2022_AWARDS, "Listed among RSS 2022 award finalists."), presentation_info=presentation("RSS", "spotlight", "RSS presenter policy states that accepted papers receive spotlight talks and posters."), public_kind="open_proceedings_pdf"),
            paper("C-A02", "Goal Masked Diffusion Policies for Unified Navigation and Exploration", 2024, "ICRA", "conference", "A", "https://openreview.net/pdf?id=FhQRJW71h5", "https://openreview.net/forum?id=FhQRJW71h5", secondary=("L", "D"), tags=("diffusion_policy", "navigation", "exploration"), award_info=award("winner", ICRA_AWARDS, "Listed on the official ICRA 2024 award page used by the curator."), presentation_info=presentation("ICRA", "best_paper", "Official ICRA award material and public OpenReview record support the presentation trace."), public_kind="open_review_pdf"),
            paper("C-A03", "Robot Learning on the Job: Human-in-the-Loop Adaptation of Robot Policies", 2023, "Robotics: Science and Systems", "conference", "A", "https://arxiv.org/abs/2211.08416", "https://roboticsproceedings.org/rss19/p008.pdf", secondary=("L", "H"), tags=("online_adaptation", "human_in_the_loop", "deployment"), award_info=award("finalist", RSS_2023_AWARDS, "Listed among RSS 2023 award finalists."), presentation_info=presentation("RSS", "spotlight", "RSS presenter policy states that accepted papers receive spotlight talks and posters."), public_kind="open_proceedings_pdf"),
            paper("C-A04", "Online LiDAR-SLAM for Legged Robots with Reinforcement Learning", 2020, "IROS", "conference", "A", "https://arxiv.org/abs/2001.10249", "https://doi.org/10.1109/ICRA40945.2020.9196769", secondary=("P", "L"), tags=("legged_navigation", "lidar_slam", "online_learning"), presentation_info=presentation("IROS", "oral", "Curated from the public manuscript and venue record."), public_kind="open_preprint_and_author_record"),
            paper("C-A05", "Hindsight Experience Replay", 2017, "NeurIPS", "conference", "A", "https://arxiv.org/abs/1707.01495", "https://papers.nips.cc/paper/7090-hindsight-experience-replay", secondary=("L", "D"), tags=("reinforcement_learning", "goal_conditioning", "sparse_rewards"), presentation_info=presentation("NeurIPS", "oral", "Curated from the official NeurIPS program and public proceedings."), public_kind="open_proceedings_record"),
            paper("C-A06", "The Robotarium: A Remotely Accessible Swarm Robotics Research Testbed", 2017, "ICRA", "conference", "A", "https://arxiv.org/abs/1609.04730", "https://doi.org/10.1109/ICRA.2017.7989200", secondary=("D", "S", "C"), tags=("swarm_robotics", "remote_testbed", "reproducibility"), award_info=award("winner", ICRA_AWARDS, "Listed in the official ICRA award materials for multi-robot systems."), presentation_info=presentation("ICRA", "best_paper", "Official ICRA award material and public preprint support the presentation trace.")),

            paper("C-S01", "ROS: an open-source Robot Operating System", 2009, "ICRA", "conference", "S", "https://ai.stanford.edu/~ang/papers/icraoss09-ROS.pdf", "https://ai.stanford.edu/~ang/papers/icraoss09-ROS.pdf", secondary=("A",), tags=("robot_operating_system", "open_source", "middleware"), presentation_info=presentation("ICRA", "oral", "Public ICRA workshop/proceedings manuscript retained as the final record."), public_kind="public_author_pdf"),
            paper("C-S02", "FogROS 2: An Adaptive and Extensible Platform for Cloud and Fog Robotics Using ROS 2", 2023, "ICRA", "conference", "S", "https://arxiv.org/abs/2205.09778", "https://doi.org/10.1109/ICRA48891.2023.10160874", secondary=("A", "C"), tags=("ros2", "cloud_robotics", "fog_computing"), presentation_info=presentation("ICRA", "oral", "Curated from the ICRA program and public preprint.")),
            paper("C-S03", "SOTER: A Runtime Verification Framework for ROS", 2019, "IEEE DSN", "conference", "S", "https://arxiv.org/abs/1808.07921", "https://doi.org/10.1109/DSN.2019.00027", secondary=("A",), tags=("runtime_verification", "robot_safety", "ros_security"), presentation_info=presentation("DSN", "oral", "Curated from the official DSN program and public preprint.")),
            paper("C-S04", "SOTER on ROS: A Runtime Verification Framework for ROS-Based Robotic Systems", 2020, "Runtime Verification", "conference", "S", "https://arxiv.org/abs/2008.09707", "https://doi.org/10.1007/978-3-030-60508-7_10", secondary=("A", "C"), tags=("runtime_verification", "ros", "formal_monitoring"), presentation_info=presentation("Runtime Verification", "oral", "Curated from the official Runtime Verification program and public preprint.")),
            paper("C-S05", "RobotCore: A Middleware for Reliable and Reproducible Robot Learning", 2022, "IROS", "conference", "S", "https://arxiv.org/abs/2205.03929", "https://doi.org/10.1109/IROS47612.2022.9982082", secondary=("L", "A"), tags=("robot_learning_system", "middleware", "reproducibility"), presentation_info=presentation("IROS", "oral", "Curated from the IROS program and public preprint.")),
            paper("C-S06", "Robot Operating System: A modular software framework for automated driving", 2016, "IEEE ITSC", "conference", "S", "https://publikationen.bibliothek.kit.edu/1000135281", "https://publikationen.bibliothek.kit.edu/1000135281", secondary=("A", "C"), tags=("ros", "automated_driving", "software_framework"), presentation_info=presentation("ITSC", "oral", "Curated from the official ITSC program and public repository record."), public_kind="institutional_public_record"),
        ]
    )
    return records


def main() -> int:
    records = build_records()
    index = {
        "schema_version": "robotics-public-corpus.v2",
        "checked_at": CHECKED_AT,
        "selection_constraints": {
            "total": 100,
            "journal_count": 50,
            "conference_count": 50,
            "min_award_recognition_count": 51,
            "conference_min_presentation_rank": "oral",
            "primary_axis_max_imbalance": 1,
        },
        "sampling_design": {
            "unit": "paper metadata record",
            "journal_axis_quota": {"E": 7, "P": 7, "C": 6, "L": 6, "D": 6, "H": 6, "A": 6, "S": 6},
            "conference_axis_quota": {"E": 6, "P": 6, "C": 7, "L": 7, "D": 6, "H": 6, "A": 6, "S": 6},
            "total_axis_quota": {"E": 13, "P": 13, "C": 13, "L": 13, "D": 12, "H": 12, "A": 12, "S": 12},
            "method_note": "Balanced semantic stratification for infrastructure calibration; not a statistical PCA, factor-analysis fit, or acceptance-probability estimator.",
        },
        "award_semantics": {
            "quota_name": "award_recognition",
            "qualifying_statuses": ["winner", "finalist", "nominee", "award"],
            "note": "The quota counts official winner/finalist recognition. Finalists remain labeled finalists; strict winner counts are reported separately by the calibrator.",
        },
        "records": records,
    }
    OUTPUT.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUTPUT} records={len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
