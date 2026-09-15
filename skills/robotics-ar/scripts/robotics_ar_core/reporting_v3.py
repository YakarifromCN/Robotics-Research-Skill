"""Detailed, disk-reconstructable report and handoff for Robot-AR v3."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Optional

from .atomic_io import atomic_write_bytes
from .canonical import sha256_obj
from .models import utc_now


def _git(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _mapping(path: Path, *, root: Optional[Path] = None) -> Optional[dict[str, Any]]:
    if root is not None and not _inside(path, root):
        return None
    try:
        from .structured import read_mapping

        if path.is_file():
            return read_mapping(path)
    except (OSError, ValueError, TypeError):
        return None
    return None


def _load_v3_context(manager: Any, supplied: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct report inputs from state and receipts, never from chat memory."""

    context = dict(supplied)
    if manager.state.get("entry_mode", "NEW_RESEARCH") != "MIDSTREAM_TAKEOVER":
        return context
    paths = manager.paths
    core_path = Path(str(manager.state.get("project_core_path", paths.takeover / "project-core.yaml")))
    contract_path = Path(str(manager.state.get("contract_path", ""))) if manager.state.get("contract_path") else paths.takeover_contracts / "batch-001.yaml"
    baseline_path = Path(str(manager.state.get("baseline_receipt_path", paths.takeover_baseline / "baseline-receipt.json")))
    for key, path, root in (
        ("project_core", core_path, paths.takeover),
        ("contract", contract_path, paths.takeover_contracts),
        ("baseline", baseline_path, paths.takeover_baseline),
    ):
        if key not in context:
            loaded = _mapping(path, root=root)
            if loaded is not None:
                context[key] = loaded

    if "best_known" not in context:
        loaded = _mapping(paths.best_known, root=paths.root)
        if loaded is not None:
            context["best_known"] = loaded

    if "environment" not in context:
        environment_path = Path(str(manager.state.get("environment_receipt_path", paths.takeover / "environment-receipt.yaml")))
        loaded = _mapping(environment_path, root=paths.takeover)
        if loaded is not None:
            context["environment"] = loaded
    context.setdefault("current_goal", (context.get("project_core") or {}).get("current_batch_goal", "UNKNOWN"))
    context.setdefault("project_core_path", core_path.as_posix())
    context.setdefault("contract_path", contract_path.as_posix())
    context.setdefault("baseline_receipt_path", baseline_path.as_posix())
    context.setdefault("task_path", manager.state.get("task_path", "UNKNOWN"))
    context.setdefault("task_sha256", manager.state.get("task_sha256", "UNKNOWN"))

    trials = list(context.get("trials", [])) if isinstance(context.get("trials", []), list) else []
    batch_id = str(context.get("batch_id", ""))
    if batch_id:
        checkpoint = paths.experiments / batch_id / "batch-checkpoint.json"
        loaded = _mapping(checkpoint, root=paths.experiments)
        if loaded is not None:
            context.setdefault("batch_checkpoint", loaded)
            if not trials:
                trials.extend(item for item in loaded.get("results", []) if isinstance(item, Mapping))
    if not trials:
        for receipt_path in sorted(paths.experiments.glob("*/decision-receipt.json")):
            loaded = _mapping(receipt_path, root=paths.experiments)
            if loaded is not None:
                trials.append(loaded)
    context["trials"] = trials

    if "history_records" not in context:
        history_path = paths.takeover_history / "experiment-ledger.jsonl"
        records: list[dict[str, Any]] = []
        if _inside(history_path, paths.takeover_history) and history_path.is_file():
            for line in history_path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, Mapping):
                    records.append(dict(value))
        context["history_records"] = records

    process_path = paths.root / "process-registry.json"
    context.setdefault("processes", _mapping(process_path, root=paths.root) or {"status": "NOT_RECORDED", "processes": []})
    lease_path = paths.project_root / ".robotics-ar-writer.lock"
    context.setdefault("writer_lease", lease_path.read_text(encoding="utf-8", errors="replace").strip() if lease_path.is_file() else "NONE")
    context.setdefault("worktrees", _git(paths.project_root, ["worktree", "list", "--porcelain"]))
    context.setdefault("environment_fingerprint", manager.state.get("environment_fingerprint", (context.get("environment") or {}).get("fingerprint", "UNKNOWN")))

    baseline = context.get("baseline") or {}
    spec = _mapping(paths.takeover_baseline / "baseline-spec.yaml", root=paths.takeover_baseline) or {}
    context.setdefault("reproduction_commands", [" ".join(map(str, baseline.get("command", [])))] if baseline.get("command") else ([" ".join(map(str, spec.get("command", [])))] if spec.get("command") else []))
    batch_checkpoint = context.get("batch_checkpoint") or {}
    resume_batch_id = batch_id or str((batch_checkpoint.get("batch") or {}).get("batch_id", ""))
    if resume_batch_id:
        checkpoint_path = paths.experiments / resume_batch_id / "batch-checkpoint.json"
        contract_arg = context.get("contract_path", manager.state.get("contract_path", ""))
        receipt_arg = manager.state.get("environment_receipt_path", paths.takeover / "environment-receipt.yaml")
        context.setdefault("resume_command", f"python3 skills/robotics-ar/scripts/robotics_ar.py batch-resume --project-root {paths.project_root} --batch-id {resume_batch_id} --checkpoint {checkpoint_path} --contract {contract_arg} --receipt {receipt_arg}")
    else:
        context.setdefault("resume_command", f"python3 skills/robotics-ar/scripts/robotics_ar.py takeover-status --project-root {paths.project_root}")
    return context


