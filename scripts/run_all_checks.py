#!/usr/bin/env python3
"""Run the repository validation profiles.

The three historical check commands now share this implementation.  The
profile wrappers remain for command-line compatibility, but the command lists
live in one place so a new test is not silently added to only one profile.
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUNTIME_REQUIRED = (
    "common/robotics_research_context.py",
    "common/robotics_research_runtime.py",
    "common/robotics_submanifold.py",
    "common/researchstudio_ideation.py",
    "common/researchstudio_patterns.py",
    "common/_researchstudio_patterns.py",
    "corpus/robotics-research-runtime.v1.json",
    "corpus/robotics-submanifold.v1.json",
    "corpus/researchstudio-pattern-cards.v1.json",
    "corpus/venue-catalog.v2.json",
    "scripts/route_robotics_research.py",
    "scripts/route_robotics_submanifold.py",
)


def validate_runtime_layout() -> None:
    """Reject regressions that pull offline or archived material into runtime."""

    missing = [relative for relative in RUNTIME_REQUIRED if not (ROOT / relative).is_file()]
    source_residue = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.source")]
    active_files = [
        *sorted((ROOT / "common").glob("*.py")),
        ROOT / "scripts/route_robotics_research.py",
        ROOT / "scripts/route_robotics_submanifold.py",
        *sorted((ROOT / "skills").glob("*/SKILL.md")),
    ]
    forbidden: list[str] = []
    for path in active_files:
        text = path.read_text(encoding="utf-8")
        for token in ("archive/legacy-v1", "corpus/venue-catalog.v1.json"):
            if token in text:
                forbidden.append(f"{path.relative_to(ROOT)} -> {token}")
        if path.suffix == ".py":
            tree = ast.parse(text, filename=str(path))
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                for module in modules:
                    if module == "tools" or module.startswith("tools.") or module == "archive" or module.startswith("archive."):
                        forbidden.append(f"{path.relative_to(ROOT)} imports {module}")
    if missing or source_residue or forbidden:
        details = [
            *(f"missing runtime file: {item}" for item in missing),
            *(f"dynamic source residue: {item}" for item in source_residue),
            *(f"active runtime references repository-only content: {item}" for item in forbidden),
        ]
        raise SystemExit("RUNTIME_LAYOUT: FAIL\n" + "\n".join(details))
    print("RUNTIME_LAYOUT: PASS")


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)


def _base_commands(python: str) -> list[list[str]]:
    return [
        [python, "-B", "-m", "unittest", "discover", "-s", str(ROOT / "skills/develop-robotics-idea/tests"), "-v"],
        [python, "-B", "-m", "unittest", "discover", "-s", str(ROOT / "skills/design-robotics-experiment/tests"), "-v"],
        [python, "-B", "-m", "unittest", "discover", "-s", str(ROOT / "skills/write-robotics-paper/tests"), "-v"],
        [python, "-B", "-m", "unittest", "discover", "-s", str(ROOT / "skills/review-robotic-feedback/tests"), "-v"],
        [python, "-B", "-m", "unittest", "discover", "-s", str(ROOT / "skills/robotics-ar/tests"), "-v"],
        [python, "-B", "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_local_skill_install.py", "-v"],
        [python, "-B", str(ROOT / "tests/check_contract_alignment.py")],
        [python, "-B", str(ROOT / "scripts/check_bilingual_layout.py"), str(ROOT)],
    ]


def _extended_commands(python: str) -> list[list[str]]:
    return [
        [python, "-B", str(ROOT / "tools/corpus/validate_robotics_research_runtime.py")],
        [python, "-B", str(ROOT / "scripts/validate_venue_catalog_v2.py")],
        [python, "-B", str(ROOT / "scripts/validate_robotics_submanifold.py"), "--catalog", "corpus/venue-catalog.v2.json"],
        [python, "-B", str(ROOT / "scripts/check_portable_corpus_paths.py")],
        [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_venue_catalog_v2.py", "-v"],
        [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_golden_cases.py", "-v"],
    ]


def _corpus_commands(python: str) -> list[list[str]]:
    return [
        [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_robotics_research_context.py", "-v"],
        [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_researchstudio_infrastructure.py", "-v"],
        [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_researchstudio_completion_v2.py", "-v"],
        [python, "-B", str(ROOT / "tools/corpus/validate_researchstudio_pattern_library.py")],
        [python, "-B", str(ROOT / "tools/corpus/validate_public_paper_fulltext_receipts.py")],
        [python, "-B", str(ROOT / "tools/corpus/validate_researchstudio_pattern_induction_v2.py")],
        [python, "-B", str(ROOT / "tools/corpus/validate_researchstudio_outcome_contrast.py")],
        [python, "-B", str(ROOT / "tools/corpus/validate_robotics_axis_strategy_analysis_v2.py")],
        [python, "-B", str(ROOT / "scripts/validate_unified_workflow_adapter.py")],
        [python, "-B", str(ROOT / "scripts/route_robotics_research.py"), "skills/develop-robotics-idea/assets/research-card.template.json", "--stage", "idea", "--venue", "conf-icra", "--per-axis", "2"],
    ]


def run_profile(profile: str) -> int:
    os.environ.setdefault("PYTHONUTF8", "1")
    validate_runtime_layout()
    python = sys.executable
    for command in _base_commands(python):
        run(command)
    if profile == "default":
        print("ALL_CHECKS: PASS")
        return 0
    for command in _extended_commands(python):
        run(command)
    if profile == "extended":
        print("ALL_CHECKS_V2: PASS")
        return 0
    for command in _corpus_commands(python):
        run(command)
    print("ALL_CHECKS_RUNTIME_FIRST_RESEARCHSTUDIO: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the repository validation profile.")
    parser.add_argument(
        "--profile",
        choices=("default", "extended", "corpus-first"),
        default="default",
        help="default Skill checks, extended compatibility checks, or full corpus-first checks",
    )
    args = parser.parse_args(argv)
    return run_profile(args.profile)


if __name__ == "__main__":
    raise SystemExit(main())
