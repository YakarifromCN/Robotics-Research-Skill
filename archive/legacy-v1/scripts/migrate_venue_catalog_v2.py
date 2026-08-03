"""Create the canonical venue catalog without academic rating fields.

The old v1 catalog is retained as a historical source snapshot.  v2 is the
runtime catalog: it preserves the user's venue set, topic tags, contribution
gates, and the direct-robotics versus strong-related prior, but removes CAA/
CCF rating fields from the routing object.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "corpus" / "venue-catalog.v1.json"
OUTPUT = ROOT / "corpus" / "venue-catalog.v2.json"


def build() -> dict[str, object]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    catalog = copy.deepcopy(source)
    catalog["schema_version"] = "robotics-venue-catalog.v2"
    catalog["catalog_id"] = "robotics-venue-catalog-v2"
    catalog["catalog_status"] = "canonical_runtime_catalog"
    catalog["provenance"] = [
        {
            "source_id": "CAA-2024",
            "authority": "中国自动化学会",
            "title": "推荐学术会议目录（2024年）",
            "scope": "conference_only",
            "source_status": "user_provided_digest",
            "use_in_runtime": "venue discovery and directness/topic semantics only",
        },
        {
            "source_id": "CCF-2026",
            "authority": "中国计算机学会",
            "title": "推荐国际学术会议和期刊目录（2026年）",
            "scope": "conference_and_journal",
            "source_status": "user_provided_digest",
            "use_in_runtime": "venue discovery and directness/topic semantics only",
        },
        {
            "source_id": "USER-ROBOTICS-NATIVE-SUPPLEMENT",
            "authority": "用户补充",
            "title": "机器人领域公认的重要期刊补充",
            "scope": "journal_only",
            "source_status": "user_provided_digest",
            "use_in_runtime": "retain robotics-native venues omitted by computing-centered lists",
        },
    ]
    catalog["rules"] = {
        "direct_robotics": "机器人、无人系统、机电一体化、触觉、HRI 或自动化科学是贡献主体。",
        "robotics_strong_related": "机器人是验证或系统载体，但核心贡献必须落在对应学科。",
        "directness_is_a_prior_not_a_rank": "directness_weight only supplies a routing prior; it is not a quality rank or acceptance model.",
        "routing_is_not_acceptance_prediction": "目录主题、directness 权重和样本数量不能推出录用概率、审稿人行为或声望总分。",
        "official_policy_boundary": "目录用于候选路由；当前投稿规则仍必须通过目标 venue 官方来源刷新 target-fit snapshot。",
    }
    for record in catalog.get("records", []):
        record.pop("ratings", None)
        record["directness_weight"] = 1.0 if record.get("layer") == "direct_robotics" else 0.65
        record["factorization_role"] = "primary_robotics_axis_prior" if record.get("layer") == "direct_robotics" else "strong_related_axis_prior"
    return catalog


def main() -> int:
    catalog = build()
    OUTPUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUTPUT} records={len(catalog.get('records', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