def _best_lines(best: Mapping[str, Any]) -> list[str]:
    primary = best.get("current_primary_best")
    stable = best.get("current_stable_best")
    pareto = best.get("pareto_candidates", [])
    return [
        f"- Primary: `{primary.get('trial_id', 'UNKNOWN') if isinstance(primary, Mapping) else 'UNKNOWN'}` {primary if primary else 'UNKNOWN'}",
        f"- Stable: `{stable.get('trial_id', 'UNKNOWN') if isinstance(stable, Mapping) else 'UNKNOWN'}` {stable if stable else 'UNKNOWN'}",
        f"- Pareto candidates: `{len(pareto) if isinstance(pareto, list) else 0}`",
    ]


def write_current_report(manager: Any, *, context: Optional[Mapping[str, Any]] = None, reason: str = "") -> Path:
    context = _load_v3_context(manager, context or {})
    state = manager.state
    core = context.get("project_core", {}) if isinstance(context.get("project_core", {}), Mapping) else {}
    contract = context.get("contract", {}) if isinstance(context.get("contract", {}), Mapping) else {}
    baseline = context.get("baseline", {}) if isinstance(context.get("baseline", {}), Mapping) else {}
    best = context.get("best_known", {}) if isinstance(context.get("best_known", {}), Mapping) else {}
    trials = context.get("trials", []) if isinstance(context.get("trials", []), list) else []
    lines = [
        "# Robot-AR Current Report", "",
        "## Session and Entry Mode", "", f"- Session: `{state.get('session_id')}`", f"- Entry mode: `{state.get('entry_mode', 'NEW_RESEARCH')}`", f"- State: `{state.get('state')}`", "",
        "## Current Goal", "", str(core.get("current_batch_goal", context.get("current_goal", "UNKNOWN"))), "",
        "## Project Core", "", f"- Project: `{core.get('project_id', 'UNKNOWN')}`", f"- Core path: `{context.get('project_core_path', 'UNKNOWN')}`", f"- Core hash: `{core.get('project_core_sha256', state.get('project_core_sha256', 'UNKNOWN'))}`", f"- Frozen invariants: {core.get('frozen_invariants', 'UNKNOWN')}", "",
        "## Current Bottleneck", "", str(core.get("current_bottleneck", context.get("current_bottleneck", "UNKNOWN"))), "",
        "## Active Trial Contract", "", f"- Path: `{context.get('contract_path', 'UNKNOWN')}`", f"- Contract: `{contract.get('contract_id', 'UNKNOWN')}`", f"- Contract hash: `{contract.get('contract_sha256', state.get('contract_sha256', 'UNKNOWN'))}`", f"- Approval: `{contract.get('status', 'UNKNOWN')}`", "",
        "## Baseline", "", f"- Spec/receipt: `{context.get('baseline_receipt_path', 'UNKNOWN')}`", f"- Status: `{baseline.get('reproduction_status', baseline.get('status', 'UNKNOWN'))}`", f"- Receipt: `{baseline.get('receipt_sha256', state.get('baseline_receipt_sha256', 'UNKNOWN'))}`", "",
        "## Best-Known State", "", *_best_lines(best), "",
        "## Trials Completed in This Batch", "", *[f"- `{item.get('trial_id', 'UNKNOWN')}`: `{item.get('decision', item.get('status', 'UNKNOWN'))}`" for item in trials if isinstance(item, Mapping)], "",
        "## Kept Results", "", *[f"- {item}" for item in _lines(context.get("kept_results", []))], "",
        "## Reverted / Negative Results", "", *[f"- {item}" for item in _lines(context.get("negative_results", []))], "",
        "## Invalid or Inconclusive Results", "", *[f"- {item}" for item in _lines(context.get("invalid_results", []))], "",
        "## Current Failure Modes", "", *[f"- {item}" for item in _lines(context.get("failure_modes", []))], "",
        "## Dynamic Expert Consensus", "", str(context.get("expert_consensus", "UNKNOWN")), "",
        "## Environment Status", "", str(context.get("environment", {"fingerprint": state.get("environment_fingerprint", "UNKNOWN")})), "",
        "## Code / Branch / Worktree Status", "", f"- Branch: `{_git(manager.paths.project_root, ['branch', '--show-current'])}`", f"- Commit: `{_git(manager.paths.project_root, ['rev-parse', 'HEAD'])}`", f"- Dirty: `{manager.dirty_git()}`", "",
        "## Resource Consumption and Remaining Budget", "", str(context.get("budget", state.get("exploration_budget", {}))), "",
        "## Why Execution Paused", "", reason or str(context.get("pause_reason", "Not paused")), "",
        "## Decisions Required From User", "", *[f"- {item}" for item in _lines(context.get("decisions_required", []))], "",
        "## Recommended Next Action", "", str(context.get("recommended_next_action", "Validate the hashes and resume only within the approved contract.")), "",
        f"Generated: `{utc_now()}`", "",
    ]
    path = manager.paths.root_report
    text = "\n".join(lines)
    atomic_write_bytes(path, text.encode("utf-8"))
    return path


