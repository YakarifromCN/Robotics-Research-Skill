"""授权范围内的多仓库内容快照。 / Content snapshots within authorized repository scopes."""
import hashlib
from pathlib import Path
import subprocess

from .canonical import sha256_obj


def snapshot(spec):
    """显式文件清单限制读取；不跟随越界链接。 / Explicit file lists bound reads and reject escaping links."""
    roots = spec.get("roots", [])
    if not roots or not spec.get("authorization"):
        raise ValueError("repository roots and authorization reference required")
    result = []
    seen = set()
    total = 0
    for row in roots:
        if row["id"] in seen:
            raise ValueError("duplicate repository root id")
        seen.add(row["id"])
        root = Path(row["path"]).resolve(strict=True)
        files = row.get("files", [])
        if not files or len(files) > 1000:
            raise ValueError("each root requires 1-1000 explicit files")
        values = {}
        for relative in files:
            if Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise ValueError("repository file must be a safe relative path")
            path = (root / relative).resolve(strict=True)
            path.relative_to(root)
            total += path.stat().st_size
            if total > 64_000_000:
                raise ValueError("repository snapshot exceeds 64 MB; narrow the file list")
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(65536), b""):
                    digest.update(chunk)
            values[relative] = digest.hexdigest()
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5)
        if head.returncode and row.get("kind") != "directory":
            raise ValueError("Git unavailable; non-Git roots require kind=directory")
        dirty = []
        if head.returncode == 0:
            from .project_audit import _git
            for command in (["diff", "--name-only", "--relative", "-z", "HEAD", "--", ".", ":(exclude).robotics-ar"],
                            ["ls-files", "--others", "--exclude-standard", "-z", "--", ".", ":(exclude).robotics-ar"]):
                code, output, _ = _git(root, command)
                if code:
                    raise ValueError("cannot bound repository dirty-file inventory")
                dirty.extend(name for name in output.split("\0") if name)
            if not set(dirty) <= set(files):
                raise ValueError("dirty files outside the explicitly approved snapshot")
        result.append({"id": row["id"], "head": head.stdout.strip() if head.returncode == 0 else None, "files": values, "dirty_files": sorted(set(dirty))})
    return {"schema_version": "robotics-ar-repositories.v1", "spec": spec, "snapshot": result, "sha256": sha256_obj({"spec": spec, "snapshot": result})}


def validate_snapshot(receipt):
    if sha256_obj({"spec": receipt["spec"], "snapshot": receipt["snapshot"]}) != receipt["sha256"]:
        raise ValueError("repository ledger digest mismatch")
    if snapshot(receipt["spec"])["sha256"] != receipt["sha256"]:
        raise ValueError("repository content or HEAD drift; refresh only after authorization")
