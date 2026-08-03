"""Authoritative v2 wrapper for the balanced public-paper corpus.

The first builder contains the long, human-auditable paper table.  This
wrapper applies the final curation corrections that were made during hard
validation: keep the TPAMI perception example, replace a weak H-axis sample
with an official RA-L award paper, add two independently traceable award
signals, and remove a duplicated systems/control title.
"""

from __future__ import annotations

import json

from build_public_paper_index import (
    AXES,
    CHECKED_AT,
    CORL_2023_AWARDS,
    ICRA_AWARDS,
    OUTPUT,
    RAS_RAL_AWARDS,
    RSS_2022_AWARDS,
    RSS_2023_AWARDS,
    RAS_TRO_AWARDS,
    build_records,
    award,
    paper,
    presentation,
)


def write_index(records: list[dict[str, object]]) -> None:
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


def build_v2_records() -> list[dict[str, object]]:
    records = build_records()
    by_id = {record["paper_id"]: record for record in records}

    # Keep JRDB in the P axis.  Replace the uncertain HRI journal placeholder
    # with a public RA-L award record whose venue/title/DOI are independently
    # listed in the IEEE RAS award history.
    by_id["J-H06"] = paper(
        "J-H06",
        "2.5D Laser-Cutting-Based Customized Fabrication of Long-Term Wearable Textile sEMG Sensor: From Design to Intention Recognition",
        2022,
        "IEEE Robotics and Automation Letters",
        "journal",
        "H",
        "https://koasas.kaist.ac.kr/handle/10203/298093",
        "https://doi.org/10.1109/LRA.2022.3190620",
        secondary=("P", "E"),
        tags=("wearable_sensor", "semg", "intention_recognition"),
        award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history."),
        public_kind="institutional_public_record",
    )

    # Add an official RA-L award entry to the A axis.
    by_id["J-A03"] = paper(
        "J-A03",
        "Vision-Based Reactive Planning for Aggressive Target Tracking While Avoiding Collisions and Occlusions",
        2018,
        "IEEE Robotics and Automation Letters",
        "journal",
        "A",
        "https://hal.science/hal-01836586/document",
        "https://doi.org/10.1109/LRA.2018.2856526",
        secondary=("P", "C"),
        tags=("reactive_planning", "target_tracking", "occlusion_avoidance"),
        award_info=award("winner", RAS_RAL_AWARDS, "Listed in the IEEE RAS RA-L Best Paper Award history."),
        public_kind="accepted_author_manuscript",
    )

    # RSS Test-of-Time is a distinct, traceable recognition signal; it is not
    # treated as a claim about present-day novelty or acceptance probability.
    rss_record = by_id["C-E03"]
    rss_record["award"] = award(
        "award",
        "https://roboticsconference.org/2025/program/testoftimeaward/",
        "RSS Test-of-Time recognition is retained as an award signal; this is not a claim about current novelty.",
    )

    # Replace the duplicated control/systems entry with an ICRA paper that has
    # a public arXiv version and a final DOI.
    by_id["C-C07"] = paper(
        "C-C07",
        "Safety Under Uncertainty: Tight Bounds with Risk-Aware Control Barrier Functions",
        2023,
        "ICRA",
        "conference",
        "C",
        "https://arxiv.org/abs/2304.01040",
        "https://doi.org/10.1109/ICRA48891.2023.10161379",
        secondary=("A", "P"),
        tags=("risk_aware_control", "stochastic_safety", "control_barrier_function"),
        presentation_info=presentation("ICRA", "oral", "Curated from the ICRA program and public preprint."),
    )

    # Preserve source order so the resulting corpus remains diff-friendly.
    return [by_id[record["paper_id"]] for record in records]


def main() -> int:
    records = build_v2_records()
    write_index(records)
    counts = {axis: sum(record["primary_axis"] == axis for record in records) for axis in AXES}
    awards = sum(record.get("award", {}).get("qualifies_for_quota") is True for record in records)
    print(f"BALANCED_CORPUS: records={len(records)} awards={awards} primary_axes={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