def write_current_handoff(manager: Any, *, context: Optional[Mapping[str, Any]] = None, reason: str = "") -> Path:
    context = _load_v3_context(manager, context or {})
    state = manager.state
    checkpoint = context.get("last_checkpoint", manager.paths.checkpoints.as_posix())
    batch_id = context.get("batch_id", ((context.get("batch_checkpoint") or {}).get("batch") or {}).get("batch_id", "UNKNOWN"))
    trial_id = context.get("trial_id", "UNKNOWN")
    core = context.get("project_core", {}) if isinstance(context.get("project_core", {}), Mapping) else {}
    contract = context.get("contract", {}) if isinstance(context.get("contract", {}), Mapping) else {}
    baseline = context.get("baseline", {}) if isinstance(context.get("baseline", {}), Mapping) else {}
    best = context.get("best_known", {}) if isinstance(context.get("best_known", {}), Mapping) else {}
    lines = [
        "# Robot-AR Handoff", "",
        "## Current State", "", f"- Session: `{state.get('session_id')}`", f"- Entry mode: `{state.get('entry_mode', 'NEW_RESEARCH')}`", f"- State: `{state.get('state')}`", "",
        "## Last Stable Checkpoint", "", str(checkpoint), "",
        "## Active Session / Batch / Trial", "", f"- Batch: `{batch_id}`", f"- Trial: `{trial_id}`", "",
        "## Active Contract", "", f"- ID: `{contract.get('contract_id', 'UNKNOWN')}`", f"- Path: `{context.get('contract_path', state.get('contract_path', 'UNKNOWN'))}`", f"- Hash: `{contract.get('contract_sha256', context.get('contract_sha256', state.get('contract_sha256', 'UNKNOWN')))}`", "",
        "## Project Core", "", f"- Project: `{core.get('project_id', 'UNKNOWN')}`", f"- Path: `{context.get('project_core_path', state.get('project_core_path', 'UNKNOWN'))}`", f"- Hash: `{core.get('project_core_sha256', context.get('project_core_sha256', state.get('project_core_sha256', 'UNKNOWN')))}`", "",
        "## Baseline Receipt", "", f"- Path: `{context.get('baseline_receipt_path', state.get('baseline_receipt_path', 'UNKNOWN'))}`", f"- Hash: `{baseline.get('receipt_sha256', state.get('baseline_receipt_sha256', 'UNKNOWN'))}`", f"- Reproduction status: `{baseline.get('reproduction_status', 'UNKNOWN')}`", "",
        "## Current Best Receipt", "", f"- Path: `{context.get('best_known_path', manager.paths.best_known)}`", f"- Trial: `{(best.get('latest_trial') or {}).get('trial_id', 'UNKNOWN') if isinstance(best.get('latest_trial'), Mapping) else 'UNKNOWN'}`", "",
        "## Active Task", "", f"- Path: `{context.get('task_path', state.get('task_path', 'UNKNOWN'))}`", f"- Hash: `{context.get('task_sha256', state.get('task_sha256', 'UNKNOWN'))}`", "",
        "## Git Branch / Commit / Dirty Diff", "", f"- Branch: `{_git(manager.paths.project_root, ['branch', '--show-current'])}`", f"- Commit: `{_git(manager.paths.project_root, ['rev-parse', 'HEAD'])}`", f"- Dirty: `{manager.dirty_git()}`", "",
        "## Worktrees and Writer Leases", "", str(context.get("worktrees", "UNKNOWN")), f"- Writer lease: `{context.get('writer_lease', 'UNKNOWN')}`", "",
        "## Running or Stopped Processes", "", str(context.get("processes", "UNKNOWN")), "",
        "## Environment Fingerprint", "", str(context.get("environment_fingerprint", state.get("environment_fingerprint", "UNKNOWN"))), "",
        "## Logs and Artifact Paths", "", *[f"- {item}" for item in _lines(context.get("artifacts", [manager.paths.experiments.as_posix(), manager.paths.takeover.as_posix()]))], "",
        "## Exact Reproduction Commands", "", *[f"- `{item}`" for item in _lines(context.get("reproduction_commands", []))], "",
        "## Exact Resume Command", "", f"`{context.get('resume_command', f'python3 skills/robotics-ar/scripts/robotics_ar.py takeover-status --project-root {manager.paths.project_root}')}`", "",
        "## Known Risks", "", *[f"- {item}" for item in _lines(context.get("known_risks", []))], "",
        "## Pending User Decision", "", *[f"- {item}" for item in _lines(context.get("decisions_required", []))], "",
        "## Safe Rollback Point", "", str(context.get("rollback_point", baseline.get("code", {}).get("commit", _git(manager.paths.project_root, ["rev-parse", "HEAD"])) if isinstance(baseline.get("code", {}), Mapping) else _git(manager.paths.project_root, ["rev-parse", "HEAD"]))), "",
        f"Reason: {reason or context.get('pause_reason', 'checkpoint')}", "",
        f"Handoff hash: `{sha256_obj({'state': state, 'context': context, 'reason': reason})}`", "",
    ]
    path = manager.paths.root_handoff
    text = "\n".join(lines)
    atomic_write_bytes(path, text.encode("utf-8"))
    return path


def write_checkpoint_artifacts(manager: Any, *, context: Optional[Mapping[str, Any]] = None, reason: str = "checkpoint") -> tuple[Optional[Path], Optional[Path]]:
    from .atomic_io import report_files_requested
    if not report_files_requested():
        return None, None
    return write_current_report(manager, context=context, reason=reason), write_current_handoff(manager, context=context, reason=reason)
