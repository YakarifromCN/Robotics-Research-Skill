"""Reject host-specific absolute paths from public corpus JSON artifacts.

检查公开语料中的字符串，禁止把个人机器路径写进版本化产物。
Scan public corpus strings and reject host-specific paths in versioned artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


_DRIVE_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_UNIX_LOCAL_ROOT = re.compile(r"^/(?:mnt|home|Users|Volumes|tmp)(?:/|$)")


def _walk(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def validate_file(path: str | Path) -> list[str]:
    file_path = Path(path)
    data = json.loads(file_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for field_path, value in _walk(data):
        if _DRIVE_ABSOLUTE.match(value) or _UNIX_LOCAL_ROOT.match(value):
            errors.append(f"{file_path}:{field_path}: host-specific absolute path")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check corpus JSON paths are repository-portable.")
    parser.add_argument("root", nargs="?", default="corpus", help="Corpus directory to scan")
    args = parser.parse_args()
    files = sorted(Path(args.root).rglob("*.json"))
    errors = [error for path in files for error in validate_file(path)]
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print(f"PORTABLE_CORPUS_PATHS: PASS files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
