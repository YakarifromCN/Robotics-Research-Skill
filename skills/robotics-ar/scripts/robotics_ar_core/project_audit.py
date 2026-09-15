"""Read-only project reconstruction for midstream takeover."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Optional

from .atomic_io import optional_report_bytes, atomic_write_json, runtime_root, project_output_directory
from .canonical import sha256_obj
from .models import utc_now
from .receipts import file_sha256, tree_fingerprint
from .structured import write_structured


class ProjectAuditError(RuntimeError):
    """Raised when a read-only audit cannot be completed safely."""


SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", "node_modules"}
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".py", ".sh", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".csv", ".log"}
RESULT_SUFFIXES = {".json", ".jsonl", ".csv", ".yaml", ".yml", ".log", ".txt", ".npz", ".npy", ".pt", ".pth", ".ckpt", ".bag"}
DECLARATION_KEYS = ("core_method", "formal_method", "method", "algorithm", "entry_point")
NUMERIC_METRIC_KEYS = frozenset(
    {
        "accuracy",
        "feasibility_rate",
        "objective",
        "objective_value",
        "score",
        "success_rate",
        "runtime",
        "solve_time",
        "loss",
        "max_constraint_violation",
    }
)


def _git(root: Path, args: list[str]) -> tuple[int, str, str]:
    return _capture(["git", *args], cwd=root)


def _capture(argv, cwd=None, limit=65536, timeout=5.0):
    """对子进程输出和等待设置上限。 / Bound subprocess output and waiting."""
    import selectors
    import signal
    import time

    try:
        process = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    output = bytearray()
    deadline = time.monotonic() + timeout
    complete = False
    try:
        while time.monotonic() < deadline and len(output) <= limit:
            if selector.select(0.05):
                chunk = os.read(process.stdout.fileno(), 8192)
                if not chunk:
                    complete = True
                    break
                output.extend(chunk)
        if not complete:
            return 124, "", "metadata command exceeded output/time budget"
        try:
            code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            return 124, "", "metadata command exceeded time budget"
        text = output.decode("utf-8", errors="replace").strip()
        return (code, text, "") if code == 0 else (code, "", text)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        selector.close()
        process.stdout.close()


def _git_root(root: Path) -> Optional[Path]:
    code, output, _ = _git(root, ["rev-parse", "--show-toplevel"])
    if code != 0 or not output:
        return None
    candidate = Path(output).resolve()
    try:
        root.resolve().relative_to(candidate)
    except ValueError:
        return None
    return candidate


def _process_snapshot(root: Path) -> dict[str, Any]:
    """Record matching live processes without executing project commands."""

    code, output, error = _capture(["ps", "-eo", "pid=,ppid=,stat=,args="])
    if code != 0:
        return {"schema_version": "robotics-ar-process-snapshot.v1", "status": "UNKNOWN", "processes": [], "error": error}
    processes: list[dict[str, Any]] = []
    marker = root.as_posix()
    for line in output.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) < 4 or marker not in parts[3]:
            continue
        processes.append({"pid": parts[0], "ppid": parts[1], "stat": parts[2], "args": parts[3], "status": "DETECTED"})
    return {"schema_version": "robotics-ar-process-snapshot.v1", "status": "PASS", "processes": processes, "created_at": utc_now()}


def _walk_read_only(root: Path, *, max_files=1000, max_bytes=8_000_000, max_seconds=5.0,
                    include=(), exclude=(), hash_files=False, coverage=None) -> list[dict[str, Any]]:
    """流式有界扫描，不展开目录列表。 / Stream a bounded scan without materializing directory listings."""
    import fnmatch
    import time

    if max_files < 1 or max_bytes < 0 or max_seconds <= 0:
        raise ProjectAuditError("invalid audit limits")
    coverage = coverage if coverage is not None else {}
    coverage.update(complete=True, visited=0, content_bytes=0, mode="hash" if hash_files else "metadata")
    entries = []
    started = time.monotonic()
    stack = [os.scandir(root)]
    try:
        while stack:
            if coverage["visited"] >= max_files or time.monotonic() - started >= max_seconds:
                coverage["complete"] = False
                break
            item = next(stack[-1], None)
            if item is None:
                stack.pop().close()
                continue
            coverage["visited"] += 1
            path = Path(item.path)
            relative = path.relative_to(root).as_posix()
            if item.name in SKIP_DIRS or item.name in {"robotics-ar", ".robotics-ar"} or any(fnmatch.fnmatch(relative, p) for p in exclude):
                continue
            if item.is_symlink():
                entries.append({"path": relative, "kind": "symlink", "status": "UNKNOWN", "target": os.readlink(path)})
            elif item.is_dir(follow_symlinks=False):
                stack.append(os.scandir(path))
            elif item.is_file(follow_symlinks=False):
                if include and not any(fnmatch.fnmatch(relative, p) for p in include):
                    continue
                size = item.stat(follow_symlinks=False).st_size
                content = size <= 1_000_000 and coverage["content_bytes"] + size <= max_bytes
                if content:
                    coverage["content_bytes"] += size
                else:
                    coverage["complete"] = False
                entries.append({"path": relative, "kind": "file", "status": "DETECTED", "bytes": size,
                                "sha256": file_sha256(path) if hash_files and content else None,
                                "suffix": path.suffix.lower() if content else "", "content_checked": content})
    finally:
        for iterator in stack:
            iterator.close()
    return sorted(entries, key=lambda item: item["path"])


def _fact(status: str, value: Any, source: str) -> dict[str, Any]:
    return {"status": status, "value": value, "source": source}


def _read_small_text(path: Path, *, limit: int = 2_000_000) -> str:
    """Read bounded text during the audit without executing project code."""

    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _normalise_claim(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().strip("`'\".,;:")).lower()


def _extract_declarations(entries: list[dict[str, Any]], root: Path) -> dict[str, list[dict[str, str]]]:
    """Extract explicit method/entry declarations for contradiction checks.

    The audit never guesses a method from arbitrary prose.  Only explicit
    ``key: value``/``key = value`` declarations are compared, which keeps a
    natural-language README from being promoted to a scientific fact.
    """

    pattern = re.compile(
        r"^\s*(?:[#/;*-]+\s*)?(core_method|formal_method|method|algorithm|entry_point)\s*[:=]\s*['\"]?([^#\n\"']+)",
        re.IGNORECASE | re.MULTILINE,
    )
    declarations: dict[str, list[dict[str, str]]] = {}
    for item in entries:
        if item.get("kind") != "file" or item.get("suffix") not in TEXT_SUFFIXES:
            continue
        path = root / str(item["path"])
        for key, raw_value in pattern.findall(_read_small_text(path)):
            value = _normalise_claim(raw_value)
            if value:
                declarations.setdefault(key.lower(), []).append({"path": item["path"], "value": value})
    return declarations


def _walk_numeric_values(value: Any, *, prefix: str = "") -> list[tuple[str, float]]:
    """Collect explicit numeric metric claims from structured artifacts."""

    claims: list[tuple[str, float]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in NUMERIC_METRIC_KEYS:
                candidate = child.get("value", child.get("mean")) if isinstance(child, Mapping) else child
                try:
                    claims.append((key_text, float(candidate)))
                except (TypeError, ValueError):
                    pass
            claims.extend(_walk_numeric_values(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            claims.extend(_walk_numeric_values(child, prefix=f"{prefix}[{index}]"))
    return claims


def _extract_metric_claims(entries: list[dict[str, Any]], root: Path) -> dict[str, list[dict[str, Any]]]:
    claims: dict[str, list[dict[str, Any]]] = {}
    for item in entries:
        if item.get("kind") != "file" or item.get("suffix") not in {".json", ".yaml", ".yml"}:
            continue
        path = root / str(item["path"])
        try:
            raw = _read_small_text(path)
            if item.get("suffix") == ".json":
                value = json.loads(raw)
            else:
                import yaml  # type: ignore

                value = yaml.safe_load(raw)
        except (OSError, ValueError, ImportError):
            continue
        except Exception:
            # YAML parsers raise implementation-specific parse exceptions.
            # A malformed artifact is an audit fact, not a reason to abort the
            # entire read-only reconstruction.
            continue
        for key, numeric in _walk_numeric_values(value):
            claims.setdefault(key, []).append({"path": item["path"], "value": numeric})
    return claims


def _find_discrepancies(entries: list[dict[str, Any]], root: Path, candidates: list[str]) -> list[dict[str, Any]]:
    """Compare only explicit cross-artifact claims and return audit findings."""

    findings: list[dict[str, Any]] = []
    declarations = _extract_declarations(entries, root)
    for key, claims in declarations.items():
        values = sorted({claim["value"] for claim in claims})
        if len(values) > 1:
            findings.append(
                {
                    "id": f"AUDIT-METHOD-{len(findings) + 1:03d}",
                    "kind": "CODE_DOCUMENT_CONFLICT",
                    "severity": "MAJOR",
                    "status": "CONTRADICTED",
                    "field": key,
                    "values": values,
                    "sources": claims,
                    "requires_reconciliation": True,
                }
            )
    metric_claims = _extract_metric_claims(entries, root)
    for key, claims in metric_claims.items():
        values = sorted({claim["value"] for claim in claims})
        if len(values) > 1 and len(claims) > 1:
            findings.append(
                {
                    "id": f"AUDIT-METRIC-{len(findings) + 1:03d}",
                    "kind": "CONFIG_RESULT_CONFLICT",
                    "severity": "MAJOR",
                    "status": "CONTRADICTED",
                    "field": key,
                    "values": values,
                    "sources": claims,
                    "requires_reconciliation": True,
                }
            )
    if not candidates:
        findings.append(
            {
                "id": "AUDIT-ENTRY-001",
                "kind": "FORMAL_ENTRY_MISSING",
                "severity": "MAJOR",
                "status": "UNKNOWN",
                "candidates": [],
                "requires_reconciliation": True,
            }
        )
    elif len(candidates) > 1:
        findings.append(
            {
                "id": "AUDIT-ENTRY-002",
                "kind": "MULTIPLE_FORMAL_ENTRY_CANDIDATES",
                "severity": "MAJOR",
                "status": "CONTRADICTED",
                "candidates": sorted(candidates),
                "requires_reconciliation": True,
            }
        )
    return findings


def audit_project(project_root: Path | str, *, output_dir: Optional[Path | str] = None, **scan_options) -> dict[str, Any]:
    """Scan repository facts and artifacts without executing project commands."""

    root = Path(project_root).resolve()
    if not root.exists() or not root.is_dir():
        raise ProjectAuditError(f"project root does not exist: {root}")
    target = project_output_directory(root, output_dir or runtime_root(root) / "takeover" / "audit")
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ProjectAuditError("audit output must be inside project root") from exc
    target.mkdir(parents=True, exist_ok=True)
    coverage = {}
    entries = _walk_read_only(root, coverage=coverage, **scan_options)
    git_root = _git_root(root)
    code, branch, branch_err = _git(root, ["branch", "--show-current"])
    head_code, head, head_err = _git(root, ["rev-parse", "HEAD"])
    dirty_code, dirty_output, dirty_err = _git(root, ["status", "--porcelain"])
    worktrees_code, worktrees, _ = _git(root, ["worktree", "list", "--porcelain"])
    tracked_code, tracked, _ = _git(root, ["ls-files"])
    text_files = [item for item in entries if item.get("kind") == "file" and item.get("suffix") in TEXT_SUFFIXES]
    result_files = [item for item in entries if item.get("kind") == "file" and item.get("suffix") in RESULT_SUFFIXES]
    candidates = [
        item["path"]
        for item in text_files
        if any(token in item["path"].lower() for token in ("run", "train", "eval", "experiment", "launch", "simulate", "environment", "adapter"))
        and not any(token in item["path"].lower() for token in ("config", "readme", "report", "handoff", "task"))
    ]
    manifests = [item["path"] for item in text_files if item["path"].lower().endswith(("environment-manifest.json", "environment.yaml", "environment.yml", "manifest.json"))]
    discrepancies = _find_discrepancies(entries, root, candidates)
    unknown_entries = [item for item in entries if item.get("status") == "UNKNOWN"]
    discrepancies.extend({"id": f"AUDIT-UNKNOWN-{index:03d}", "kind": "UNREADABLE_OR_SYMLINK", "severity": "MINOR", **item} for index, item in enumerate(unknown_entries, 1))
    requires_reconciliation = any(item.get("requires_reconciliation") for item in discrepancies)
    execution_status = "UNKNOWN" if not candidates else ("CONTRADICTED" if len(candidates) > 1 else "DETECTED")
    discrepancy_status = "CONTRADICTED" if requires_reconciliation else ("DETECTED" if discrepancies else "PASS")
    snapshot = {
        "schema_version": "robotics-ar-project-snapshot.v1",
        "project_root": root.as_posix(),
        "created_at": utc_now(),
        "repository": {
            "git_root": git_root.as_posix() if git_root else None,
            "branch": branch if code == 0 else "UNKNOWN",
            "head": head if head_code == 0 else "UNKNOWN",
            "dirty": bool(dirty_output) if dirty_code == 0 else True,
            "dirty_output": dirty_output,
            "worktrees": worktrees,
            "tracked_files": tracked.splitlines() if tracked_code == 0 else [],
            "errors": [item for item in (branch_err, head_err, dirty_err) if item],
        },
        "entries": entries,
        "facts": {
            "repository": _fact("EXECUTION_VERIFIED" if git_root else "UNKNOWN", {"branch": branch, "head": head, "dirty": bool(dirty_output)}, "git"),
            "execution_candidates": _fact("DETECTED", candidates, "read-only path scan"),
            "environment_candidates": _fact("DETECTED" if manifests else "UNKNOWN", manifests, "read-only path scan"),
            "result_artifacts": _fact("DETECTED", len(result_files), "read-only path scan"),
            "formal_entry": _fact(execution_status, candidates, "explicit path candidate scan"),
            "discrepancies": _fact(discrepancy_status, discrepancies, "explicit cross-artifact comparison"),
        },
    }
    snapshot["snapshot_sha256"] = sha256_obj(snapshot)
    atomic_write_json(target / "project-snapshot.json", snapshot)
    repository_lines = ["# Repository map", "", f"Root: `{root}`", f"Git root: `{git_root or 'UNKNOWN'}`", f"Branch: `{branch or 'UNKNOWN'}`", f"HEAD: `{head or 'UNKNOWN'}`", f"Dirty: `{bool(dirty_output) if dirty_code == 0 else 'UNKNOWN'}`", "", "## Files", "", *[f"- `{item['path']}` ({item.get('bytes', 0)} bytes)" for item in entries if item.get("kind") == "file"], ""]
    optional_report_bytes(target / "repository-map.md", "\n".join(repository_lines).encode("utf-8"))
    write_structured(target / "execution-map.yaml", {"schema_version": "robotics-ar-execution-map.v1", "candidates": candidates, "commands_executed": [], "status": "READ_ONLY_DISCOVERY", "requires_user_selection": len(candidates) != 1, "requires_reconciliation": requires_reconciliation})
    write_structured(target / "method-artifact-index.yaml", {"schema_version": "robotics-ar-method-artifact-index.v1", "files": [item for item in entries if item.get("kind") == "file" and any(token in item["path"].lower() for token in ("method", "model", "algorithm", "paper", "readme", "agent"))]})
    with (target / "result-artifact-index.jsonl").open("w", encoding="utf-8") as handle:
        for item in result_files:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    write_structured(target / "environment-candidates.yaml", {"schema_version": "robotics-ar-environment-candidates.v1", "candidates": manifests, "status": "CANDIDATES_ONLY"})
    write_structured(target / "current-processes.yaml", _process_snapshot(root))
    if dirty_code != 0:
        discrepancies.append({"id": "AUDIT-GIT-001", "kind": "GIT_STATUS_UNAVAILABLE", "severity": "MAJOR", "status": "UNKNOWN", "reason": dirty_err or "git status unavailable", "requires_reconciliation": True})
    snapshot["facts"]["discrepancies"] = _fact("CONTRADICTED" if any(item.get("requires_reconciliation") for item in discrepancies) else ("DETECTED" if discrepancies else "PASS"), discrepancies, "explicit cross-artifact comparison")
    snapshot["snapshot_sha256"] = sha256_obj(snapshot)
    atomic_write_json(target / "project-snapshot.json", snapshot)
    write_structured(target / "discrepancies.json", {"schema_version": "robotics-ar-discrepancies.v1", "status": snapshot["facts"]["discrepancies"]["status"], "requires_reconciliation": any(item.get("requires_reconciliation") for item in discrepancies), "items": discrepancies, "snapshot_sha256": snapshot["snapshot_sha256"]})
    optional_report_bytes(target / "discrepancies.md", ("# Discrepancies\n\n" + ("\n".join(f"- **{item.get('kind', 'UNKNOWN')}** `{item.get('status', 'UNKNOWN')}`: `{item}`" for item in discrepancies) or "- None detected by explicit checks.") + "\n").encode("utf-8"))
    receipt = {"schema_version": "robotics-ar-project-audit-receipt.v1", "status": "PASS", "project_snapshot_sha256": snapshot["snapshot_sha256"], "read_only": True, "commands_executed": [], "discrepancies": discrepancies, "requires_reconciliation": any(item.get("requires_reconciliation") for item in discrepancies), "created_at": utc_now()}
    receipt["coverage"] = coverage
    if not coverage["complete"]:
        receipt["status"] = "PARTIAL"
        receipt["requires_reconciliation"] = True
    receipt["receipt_sha256"] = sha256_obj(receipt)
    atomic_write_json(target / "audit-receipt.json", receipt)
    # The concise artifacts requested by the product contract are aliases with
    # explicit provenance, not replacements for the structured audit files.
    optional_report_bytes(target / "current-state.md", ("# Current State\n\n" + f"Snapshot: `{snapshot['snapshot_sha256']}`\n\n" + f"Git dirty: `{snapshot['repository']['dirty']}`\n").encode("utf-8"))
    optional_report_bytes(target / "known-failures.md", b"# Known failures\n\nNo failure was upgraded from an unverified scan.\n")
    optional_report_bytes(target / "unresolved-questions.md", ("# Unresolved questions\n\n" + "\n".join(f"- {item}" for item in snapshot["facts"]["environment_candidates"]["value"]) + "\n").encode("utf-8"))
    return {"status": receipt["status"], "snapshot": snapshot, "receipt": receipt, "output_dir": target.as_posix()}
