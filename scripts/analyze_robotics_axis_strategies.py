"""Entry point for the quota-balanced robotics axis strategy analysis."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_SOURCE = Path(__file__).with_name("analyze_robotics_axis_strategies.py.source")
_namespace = {"__name__": "_researchstudio_axis_analysis_source", "__file__": str(_SOURCE)}
exec(compile(_SOURCE.read_text(encoding="utf-8"), str(_SOURCE), "exec"), _namespace, _namespace)


def _axis_records(records: list[dict], axis: str) -> list[dict]:
    """Use the balanced primary-axis stratum for the baseline report."""

    return [record for record in records if record.get("primary_axis") == axis]


_namespace["_axis_records"] = _axis_records
main = _namespace["main"]
build_report = _namespace["build_report"]


if __name__ == "__main__":
    raise SystemExit(main())
