#!/usr/bin/env python3
"""解析已安装或内置 Humanizer，不下载依赖。 / Resolve installed or bundled Humanizer without downloads."""
import hashlib
import json
import os
from pathlib import Path


def resolve():
    candidate = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills" / "humanizer" / "SKILL.md"
    if candidate.is_file() and 'version: "3.0.0"' in candidate.read_text(encoding="utf-8"):
        path, kind = candidate, "installed"
    else:
        path, kind = Path(__file__).resolve().parents[1] / "references" / "humanizer-academic.md", "bundled-adaptation"
    data = path.read_bytes()
    if kind == "bundled-adaptation":
        manifest = json.loads((Path(__file__).resolve().parents[1] / "assets" / "dependencies.json").read_text())
        if hashlib.sha256(data).hexdigest() != manifest["humanizer"]["bundled_sha256"]:
            raise ValueError("bundled Humanizer digest mismatch")
    return {"status": "READY", "path": str(path), "kind": kind, "version": "3.0.0",
            "sha256": hashlib.sha256(data).hexdigest(), "language_pass_completed": False}


if __name__ == "__main__":
    print(json.dumps(resolve(), ensure_ascii=False))
