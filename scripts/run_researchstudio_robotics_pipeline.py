"""Direct entrypoint for the complete ResearchStudio robotics pipeline."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_SOURCE = Path(__file__).with_name("run_researchstudio_robotics_pipeline.py.source")
_namespace = {"__name__": "_researchstudio_pipeline_source", "__file__": str(_SOURCE)}
exec(compile(_SOURCE.read_text(encoding="utf-8"), str(_SOURCE), "exec"), _namespace, _namespace)
main = _namespace["main"]


if __name__ == "__main__":
    raise SystemExit(main())
