#!/usr/bin/env python3
"""构建可重建的轻量 runtime 与 developer 发行包。

Build reproducible lightweight runtime and developer release bundles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from typing import Iterable

from local_skill_install import STAGED_SHARED_FILES, discover_skills


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_LIMIT = 5 * 1024 * 1024
DEVELOPER_LIMIT = 20 * 1024 * 1024
EXCLUDED_PARTS = {".git", "agent", "dist", "__pycache__"}
EXCLUDED_PREFIXES = {("corpus", "papers"), ("corpus", "extracted")}


def excluded(relative: Path) -> bool:
    parts = relative.parts
    return bool(set(parts) & EXCLUDED_PARTS) or any(parts[: len(prefix)] == prefix for prefix in EXCLUDED_PREFIXES) or relative.suffix in {".pyc", ".pyo"}


def developer_files(root: Path) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root, text=True, capture_output=True, check=False,
    )
    if listed.returncode == 0:
        candidates = [root / line for line in listed.stdout.splitlines() if line]
    else:
        candidates = list(root.rglob("*"))
    return sorted(path for path in candidates if path.is_file() and not excluded(path.relative_to(root)))


def runtime_files(root: Path) -> list[Path]:
    files = [path for path in (root / "common").rglob("*.py") if path.is_file() and not excluded(path.relative_to(root))]
    files.extend(root / relative for relative in STAGED_SHARED_FILES if (root / relative).is_file())
    for skill in discover_skills(root).values():
        files.extend(path for path in skill.rglob("*") if path.is_file() and "tests" not in path.relative_to(skill).parts and not excluded(path.relative_to(root)))
    return sorted(set(files))


def content_hash(root: Path, files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(4, "big")); digest.update(relative)
        data = path.read_bytes(); digest.update(len(data).to_bytes(8, "big")); digest.update(data)
    return digest.hexdigest()


def git_state(root: Path) -> tuple[str | None, bool]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=False)
    return (head.stdout.strip() if head.returncode == 0 else None, status.returncode != 0 or bool(status.stdout.strip()))


def write_zip(root: Path, files: list[Path], output: Path, package_root: str, kind: str, head: str | None, dirty: bool) -> dict:
    digest = content_hash(root, files)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    manifest = {"schema_version": "robotics-research-release.v2", "version": version, "kind": kind, "head_commit": head, "source_dirty": dirty, "content_tree_sha256": digest, "file_count": len(files)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(f"{package_root}/{path.relative_to(root).as_posix()}", date_time=(2020, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        info = zipfile.ZipInfo(f"{package_root}/release-manifest.json", date_time=(2020, 1, 1, 0, 0, 0))
        info.external_attr = 0o100644 << 16
        archive.writestr(info, json.dumps(manifest, sort_keys=True, indent=2).encode() + b"\n", compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    manifest["archive_bytes"] = output.stat().st_size
    manifest["archive_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    return manifest


def build(root: Path, output_dir: Path, *, allow_dirty: bool = False) -> dict:
    root = root.resolve(); head, dirty = git_state(root)
    if dirty and not allow_dirty:
        raise RuntimeError("formal release requires a clean worktree")
    runtime = write_zip(root, runtime_files(root), output_dir / "runtime.zip", "Robotics-Research-Skill-runtime", "runtime", head, dirty)
    developer = write_zip(root, developer_files(root), output_dir / "developer.zip", "Robotics-Research-Skill-developer", "developer", head, dirty)
    if runtime["archive_bytes"] >= RUNTIME_LIMIT:
        raise RuntimeError("runtime.zip exceeds 5 MiB")
    if developer["archive_bytes"] >= DEVELOPER_LIMIT:
        raise RuntimeError("developer.zip exceeds 20 MiB")
    return {"runtime": runtime, "developer": developer, "dirty_source": dirty}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    try:
        result = build(args.root, args.output_dir, allow_dirty=args.allow_dirty)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
