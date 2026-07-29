"""Materialize the ResearchStudio-inspired robotics infrastructure in one run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common.researchstudio_patterns import validate_pattern_library
from scripts.analyze_robotics_axis_strategies import build_report
from scripts.build_researchstudio_pattern_cards import build_library
from scripts.build_researchstudio_signature_index import build as build_signatures
from scripts.induce_researchstudio_patterns import build as build_clusters
from scripts.validate_public_paper_index import load as load_public
from scripts.validate_robotics_axis_strategy_analysis import validate as validate_axis_report


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete robotics ResearchStudio infrastructure pipeline.")
    parser.add_argument("--strict-real", action="store_true")
    args = parser.parse_args()
    model = ROOT / "corpus" / "robotics-submanifold.v1.json"
    catalog = ROOT / "corpus" / "venue-catalog.v2.json"
    public = ROOT / "corpus" / "public-paper-index.json"
    pattern_path = ROOT / "corpus" / "researchstudio-pattern-cards.v1.json"
    signature_path = ROOT / "corpus" / "researchstudio-paper-signatures.v1.json"
    cluster_path = ROOT / "corpus" / "researchstudio-cluster-analysis.v1.json"
    report_path = ROOT / "corpus" / "robotics-axis-strategy-analysis.v1.json"
    library = build_library()
    _write(pattern_path, library)
    signatures = build_signatures(public)
    _write(signature_path, signatures)
    clusters = build_clusters(signature_path, pattern_path, strict_real=args.strict_real)
    _write(cluster_path, clusters)
    report = build_report(signature_path, pattern_path, catalog, model)
    _write(report_path, report)
    errors = validate_pattern_library(library)
    errors.extend(validate_axis_report(report, signatures, library, load_public(public)))
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print("RESEARCHSTUDIO_ROBOTICS_PIPELINE: PASS")
    print("projection:", clusters["method"]["projection"]["status"])
    print("clustering:", clusters["method"]["clustering"]["status"])
    print("axis_rows:", len(report["axes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
