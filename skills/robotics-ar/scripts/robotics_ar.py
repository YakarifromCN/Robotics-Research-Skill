#!/usr/bin/env python3
"""提供 Robotics-AR 的确定性 CLI。

Provide the deterministic Robotics-AR command-line interface.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from robotics_ar_core.environment import EnvironmentAdapter, EnvironmentError, validate_environment_receipt  # noqa: E402
from robotics_ar_core.reporting import write_handoff, write_report  # noqa: E402
from robotics_ar_core.session import SessionError, SessionManager  # noqa: E402
from robotics_ar_core.sibling_skill_adapter import SiblingAdapterError, SiblingSkillInvocationAdapter  # noqa: E402
from robotics_ar_core.takeover import TakeoverError, TakeoverManager, build_intake  # noqa: E402
from robotics_ar_core.project_audit import ProjectAuditError, audit_project  # noqa: E402
from robotics_ar_core.history_reconstruction import HistoryError, reconstruct_history  # noqa: E402
from robotics_ar_core.project_core import ProjectCoreError, compile_project_core, load_project_core, save_project_core, mark_project_core_approved, assert_project_core_approved, core_hash  # noqa: E402
from robotics_ar_core.baseline import BaselineError, compile_baseline_spec, reproduce_baseline, assert_baseline_usable, recover_baseline  # noqa: E402
from robotics_ar_core.trial_contract import TrialContractError, TrialContractManager, compile_trial_contract  # noqa: E402
from robotics_ar_core.trial_queue import TrialQueueError, TrialQueue, build_proposal, validate_proposal, validate_trial_id  # noqa: E402
from robotics_ar_core.trial_loop import TrialLoopError, TrialDecisionEngine  # noqa: E402
from robotics_ar_core.best_known import BestKnownError, BestKnownState  # noqa: E402
from robotics_ar_core.batch_controller import BatchControllerError, BatchController, compile_batch  # noqa: E402
from robotics_ar_core.user_correction import UserCorrectionError, compile_correction, confirm_and_resume  # noqa: E402
from robotics_ar_core.reporting_v3 import write_current_handoff, write_current_report  # noqa: E402
from robotics_ar_core.structured import read_mapping, write_structured  # noqa: E402
from robotics_ar_core.agent_protocol import validate_agent_receipt  # noqa: E402
from robotics_ar_core.migration import migrate_project  # noqa: E402
from robotics_ar_core.canonical import sha256_obj  # noqa: E402
from robotics_ar_core.models import utc_now  # noqa: E402


class CLIError(RuntimeError):
    """CLI 参数或 gate 失败。 / Raised for CLI argument or gate failures."""


def _manager(args: argparse.Namespace) -> SessionManager:
    return SessionManager(args.project_root)


def _split(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_json(path: Path | str) -> Dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CLIError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CLIError(f"JSON object required: {path}")
    return value


def _load_structured(path: Path | str) -> Dict[str, Any]:
    try:
        return read_mapping(path)
    except Exception as exc:
        raise CLIError(f"cannot read structured artifact: {path}") from exc


def _dry(args: argparse.Namespace, action: str, **extra: Any) -> Dict[str, Any]:
    return {"status": "DRY_RUN", "action": action, **extra}


def _metric_versions(value: Mapping[str, Any]) -> Dict[str, str]:
    """Extract only explicitly declared metric versions from an artifact."""

    result: Dict[str, str] = {}
    explicit = value.get("metric_versions")
    if isinstance(explicit, Mapping):
        result.update({str(key): str(item) for key, item in explicit.items() if item not in (None, "")})
    metrics = value.get("metrics")
    if isinstance(metrics, Mapping):
        for name, item in metrics.items():
            if isinstance(item, Mapping):
                version = item.get("metric_version", item.get("version", item.get("version_id")))
                if version not in (None, ""):
                    result.setdefault(str(name), str(version))
    return result


def _load_optional_mapping(value: Any, *, label: str) -> Optional[Dict[str, Any]]:
    """Accept an embedded mapping or a path supplied by a CLI input artifact."""

    if isinstance(value, Mapping):
        return dict(value)
    if value in (None, ""):
        return None
    try:
        return _load_structured(str(value))
    except CLIError as exc:
        raise CLIError(f"cannot load {label}: {value}") from exc


def _trial_usage(manager: SessionManager, *, current_trial_id: str) -> tuple[int, int]:
    """Count persisted trial runs and still-open run receipts for contract gates."""

    used = 0
    parallel = 0
    if not manager.paths.experiments.exists():
        return used, parallel
    for trial_dir in manager.paths.experiments.iterdir():
        if not trial_dir.is_dir():
            continue
        has_run = any((trial_dir / name).is_file() for name in ("run-receipt.json", "run-manifest.yaml", "decision-receipt.json"))
        if not has_run:
            continue
        used += 1
        if (trial_dir / "run-receipt.json").is_file() and not (trial_dir / "decision-receipt.json").is_file():
            parallel += 1
    return used, parallel


def command_discover(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = SiblingSkillInvocationAdapter(args.robotics_research_root)
    manifest = adapter.discover()
    path = Path(args.project_root).resolve() / ".robotics-ar" / "sibling-skills" / "manifest.json"
    if args.dry_run:
        return _dry(args, "discover", manifest=manifest, path=path.as_posix())
    adapter.write_manifest(path, manifest)
    return {"status": "PASS", "manifest_path": path.as_posix(), "manifest": manifest}


def command_init(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "init", project_root=str(Path(args.project_root).resolve()), mode=args.mode)
    return _manager(args).initialize(mode=args.mode, interaction_language=args.interaction_language, entry_mode=args.entry_mode)


def command_status(args: argparse.Namespace) -> Dict[str, Any]:
    return _manager(args).state


def _manifest_path(args: argparse.Namespace) -> Path:
    return Path(args.manifest or (Path(args.project_root).resolve() / ".robotics-ar" / "sibling-skills" / "manifest.json"))


def command_validate_siblings(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = SiblingSkillInvocationAdapter(args.robotics_research_root)
    path = _manifest_path(args)
    manifest = _load_json(path)
    adapter.validate_manifest(manifest, require_confirmed=not args.allow_unconfirmed)
    return {"status": "PASS", "manifest_path": path.as_posix(), "manifest_sha256": manifest.get("manifest_sha256")}


def command_prepare_stage(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = SiblingSkillInvocationAdapter(args.robotics_research_root)
    manifest = _load_json(_manifest_path(args))
    request = adapter.prepare_invocation(manifest, args.stage, session_id=_manager(args).session_id, prompt=args.prompt, allowed_files=_split(args.allowed_files), input_sha256=args.input_sha256)
    path = Path(args.project_root).resolve() / ".robotics-ar" / "sibling-skills" / args.stage / "invocation-request.json"
    if args.dry_run:
        return _dry(args, "prepare-stage", request=request, path=path.as_posix())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"status": "PASS", "request_path": path.as_posix(), "request": request}


def command_register_stage_result(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = SiblingSkillInvocationAdapter(args.robotics_research_root)
    manifest = _load_json(_manifest_path(args))
    result = adapter.validate_native_artifact(args.stage, args.artifact, manifest=manifest)
    if result["status"] != "PASS":
        raise CLIError("native artifact failed owner validator")
    receipt = adapter.register_stage_result(args.stage, args.artifact, session_id=_manager(args).session_id, manifest=manifest, validation=result, handoff_status=args.handoff_status)
    path = Path(args.project_root).resolve() / ".robotics-ar" / "sibling-skills" / args.stage / "stage-receipt.json"
    if args.dry_run:
        return _dry(args, "register-stage-result", receipt=receipt, path=path.as_posix())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"status": "PASS", "receipt_path": path.as_posix(), "receipt": receipt}


def command_approve(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    subject = Path(args.subject)
    if args.dry_run:
        return _dry(args, "approve", gate=args.gate, subject_path=subject.as_posix())
    return manager.approve_subject(args.gate, subject, scope=args.scope)


def command_compile_task(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "compile-task", allowed_paths=_split(args.allowed_paths), forbidden_paths=_split(args.forbidden_paths))
    return manager.compile_task(args.instruction, allowed_paths=_split(args.allowed_paths), forbidden_paths=_split(args.forbidden_paths), stop_conditions=_split(args.stop_conditions))


def command_approve_task(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "approve-task", approval=args.approval)
    task_path = manager.state.get("task_path")
    approval = manager.consume_approval(
        args.approval,
        expected_gate="TASK",
        expected_subject_path=task_path if task_path else None,
    )
    if manager.state["state"] == "AWAITING_TASK_APPROVAL":
        manager.transition("IMPLEMENTING", "TASK_APPROVED", {"approval_id": approval["approval_id"]})
    return {"status": "PASS", "approval": approval, "state": manager.state}


def command_validate_environment(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = EnvironmentAdapter.from_file(args.environment_manifest)
    if args.dry_run:
        return _dry(args, "validate-environment", environment_id=adapter.manifest.get("id"))
    takeover_mode = False
    manager = None
    try:
        manager = _manager(args)
        takeover_mode = manager.state.get("entry_mode") == "MIDSTREAM_TAKEOVER"
    except SessionError:
        takeover_mode = False
    path = Path(args.project_root).resolve() / ".robotics-ar" / "environment" / "validation-receipt.json"
    try:
        receipt = adapter.verify_takeover() if takeover_mode else adapter.verify_online()
    except Exception as exc:
        write_structured(path, {"status": "FAILED", "error_type": type(exc).__name__, "verification_completed": False})
        raise CLIError(f"environment verification failed; receipt: {path}") from exc
    write_structured(path, receipt)
    if receipt.get("status") != "ONLINE_VERIFIED":
        if manager is not None and manager.state.get("state") == "TAKEOVER_ENVIRONMENT_VALIDATION":
            TakeoverManager(manager).mark_environment(receipt)
        raise CLIError(f"environment is not ONLINE_VERIFIED; receipt: {path}")
    if manager is not None and takeover_mode and manager.state.get("state") == "TAKEOVER_ENVIRONMENT_VALIDATION":
        state = TakeoverManager(manager).mark_environment(receipt)
        path = manager.paths.takeover / "environment-receipt.yaml"
        return {"status": "PASS", "receipt_path": path.as_posix(), "receipt": receipt, "state": state}
    path = Path(args.project_root).resolve() / ".robotics-ar" / "environment" / "validation-receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_structured(path, receipt)
    return {"status": "PASS", "receipt_path": path.as_posix(), "receipt": receipt}


def command_enable_execution(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    receipt = _load_json(args.receipt)
    if receipt.get("status") != "ONLINE_VERIFIED":
        raise CLIError("ONLINE_VERIFIED receipt required")
    if args.dry_run:
        return _dry(args, "enable-execution", fingerprint=receipt.get("fingerprint"))
    state = manager.enable_execution(receipt, receipt_path=args.receipt)
    return {"status": "PASS", "state": state, "environment_fingerprint": receipt["fingerprint"]}


def command_run_batch(args: argparse.Namespace) -> Dict[str, Any]:
    adapter = EnvironmentAdapter.from_file(args.environment_manifest)
    manager = _manager(args)
    receipt = _load_json(args.receipt)
    request = _load_json(args.request) if args.request else {"batch_id": args.batch_id}
    if args.dry_run:
        return _dry(args, "run-batch", batch_id=args.batch_id)
    if adapter.manifest.get("kind") == "real_robot":
        raise CLIError("use the established one-shot real-robot trial path; this batch entry supports nonphysical environments only")
    registry, execution = _start_bound_execution(args, manager, "run-batch", request)
    try:
        result = adapter.run_batch(manager.state["mode"], receipt, request=request)
    except Exception as exc:
        registry.finish(args.execution_id, args.lease_token, {"execution_id": args.execution_id, "status": "FAIL", "error_type": type(exc).__name__})
        raise
    registry.finish(args.execution_id, args.lease_token, {"execution_id": args.execution_id, "status": "PASS", "result": result})
    return {"status": "PASS", "batch_id": args.batch_id, "result": result}


def command_pause(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "pause", reason=args.reason)
    return _manager(args).pause(args.reason)


def command_resume(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "resume")
    return _manager(args).resume()


def command_report(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = manager.paths.root / "report.md"
    if args.dry_run:
        return _dry(args, "report", path=path.as_posix())
    if manager.state.get("entry_mode") == "MIDSTREAM_TAKEOVER":
        write_current_report(manager, context={"decisions_required": _split(args.actions), "recommended_next_action": args.summary}, reason=args.reason)
    else:
        write_report(path, title="Robotics-AR report", state=manager.state["state"], summary=args.summary, actions=_split(args.actions))
    return {"status": "PASS", "report_path": path.as_posix()}


def command_handoff(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = manager.paths.root / "handoff.md"
    if args.dry_run:
        return _dry(args, "handoff", path=path.as_posix())
    if manager.state.get("entry_mode") == "MIDSTREAM_TAKEOVER":
        write_current_handoff(manager, reason=args.reason)
    else:
        write_handoff(path, state=manager.state["state"], session_id=manager.session_id, reason=args.reason)
    return {"status": "PASS", "handoff_path": path.as_posix()}


def command_reconstruct(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "reconstruct-state")
    return _manager(args).reconstruct_state(persist=True)


def command_takeover_init(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "takeover-init", entry_mode="MIDSTREAM_TAKEOVER")
    return TakeoverManager(_manager(args)).initialize()


def command_takeover_status(args: argparse.Namespace) -> Dict[str, Any]:
    return TakeoverManager(_manager(args)).status()


def command_takeover_record_intake(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    values = _load_structured(args.input) if args.input else {
        "project_id": args.project_id,
        "project_path": args.project_path or str(Path(args.project_root).resolve()),
        "project_core": {},
        "current_goal": args.current_goal,
        "current_bottleneck": args.current_bottleneck,
        "environment": {},
        "allowed_directions": _split(args.allowed_directions),
        "forbidden_changes": _split(args.forbidden_changes),
        "budget": {"max_trials": args.max_trials, "max_wall_time_hours": args.max_wall_time_hours},
        "pause_conditions": _split(args.pause_conditions),
        "user_asserted": [], "repository_observed": [], "agent_inferred": [], "unresolved": [],
    }
    if args.dry_run:
        return _dry(args, "takeover-record-intake", project_id=values.get("project_id"))
    return TakeoverManager(manager).record_intake(values, user_statement=args.instruction)


def command_takeover_audit(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "takeover-audit", project_root=str(Path(args.project_root).resolve()))
    result = audit_project(args.project_root, output_dir=args.output, max_files=args.audit_max_files,
                           max_bytes=args.audit_max_bytes, max_seconds=args.audit_max_seconds,
                           include=_split(args.audit_include), exclude=_split(args.audit_exclude))
    if manager.state.get("state") == "TAKEOVER_AUDITING":
        TakeoverManager(manager).record_audit(result["receipt"])
    return {"status": result["status"], "output_dir": result["output_dir"],
            "receipt_sha256": result["receipt"]["receipt_sha256"], "coverage": result["receipt"]["coverage"]}


def command_takeover_import_history(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    sources = _split(args.sources)
    if args.dry_run:
        return _dry(args, "takeover-import-history", sources=sources)
    result = reconstruct_history(args.project_root, sources=sources or None, output_dir=args.output)
    if manager.state.get("state") == "TAKEOVER_HISTORY_RECONSTRUCTION":
        TakeoverManager(manager).mark_history_reconstructed(receipt=result["receipt"])
    return result


def command_takeover_compile_core(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    values = _load_structured(args.input) if args.input else {
        "project_id": args.project_id,
        "research_problem": args.research_problem,
        "core_method": args.core_method,
        "frozen_invariants": _split(args.frozen_invariants),
        "modifiable_components": _split(args.modifiable_components),
        "forbidden_pivots": _split(args.forbidden_pivots),
        "current_bottleneck": args.current_bottleneck,
        "current_batch_goal": args.current_batch_goal,
        "success_criteria": {"primary": args.primary_metric},
    }
    if args.dry_run:
        return _dry(args, "takeover-compile-core", project_id=values.get("project_id"))
    core = TakeoverManager(manager).compile_core(values)
    return {"status": "PASS", "project_core_path": (manager.paths.takeover / "project-core.yaml").as_posix(), "project_core": core, "state": manager.state}


def command_takeover_approve_core(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    core_path = Path(args.core or manager.paths.takeover / "project-core.yaml")
    if args.dry_run:
        return _dry(args, "takeover-approve-core", core_path=core_path.as_posix())
    approved = TakeoverManager(manager).approve_core(args.approval, core_path=core_path)
    return {"status": "PASS", "core": approved, "state": manager.state}


def command_baseline_list_candidates(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve()
    candidates = []
    for path in (root / ".robotics-ar", root / "agent", root).glob("**/*"):
        if path.is_file() and any(token in path.name.lower() for token in ("baseline", "config", "handoff", "report")):
            candidates.append(path.as_posix())
    candidates = sorted(set(candidates))
    if len(candidates) > 1:
        target = root / ".robotics-ar" / "takeover" / "baseline" / "baseline-candidates.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Baseline candidates\n\n" + "\n".join(f"- `{item}`" for item in candidates) + "\n\nUser selection is required before reproduction.\n", encoding="utf-8")
    return {"status": "PASS", "candidates": candidates, "requires_user_selection": len(candidates) > 1}


def command_baseline_compile(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    values = _load_structured(args.input) if args.input else {"baseline_id": args.baseline_id, "repetitions": args.repetitions, "expected_metrics": {}}
    core_path = Path(args.core) if args.core else Path(str(manager.state.get("project_core_path", manager.paths.takeover / "project-core.yaml")))
    core = load_project_core(core_path) if core_path.exists() else None
    receipt_path = Path(args.receipt) if args.receipt else Path(str(manager.state.get("environment_receipt_path", manager.paths.takeover / "environment-receipt.yaml")))
    environment_receipt = _load_structured(receipt_path) if receipt_path.exists() else None
    if args.dry_run:
        return _dry(args, "baseline-compile", baseline_id=values.get("baseline_id"))
    spec = compile_baseline_spec(values, project_core=core, environment_receipt=environment_receipt)
    path = manager.paths.takeover_baseline / "baseline-spec.yaml"
    write_structured(path, spec)
    return {"status": "PASS", "baseline_path": path.as_posix(), "baseline": spec}


def command_baseline_select(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = Path(args.baseline or manager.paths.takeover_baseline / "baseline-spec.yaml")
    if args.dry_run:
        return _dry(args, "baseline-select", baseline_path=str(path))
    spec = _load_structured(path)
    if not args.reason:
        raise CLIError("baseline-select requires --reason")
    from robotics_ar_core.canonical import sha256_obj

    selection = {"baseline_id": spec["baseline_id"], "config_sha256": sha256_obj(spec), "reason": args.reason}
    if args.approval:
        return {"status": "PASS", "state": TakeoverManager(manager).amend_baseline_selection(selection, path, args.approval)}
    return {"status": "PASS", "state": TakeoverManager(manager).begin_baseline(selection)}


def command_baseline_run(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    spec_path = Path(args.baseline or manager.paths.takeover_baseline / "baseline-spec.yaml")
    if args.dry_run:
        return _dry(args, "baseline-run", baseline_path=spec_path.as_posix())
    if manager.state.get("entry_mode") != "NEW_RESEARCH" and manager.state.get("state") not in {"TAKEOVER_BASELINE_REPRODUCTION", "TAKEOVER_BASELINE_RECOVERY"}:
        raise CLIError("baseline-run requires baseline-select first")
    selection_path = manager.paths.takeover_baseline / "baseline-selection.json"
    if not selection_path.exists():
        raise CLIError("baseline selection binding missing")
    from robotics_ar_core.canonical import sha256_obj

    if _load_structured(selection_path)["config_sha256"] != sha256_obj(_load_structured(spec_path)):
        raise CLIError("selected baseline configuration changed")
    adapter = EnvironmentAdapter.from_file(args.environment_manifest)
    if adapter.manifest.get("kind") == "real_robot":
        raise CLIError("baseline-run cannot bypass the one-shot real-robot trial gate")
    registry, execution = _start_bound_execution(args, manager, "baseline-run", _load_structured(spec_path))
    try:
        receipt = reproduce_baseline(_load_structured(spec_path), adapter, output_dir=manager.paths.takeover_baseline, user_approved_variance=args.allow_variance)
    except Exception as exc:
        registry.finish(args.execution_id, args.lease_token, {"execution_id": args.execution_id, "status": "FAIL", "error_type": type(exc).__name__})
        raise
    registry.finish(args.execution_id, args.lease_token, {"execution_id": args.execution_id, "status": "PASS" if receipt.get("reproduction_status", receipt.get("status")) in {"REPRODUCED", "REPRODUCED_WITH_VARIANCE", "PARTIALLY_REPRODUCED"} else "FAIL", "result": receipt})
    if manager.state.get("state") in {"TAKEOVER_BASELINE_REPRODUCTION", "TAKEOVER_BASELINE_RECOVERY"}:
        TakeoverManager(manager).baseline_result(receipt)
    return receipt


def command_baseline_recover(args: argparse.Namespace) -> Dict[str, Any]:
    """Record bounded recovery diagnostics without changing algorithm code."""

    manager = _manager(args)
    spec_path = Path(args.baseline or manager.paths.takeover_baseline / "baseline-spec.yaml")
    if args.dry_run:
        return _dry(args, "baseline-recover", baseline_path=spec_path.as_posix())
    spec = _load_structured(spec_path)
    diagnostics = _split(args.diagnostics)
    if not diagnostics:
        raise CLIError("baseline recovery requires explicit diagnostics")
    receipt = recover_baseline(spec, diagnostics=diagnostics, output_dir=manager.paths.takeover_baseline)
    if manager.state.get("state") != "TAKEOVER_BASELINE_RECOVERY":
        raise CLIError("baseline recovery is only allowed in TAKEOVER_BASELINE_RECOVERY")
    return receipt


def command_baseline_approve(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = Path(args.baseline or manager.paths.takeover_baseline / "baseline-receipt.json")
    if args.dry_run:
        return _dry(args, "baseline-approve", baseline_path=path.as_posix())
    receipt = _load_structured(path)
    if receipt.get("reproduction_status", receipt.get("status")) not in {"REPRODUCED", "REPRODUCED_WITH_VARIANCE", "PARTIALLY_REPRODUCED"}:
        raise CLIError("only a reproduced baseline can be approved")
    if manager.state.get("state") != "AWAITING_TAKEOVER_APPROVAL":
        raise CLIError("baseline approval requires AWAITING_TAKEOVER_APPROVAL")
    approval = manager.consume_approval(
        args.approval,
        expected_gate=("BASELINE", "EXPERIMENT"),
        expected_subject_path=path,
    )
    if approval.get("gate") not in {"BASELINE", "EXPERIMENT"}:
        raise CLIError("approval gate is not BASELINE")
    approved = TakeoverManager(manager).approve_baseline(str(approval["approval_id"]))
    return {"status": "PASS", "receipt": approved, "state": manager.state}


def command_contract_compile(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    values = _load_structured(args.input) if args.input else {"contract_id": args.contract_id, "current_bottleneck": args.current_bottleneck, "primary_hypothesis": {"statement": args.primary_hypothesis}, "primary_objective": {"metric": args.primary_metric, "direction": args.direction}, "allowed_search_space": {"tier_0_parameters": _split(args.allowed_directions)}, "budget": {"max_trials": args.max_trials, "max_parallel_jobs": args.max_parallel_jobs}, "stop_conditions": _split(args.stop_conditions), "escalation_conditions": _split(args.escalation_conditions)}
    state = manager.state
    if state.get("entry_mode") == "MIDSTREAM_TAKEOVER":
        if state.get("state") != "TRIAL_CONTRACT_COMPILATION":
            raise CLIError("takeover contract compilation requires TRIAL_CONTRACT_COMPILATION")
        if state.get("project_core_approved") is not True or state.get("baseline_approved") is not True:
            raise CLIError("approved Project Core and baseline are required before compiling a Trial Contract")
        values = dict(values)
        core_path = Path(str(state.get("project_core_path", manager.paths.takeover / "project-core.yaml")))
        baseline_path = Path(str(state.get("baseline_receipt_path", manager.paths.takeover_baseline / "baseline-receipt.json")))
        environment_path = Path(str(state.get("environment_receipt_path", manager.paths.takeover / "environment-receipt.yaml")))
        if not core_path.is_file() or not baseline_path.is_file() or not environment_path.is_file():
            raise CLIError("approved Project Core, baseline, and environment receipt artifacts are required")
        core = load_project_core(core_path)
        assert_project_core_approved(core)
        baseline_receipt = _load_structured(baseline_path)
        try:
            assert_baseline_usable(baseline_receipt, allow_variance=True)
            validate_environment_receipt(_load_structured(environment_path), require_online=True)
        except (BaselineError, EnvironmentError) as exc:
            raise CLIError(str(exc)) from exc
        environment_receipt = _load_structured(environment_path)
        if core_hash(core) != state.get("project_core_sha256") or baseline_receipt.get("receipt_sha256") != state.get("baseline_receipt_sha256") or environment_receipt.get("receipt_sha256") != state.get("environment_receipt_sha256"):
            raise CLIError("upstream artifact hash drift prevents contract compilation")
        values.update({
            "project_core_sha256": core["project_core_sha256"],
            "baseline_receipt_sha256": baseline_receipt["receipt_sha256"],
            "environment_receipt_sha256": environment_receipt["receipt_sha256"],
            "baseline_reproduction_status": baseline_receipt.get("reproduction_status"),
            "baseline_user_approved_variance": bool(baseline_receipt.get("user_approved_variance", False)),
            "project_core_approval_id": core.get("approval_id", ""),
            "baseline_approval_id": baseline_receipt.get("approval_id", ""),
            "project_core_path": core_path.resolve().as_posix(),
            "baseline_receipt_path": baseline_path.resolve().as_posix(),
            "environment_receipt_path": environment_path.resolve().as_posix(),
            "upstream_approval_binding_required": True,
        })
        values["project_core_approved"] = True
        values["baseline_approved"] = True
    if args.dry_run:
        return _dry(args, "contract-compile", contract_id=values.get("contract_id"))
    contract = compile_trial_contract(values, project_core_sha256=args.project_core_sha256 or str(values.get("project_core_sha256", "")), baseline_receipt_sha256=args.baseline_receipt_sha256 or str(values.get("baseline_receipt_sha256", "")), environment_receipt_sha256=args.environment_receipt_sha256 or str(values.get("environment_receipt_sha256", "")))
    path = manager.paths.takeover_contracts / f"{contract['contract_id']}.yaml"
    write_structured(path, contract)
    updated = dict(manager.state)
    updated["contract_sha256"] = contract["contract_sha256"]
    updated["contract_path"] = path.as_posix()
    from robotics_ar_core.atomic_io import atomic_write_json

    atomic_write_json(manager.paths.state, updated)
    manager._state = updated
    if manager.state["state"] == "TRIAL_CONTRACT_COMPILATION":
        manager.transition("AWAITING_TRIAL_CONTRACT_APPROVAL", "TRIAL_CONTRACT_COMPILED", {"contract_sha256": contract["contract_sha256"]})
    return {"status": "PASS", "contract_path": path.as_posix(), "contract": contract, "state": manager.state}


def command_contract_approve(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = Path(args.contract or manager.paths.takeover_contracts / "batch-001.yaml")
    if args.dry_run:
        return _dry(args, "contract-approve", contract_path=path.as_posix())
    result = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals).approve(path, args.approval)
    from robotics_ar_core.atomic_io import atomic_write_json

    updated = dict(manager.state)
    updated.update({"contract_path": path.resolve().as_posix(), "contract_sha256": result["contract_sha256"], "contract_approved": True})
    atomic_write_json(manager.paths.state, updated)
    manager._state = updated
    if manager.state["state"] == "AWAITING_TRIAL_CONTRACT_APPROVAL":
        manager.transition("TRIAL_BATCH_READY", "TRIAL_CONTRACT_APPROVED", {"contract_sha256": result["contract_sha256"]})
    return {"status": "PASS", "contract": result, "state": manager.state}


def command_contract_amend(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = Path(args.contract or manager.paths.takeover_contracts / "batch-001.yaml")
    if args.dry_run:
        return _dry(args, "contract-amend", contract_path=path.as_posix())
    contracts = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals)
    amendment = contracts.amend(path, user_instruction=args.instruction, changes=_load_structured(args.input) if args.input else {"instruction": args.instruction})
    amendment_path = manager.paths.takeover_contracts / f"{amendment['amendment_id']}.yaml"
    amended = contracts.compile_amended(path, amendment_path)
    amended_path = contracts.save(amended)
    from robotics_ar_core.atomic_io import atomic_write_json

    updated = dict(manager.state)
    updated.update({"contract_path": amended_path.as_posix(), "contract_sha256": amended["contract_sha256"], "contract_approved": False})
    atomic_write_json(manager.paths.state, updated)
    manager._state = updated
    if manager.state.get("state") in {"TRIAL_BATCH_READY", "TRIAL_PLANNING", "TRIAL_IMPLEMENTING", "TRIAL_TESTING", "TRIAL_DEBUGGING", "TRIAL_RUNNING", "TRIAL_ANALYZING", "TRIAL_EXPERT_REVIEW", "TRIAL_DECIDING", "BATCH_CHECKPOINT"}:
        manager.transition("AWAITING_USER_DIRECTION", "CONTRACT_AMENDED", {"amendment_sha256": amendment["amendment_sha256"], "contract_sha256": amended["contract_sha256"]})
    return {"status": "PASS", "amendment": amendment, "contract_path": amended_path.as_posix(), "contract": amended, "state": manager.state}


def command_trial_propose(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    values = _load_structured(args.input) if args.input else {"trial_id": args.trial_id, "parent_contract": args.contract_sha256 or args.contract or "", "hypothesis": {"statement": args.hypothesis, "rationale": args.rationale, "expected_observation": args.expected_observation, "falsification_condition": args.falsification_condition}, "uncertainty_target": args.uncertainty_target, "change": {"tier": args.tier, "components": _split(args.components), "minimal_patch": True}, "experiment": {}, "metrics": {}, "resource_estimate": {}, "rollback": {}}
    if args.dry_run:
        return _dry(args, "trial-propose", trial_id=values.get("trial_id"))
    proposal = build_proposal(values)
    queue = TrialQueue(manager.paths.trial_queue)
    queued = queue.add(proposal, retry_justification=args.retry_justification)
    return {"status": "PASS", "proposal": queued}


def command_trial_register_agent_receipt(args: argparse.Namespace) -> Dict[str, Any]:
    receipt = _load_structured(args.receipt)
    try:
        trial_id = validate_trial_id(args.trial_id)
    except TrialQueueError as exc:
        raise CLIError(str(exc)) from exc
    if args.dry_run:
        return _dry(args, "trial-register-agent-receipt", role=receipt.get("role"))
    validate_agent_receipt(receipt, expected_task_id=args.trial_id if args.trial_id else None)
    target = Path(args.output or Path(args.project_root).resolve() / ".robotics-ar" / "experiments" / trial_id / f"{str(receipt.get('role', 'agent')).lower().replace(' ', '-')}-receipt.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return {"status": "PASS", "receipt_path": target.as_posix()}


def command_trial_run(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "trial-run", trial_id=args.trial_id)
    if not args.environment_manifest:
        raise CLIError("trial-run requires --environment-manifest")
    proposal = _load_structured(args.proposal or (manager.paths.trial_queue / "active" / f"{args.trial_id}.yaml"))
    try:
        validate_proposal(proposal)
    except TrialQueueError as exc:
        raise CLIError(str(exc)) from exc
    environment_receipt = None
    contract = None
    if manager.state.get("entry_mode") == "MIDSTREAM_TAKEOVER":
        contract_value = getattr(args, "contract", None) or manager.state.get("contract_path")
        if not contract_value:
            raise CLIError("an active approved Trial Contract is required")
        contract_path = Path(str(contract_value)).resolve()
        if not contract_path.is_file():
            raise CLIError("active approved Trial Contract is missing")
        contracts = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals)
        contract = contracts.assert_approved(contract_path, expected_hash=manager.state.get("contract_sha256"))
        receipt_path = Path(args.receipt or str(manager.state.get("environment_receipt_path", manager.paths.takeover / "environment-receipt.yaml")))
        if not receipt_path.exists():
            raise CLIError("an ONLINE_VERIFIED environment receipt is required for takeover trial execution")
        environment_receipt = _load_structured(receipt_path)
        try:
            validate_environment_receipt(environment_receipt, require_online=True)
        except EnvironmentError as exc:
            raise CLIError(str(exc)) from exc
        if environment_receipt.get("receipt_sha256") != contract.get("environment_receipt_sha256"):
            raise CLIError("trial environment receipt is not bound to the active contract")
    adapter = EnvironmentAdapter.from_file(args.environment_manifest)
    if environment_receipt is not None and environment_receipt.get("fingerprint") != adapter.fingerprint():
        raise CLIError("trial environment fingerprint drift")
    if contract is not None:
        used_trials, parallel_jobs = _trial_usage(manager, current_trial_id=str(proposal["trial_id"]))
        try:
            TrialContractManager.check_trial(
                contract,
                proposal,
                used_trials=used_trials,
                parallel_jobs=parallel_jobs,
                environment_receipt_sha256=str(environment_receipt["receipt_sha256"]),
            )
        except TrialContractError as exc:
            raise CLIError(str(exc)) from exc

    target = manager.paths.experiments / str(proposal["trial_id"])
    target.mkdir(parents=True, exist_ok=True)
    write_structured(target / "proposal.yaml", proposal)
    code_receipt = _load_optional_mapping(getattr(args, "code_receipt", None), label="code receipt")
    test_receipt = _load_optional_mapping(getattr(args, "test_receipt", None), label="test receipt")
    result = adapter.run_trial(proposal)
    write_structured(target / "run-manifest.yaml", result)
    run_receipt = dict(result)
    run_receipt.update(
        {
            "schema_version": "robotics-ar-trial-run-receipt.v1",
            "trial_id": proposal["trial_id"],
            "proposal_sha256": proposal.get("proposal_sha256"),
            "created_at": utc_now(),
            "runtime_status": "SINGLE_AGENT_MODE",
            "metric_versions": _metric_versions(proposal),
        }
    )
    if contract is not None:
        run_receipt.update(
            {
                "contract_sha256": contract.get("contract_sha256"),
                "environment_receipt_sha256": environment_receipt.get("receipt_sha256"),
                "environment_fingerprint": environment_receipt.get("fingerprint"),
            }
        )
    if code_receipt is not None:
        run_receipt["code_receipt_sha256"] = code_receipt.get("receipt_sha256")
        if code_receipt.get("code_version") is not None:
            run_receipt["code_version"] = code_receipt.get("code_version")
        if code_receipt.get("configuration_sha256") is not None:
            run_receipt["configuration_sha256"] = code_receipt.get("configuration_sha256")
    if test_receipt is not None:
        run_receipt["test_receipt_sha256"] = test_receipt.get("receipt_sha256")
    run_receipt["receipt_sha256"] = sha256_obj(run_receipt)
    write_structured(target / "run-receipt.json", run_receipt)
    return {"status": "PASS", "run": run_receipt, "run_manifest_path": (target / "run-manifest.yaml").as_posix(), "run_receipt_path": (target / "run-receipt.json").as_posix(), "runtime_status": "SINGLE_AGENT_MODE"}


def command_trial_analyze(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    try:
        trial_id = validate_trial_id(args.trial_id)
    except TrialQueueError as exc:
        raise CLIError(str(exc)) from exc
    if not args.input:
        raise CLIError("trial-analyze requires --input with raw evidence and versioned metrics; it cannot fabricate results from flags")
    values = _load_structured(args.input)
    if args.dry_run:
        return _dry(args, "trial-analyze", trial_id=args.trial_id)
    raw_evidence = values.get("raw_evidence", values.get("raw_paths"))
    proposal = _load_optional_mapping(values.get("proposal"), label="proposal")
    proposal = proposal or _load_optional_mapping(values.get("proposal_path") or getattr(args, "proposal", None), label="proposal")
    contract = _load_optional_mapping(values.get("contract"), label="contract")
    contract_path_value = values.get("contract_path") or getattr(args, "contract", None) or manager.state.get("contract_path")
    if contract is None and contract_path_value:
        contract_path = Path(str(contract_path_value))
        if contract_path.is_file():
            contract = _load_structured(contract_path)
    run = _load_optional_mapping(values.get("run_receipt") or values.get("run"), label="run receipt")
    run_path_value = values.get("run_receipt_path") or values.get("run_path")
    if run is None and run_path_value:
        run = _load_structured(run_path_value)
    if run is None:
        default_run = manager.paths.experiments / trial_id / "run-receipt.json"
        if default_run.is_file():
            run = _load_structured(default_run)
    if proposal is None:
        default_proposal = manager.paths.experiments / trial_id / "proposal.yaml"
        if default_proposal.is_file():
            proposal = _load_structured(default_proposal)
    strict_context = proposal is not None or contract is not None or run is not None
    if strict_context and (proposal is None or contract is None or run is None):
        raise CLIError("strict trial analysis requires proposal, contract, and run receipt bindings")
    if run is not None:
        raw_evidence = raw_evidence or run.get("raw_evidence")
    if not raw_evidence:
        raise CLIError("analysis input must include raw_evidence or raw_paths")
    metrics = values.get("metrics")
    metric_versions = _metric_versions(values)
    if not metric_versions and run is not None and isinstance(run.get("metric_versions"), Mapping):
        metric_versions = {str(key): str(item) for key, item in run["metric_versions"].items() if item not in (None, "")}
    embedded_versions = isinstance(metrics, dict) and any(isinstance(item, dict) and any(key in item for key in ("metric_version", "version", "version_id")) for item in metrics.values())
    if not values.get("metric_receipt") and not metric_versions and not embedded_versions:
        raise CLIError("analysis input must include versioned metrics or metric_receipt")
    if not metric_versions and embedded_versions:
        metric_versions = _metric_versions({"metrics": metrics})

    if strict_context:
        try:
            validate_proposal(proposal or {})
        except TrialQueueError as exc:
            raise CLIError(str(exc)) from exc
        if str((proposal or {}).get("trial_id")) != str(args.trial_id):
            raise CLIError("analysis proposal trial_id does not match --trial-id")
        run_hash = run.get("receipt_sha256")
        expected_run_hash = sha256_obj({key: item for key, item in run.items() if key != "receipt_sha256"})
        if not run_hash or run_hash != expected_run_hash:
            raise CLIError("analysis requires a self-hashed run receipt")
        if run.get("trial_id") != proposal.get("trial_id") or run.get("proposal_sha256") != proposal.get("proposal_sha256") or run.get("contract_sha256") != contract.get("contract_sha256"):
            raise CLIError("run receipt is not bound to the proposal and contract")
        if run.get("status") not in {"PASS", "ONLINE_VERIFIED", "VERIFIED"}:
            raise CLIError("analysis requires a successful run receipt")

    target = manager.paths.experiments / trial_id / "analysis"
    target.mkdir(parents=True, exist_ok=True)
    write_structured(target / "metrics.json", values)
    receipt = {
        "schema_version": "robotics-ar-analysis-receipt.v1",
        "trial_id": args.trial_id,
        "status": "PASS",
        "analysis": values,
        "raw_evidence": raw_evidence,
        "metric_versions": metric_versions,
        "valid": values.get("valid") is True,
        "reproducible": values.get("reproducible") is True,
        "created_at": utc_now(),
    }
    for key in ("metrics", "baseline", "baseline_metrics", "observed", "improved", "uncertainty_reduced", "contradictory", "needs_discriminative_experiment", "manual_operation"):
        if key in values:
            receipt[key] = values[key]
    if strict_context and proposal is not None and contract is not None and run is not None:
        receipt.update(
            {
                "proposal_sha256": proposal.get("proposal_sha256"),
                "contract_sha256": contract.get("contract_sha256"),
                "run_receipt_sha256": run.get("receipt_sha256"),
                "environment_receipt_sha256": run.get("environment_receipt_sha256") or contract.get("environment_receipt_sha256"),
                "environment_fingerprint": run.get("environment_fingerprint"),
            }
        )
    receipt["receipt_sha256"] = __import__("robotics_ar_core.canonical", fromlist=["sha256_obj"]).sha256_obj(receipt)
    write_structured(target / "analysis-receipt.json", receipt)
    return {"status": "PASS", "analysis_receipt": receipt, "analysis_receipt_path": (target / "analysis-receipt.json").as_posix()}


def command_trial_decide(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    try:
        trial_id = validate_trial_id(args.trial_id)
    except TrialQueueError as exc:
        raise CLIError(str(exc)) from exc
    if args.dry_run:
        return _dry(args, "trial-decide", trial_id=args.trial_id)
    proposal = _load_structured(args.proposal)
    contract = _load_structured(args.contract)
    code = _load_structured(args.code_receipt)
    test = _load_structured(args.test_receipt)
    run = _load_structured(args.run_receipt)
    analysis = _load_structured(args.analysis_receipt)
    expert = _load_structured(args.expert_receipt) if args.expert_receipt else None
    decision = TrialDecisionEngine().decide(proposal=proposal, contract=contract, code_receipt=code, test_receipt=test, run_receipt=run, analysis=analysis, expert_consensus=expert, environment_receipt_sha256=str(contract.get("environment_receipt_sha256", "")), environment_fingerprint=str(run.get("environment_fingerprint", "")))
    target = manager.paths.experiments / trial_id
    target.mkdir(parents=True, exist_ok=True)
    write_structured(target / "decision-receipt.json", decision)
    return {"status": "PASS", "decision": decision}


def command_batch_start(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    contract_path = Path(args.contract or manager.paths.takeover_contracts / "batch-001.yaml")
    if args.dry_run:
        return _dry(args, "batch-start", batch_id=args.batch_id)
    contract = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals).assert_approved(contract_path, expected_hash=manager.state.get("contract_sha256") if manager.state.get("contract_path") else None)
    values = _load_structured(args.input) if args.input else {"batch_id": args.batch_id, "contract_sha256": contract.get("contract_sha256"), "max_trials": args.max_trials, "max_wall_time_minutes": args.max_wall_time_minutes, "max_parallel_jobs": args.max_parallel_jobs, "report_every_trials": args.report_every_trials, "stop_on": _split(args.stop_on)}
    batch = compile_batch(values, contract_sha256=contract.get("contract_sha256"))
    receipt = _load_structured(args.receipt)
    controller = BatchController(manager.paths.experiments / str(batch["batch_id"]), mode=manager.state["mode"], manager=manager, contracts_dir=manager.paths.takeover_contracts)
    token = None
    binding: Dict[str, Any] = {}
    if args.real_robot:
        if not args.real_robot_token or not args.real_robot_binding:
            raise CLIError("real-robot batch requires --real-robot-token and --real-robot-binding")
        from robotics_ar_core.real_robot import OneShotRealRobotToken

        token = OneShotRealRobotToken.load(args.real_robot_token)
        binding = _load_structured(args.real_robot_binding)
    checkpoint = controller.start(batch, contract=contract, environment_receipt=receipt, real_robot=args.real_robot, real_robot_token=token, real_robot_binding=binding, approval_dir=manager.paths.approvals)
    return {"status": "PASS", "batch": batch, "checkpoint": checkpoint}


def command_batch_checkpoint(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = Path(args.checkpoint or manager.paths.experiments / args.batch_id / "batch-checkpoint.json")
    if args.dry_run:
        return _dry(args, "batch-checkpoint", path=path.as_posix())
    controller = BatchController.load_checkpoint(path, mode=manager.state["mode"], manager=manager, contracts_dir=manager.paths.takeover_contracts)
    return {"status": "PASS", "checkpoint": controller.checkpoint()}


def command_batch_resume(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = Path(args.checkpoint or manager.paths.experiments / args.batch_id / "batch-checkpoint.json")
    if args.dry_run:
        return _dry(args, "batch-resume", path=path.as_posix())
    contract_path = Path(args.contract or manager.paths.takeover_contracts / "batch-001.yaml")
    contract = TrialContractManager(manager.paths.takeover_contracts, manager.paths.approvals).assert_approved(contract_path, expected_hash=manager.state.get("contract_sha256") if manager.state.get("contract_path") else None)
    receipt = _load_structured(args.receipt)
    controller = BatchController.load_checkpoint(path, mode=manager.state["mode"], manager=manager, contracts_dir=manager.paths.takeover_contracts)
    return {"status": "PASS", "checkpoint": controller.resume(contract=contract, environment_receipt=receipt, approval_dir=manager.paths.approvals)}


def command_batch_stop(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    path = Path(args.checkpoint or manager.paths.experiments / args.batch_id / "batch-checkpoint.json")
    if args.dry_run:
        return _dry(args, "batch-stop", path=path.as_posix())
    controller = BatchController.load_checkpoint(path, mode=manager.state["mode"], manager=manager, contracts_dir=manager.paths.takeover_contracts)
    return {"status": "PASS", "checkpoint": controller.stop(args.reason)}


def command_apply_user_correction(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "apply-user-correction")
    task = compile_correction(manager, args.instruction, objective=args.objective, project_core_ref=args.project_core_ref, allowed_changes=_split(args.allowed_changes), forbidden_changes=_split(args.forbidden_changes), metrics=_split(args.metrics), budget={"max_trials": args.max_trials}, stop_conditions=_split(args.stop_conditions), escalation_conditions=_split(args.escalation_conditions), contract_path=args.contract)
    return {"status": "PASS", "task": task, "state": manager.state}


def command_confirm_user_correction(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "confirm-user-correction")
    return confirm_and_resume(manager, task_approval_path=args.task_approval or args.approval, contract_path=args.contract, contract_approval_path=args.contract_approval)


def command_best_known(args: argparse.Namespace) -> Dict[str, Any]:
    manager = _manager(args)
    state = BestKnownState(manager.paths.best_known)
    if args.dry_run:
        return _dry(args, "best-known")
    if args.candidate:
        candidate = _load_structured(args.candidate)
        return {"status": "PASS", "best_known": state.promote(candidate, stable=args.stable)}
    return {"status": "PASS", "best_known": state.current()}


def command_migrate_v2(args: argparse.Namespace) -> Dict[str, Any]:
    if args.dry_run:
        return _dry(args, "migrate-v2", project_root=str(Path(args.project_root).resolve()))
    return migrate_project(args.project_root)


def command_doctor(args):
    from robotics_ar_core.migration import doctor_project
    return doctor_project(args.project_root)


def command_snapshot_repositories(args):
    from robotics_ar_core.repository_ledger import snapshot
    manager = _manager(args)
    if args.dry_run:
        return _dry(args, "snapshot-repositories")
    receipt = snapshot(_load_structured(args.input))
    path = manager.paths.root / "repository-ledger.json"
    write_structured(path, receipt)
    return {"status": "PASS", "receipt_path": str(path), "sha256": receipt["sha256"]}


def command_reconcile(args):
    if args.dry_run:
        return _dry(args, "takeover-reconcile")
    return {"status": "PASS", "state": TakeoverManager(_manager(args)).complete_idea_reconciliation(_load_structured(args.input))}


def command_external_execution(args):
    from robotics_ar_core.execution_registry import ExecutionRegistry
    if args.dry_run:
        return _dry(args, args.command)
    registry = ExecutionRegistry(_manager(args))
    if args.command == "reserve-execution":
        row = registry.reserve(args.input, args.approval)
    elif args.command == "reconcile-execution":
        row = registry.reconcile(args.input, args.approval)
    elif args.command == "start-execution":
        row = registry.start(args.execution_id, args.lease_token)
    elif args.command == "import-execution":
        row = registry.import_history(args.execution_id, _load_structured(args.input))
    else:
        row = registry.finish(args.execution_id, args.lease_token, _load_structured(args.input))
    return {"status": "PASS", "execution": row}


def _start_bound_execution(args, manager, operation, value):
    from robotics_ar_core.execution_registry import ExecutionRegistry
    from robotics_ar_core.canonical import sha256_obj
    if not args.execution_id or not args.lease_token:
        raise CLIError("reserve-execution and a lease token are required before launch")
    registry = ExecutionRegistry(manager)
    row = registry.read()["executions"].get(args.execution_id, {})
    spec = row.get("spec", {})
    if spec.get("operation") != operation or spec.get("input_sha256") != sha256_obj(value):
        raise CLIError("execution operation/input differs from approved specification")
    if spec.get("environment_fingerprint") != manager.state.get("environment_fingerprint"):
        raise CLIError("execution environment binding changed")
    return registry, registry.start(args.execution_id, args.lease_token)


def command_baseline_bootstrap_new(args):
    manager = _manager(args)
    if manager.state.get("entry_mode") != "NEW_RESEARCH":
        raise CLIError("baseline-bootstrap-new requires NEW_RESEARCH")
    result = command_baseline_compile(args)
    if not args.dry_run:
        from robotics_ar_core.canonical import sha256_obj
        if not args.reason:
            raise CLIError("baseline-bootstrap-new requires --reason")
        write_structured(manager.paths.takeover_baseline / "baseline-selection.json",
                         {"baseline_id": result["baseline"]["baseline_id"], "config_sha256": sha256_obj(result["baseline"]), "reason": args.reason})
    return result


COMMANDS = {
    "reserve-execution": command_external_execution,
    "reconcile-execution": command_external_execution,
    "baseline-bootstrap-new": command_baseline_bootstrap_new,
    "start-execution": command_external_execution,
    "register-external-execution": command_external_execution,
    "import-execution": command_external_execution,
    "doctor": command_doctor,
    "snapshot-repositories": command_snapshot_repositories,
    "takeover-reconcile": command_reconcile,
    "discover": command_discover,
    "init": command_init,
    "status": command_status,
    "validate-siblings": command_validate_siblings,
    "prepare-stage": command_prepare_stage,
    "register-stage-result": command_register_stage_result,
    "approve": command_approve,
    "compile-task": command_compile_task,
    "approve-task": command_approve_task,
    "validate-environment": command_validate_environment,
    "enable-execution": command_enable_execution,
    "run-batch": command_run_batch,
    "pause": command_pause,
    "resume": command_resume,
    "report": command_report,
    "handoff": command_handoff,
    "reconstruct-state": command_reconstruct,
    "takeover-init": command_takeover_init,
    "takeover-status": command_takeover_status,
    "takeover-record-intake": command_takeover_record_intake,
    "takeover-audit": command_takeover_audit,
    "takeover-import-history": command_takeover_import_history,
    "takeover-compile-core": command_takeover_compile_core,
    "takeover-approve-core": command_takeover_approve_core,
    "baseline-list-candidates": command_baseline_list_candidates,
    "baseline-compile": command_baseline_compile,
    "baseline-select": command_baseline_select,
    "baseline-run": command_baseline_run,
    "baseline-recover": command_baseline_recover,
    "baseline-approve": command_baseline_approve,
    "contract-compile": command_contract_compile,
    "contract-approve": command_contract_approve,
    "contract-amend": command_contract_amend,
    "trial-propose": command_trial_propose,
    "trial-register-agent-receipt": command_trial_register_agent_receipt,
    "trial-run": command_trial_run,
    "trial-analyze": command_trial_analyze,
    "trial-decide": command_trial_decide,
    "batch-start": command_batch_start,
    "batch-checkpoint": command_batch_checkpoint,
    "batch-resume": command_batch_resume,
    "batch-stop": command_batch_stop,
    "apply-user-correction": command_apply_user_correction,
    "confirm-user-correction": command_confirm_user_correction,
    "best-known": command_best_known,
    "migrate-v2": command_migrate_v2,
}


def build_parser() -> argparse.ArgumentParser:
    """创建 CLI parser。 / Build the CLI parser."""

    parser = argparse.ArgumentParser(prog="robotics_ar.py")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--robotics-research-root", default=".")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=["PLANNING_ONLY", "EXECUTION_ENABLED"], default="PLANNING_ONLY")
    parser.add_argument("--entry-mode", choices=["NEW_RESEARCH", "MIDSTREAM_TAKEOVER"], default="NEW_RESEARCH")
    parser.add_argument("--interaction-language", default="zh")
    parser.add_argument("--manifest")
    parser.add_argument("--allow-unconfirmed", action="store_true")
    parser.add_argument("--stage", choices=["idea", "experiment", "writing", "review"])
    parser.add_argument("--prompt", default="")
    parser.add_argument("--allowed-files", default="README.md")
    parser.add_argument("--input-sha256", default="")
    parser.add_argument("--artifact")
    parser.add_argument("--handoff-status", choices=["READY", "REVISE", "BLOCKED", "STOPPED"], default="READY")
    parser.add_argument("--gate", choices=["IDEA", "EXPERIMENT", "TASK", "EVIDENCE", "WRITING", "REVIEW_ROUTE", "REAL_ROBOT", "TAKEOVER_CORE", "BASELINE", "TRIAL_CONTRACT", "TRIAL_BATCH"])
    parser.add_argument("--subject")
    parser.add_argument("--scope", choices=["single-use", "persistent-until-drift"], default="single-use")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--allowed-paths", default="src")
    parser.add_argument("--forbidden-paths", default="raw,research,claims")
    parser.add_argument("--stop-conditions", default="budget,critical-failure")
    parser.add_argument("--approval")
    parser.add_argument("--task-approval")
    parser.add_argument("--contract-approval")
    parser.add_argument("--environment-manifest")
    parser.add_argument("--receipt")
    parser.add_argument("--request")
    parser.add_argument("--batch-id", default="batch-001")
    parser.add_argument("--reason", default="user-request")
    parser.add_argument("--summary", default="No summary supplied.")
    parser.add_argument("--actions", default="resume after validation")
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--sources", default="")
    parser.add_argument("--project-id", default="project")
    parser.add_argument("--project-path", default="")
    parser.add_argument("--current-goal", default="")
    parser.add_argument("--current-bottleneck", default="")
    parser.add_argument("--allowed-directions", default="")
    parser.add_argument("--forbidden-changes", default="")
    parser.add_argument("--pause-conditions", default="core-change-required,budget-exhausted")
    parser.add_argument("--max-trials", type=int, default=30)
    parser.add_argument("--max-wall-time-hours", type=float, default=8.0)
    parser.add_argument("--research-problem", default="")
    parser.add_argument("--core-method", default="")
    parser.add_argument("--frozen-invariants", default="")
    parser.add_argument("--modifiable-components", default="")
    parser.add_argument("--forbidden-pivots", default="")
    parser.add_argument("--current-batch-goal", default="")
    parser.add_argument("--primary-metric", default="primary")
    parser.add_argument("--core")
    parser.add_argument("--baseline")
    parser.add_argument("--baseline-id", default="baseline-current")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--allow-variance", action="store_true")
    parser.add_argument("--contract", dest="contract")
    parser.add_argument("--contract-id", default="batch-001")
    parser.add_argument("--contract-sha256", default="")
    parser.add_argument("--primary-hypothesis", default="")
    parser.add_argument("--direction", choices=["maximize", "minimize"], default="maximize")
    parser.add_argument("--escalation-conditions", default="core-change-required,tier-3-pivot")
    parser.add_argument("--max-parallel-jobs", type=int, default=1)
    parser.add_argument("--project-core-sha256", default="")
    parser.add_argument("--baseline-receipt-sha256", default="")
    parser.add_argument("--environment-receipt-sha256", default="")
    parser.add_argument("--trial-id", default="trial-0001")
    parser.add_argument("--proposal")
    parser.add_argument("--hypothesis", default="")
    parser.add_argument("--rationale", default="")
    parser.add_argument("--expected-observation", default="")
    parser.add_argument("--falsification-condition", default="")
    parser.add_argument("--uncertainty-target", default="")
    parser.add_argument("--components", default="")
    parser.add_argument("--tier", type=int, default=0)
    parser.add_argument("--retry-justification", default="")
    parser.add_argument("--code-receipt")
    parser.add_argument("--test-receipt")
    parser.add_argument("--run-receipt")
    parser.add_argument("--analysis-receipt")
    parser.add_argument("--expert-receipt")
    parser.add_argument("--analysis-status", default="PASS")
    parser.add_argument("--improved", action="store_true")
    parser.add_argument("--uncertainty-reduced", action="store_true")
    parser.add_argument("--report-every-trials", type=int, default=2)
    parser.add_argument("--max-wall-time-minutes", type=int, default=480)
    parser.add_argument("--stop-on", default="budget_exhausted,core_change_required,critical_block")
    parser.add_argument("--real-robot", action="store_true")
    parser.add_argument("--real-robot-token")
    parser.add_argument("--real-robot-binding")
    parser.add_argument("--checkpoint")
    parser.add_argument("--candidate")
    parser.add_argument("--stable", action="store_true")
    parser.add_argument("--objective", default="")
    parser.add_argument("--project-core-ref", default="")
    parser.add_argument("--allowed-changes", default="")
    parser.add_argument("--metrics", default="")
    parser.add_argument("--diagnostics", default="")
    parser.add_argument("--audit-max-files", type=int, default=1000)
    parser.add_argument("--audit-max-bytes", type=int, default=8_000_000)
    parser.add_argument("--audit-max-seconds", type=float, default=5.0)
    parser.add_argument("--audit-include", default="")
    parser.add_argument("--audit-exclude", default="")
    parser.add_argument("--invocation-receipt", help="optional local receipt path; no prompts or command arguments recorded")
    parser.add_argument("--execution-id")
    parser.add_argument("--lease-token")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """运行 CLI，只输出一个 JSON 对象。 / Run the CLI and emit one JSON object."""
    args = build_parser().parse_args(argv)
    try:
        from contextlib import nullcontext
        from robotics_ar_core.transaction import writer_lock

        # 长运行不持有会话锁，暂停必须仍可进入；起止登记各自加锁。
        # Long execution releases the session lock so pause can enter; launch/completion lock separately.
        unlocked = args.dry_run or args.command in {"status", "discover", "takeover-status", "validate-siblings", "doctor",
                                                   "run-batch", "baseline-run", "trial-run", "validate-environment"}
        with nullcontext() if unlocked else writer_lock(Path(args.project_root) / ".robotics-ar"):
            result = COMMANDS[args.command](args)
    except (CLIError, SessionError, SiblingAdapterError, EnvironmentError, OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        result = {"status": "BLOCKED", "error": str(exc)[:4096]}
    if args.invocation_receipt:
        import uuid
        import hashlib
        from robotics_ar_core.models import utc_now
        version_path = Path(__file__).resolve().parents[3] / "VERSION"
        receipt = {"schema_version": "robotics-skill-invocation.v1",
            "invocation_id": str(uuid.uuid4()), "skill": "robotics-ar", "entrypoint": args.command,
            "result_status": result.get("status", "UNKNOWN"), "coverage": "explicit-cli-only",
            "suite_version": version_path.read_text().strip() if version_path.exists() else "UNKNOWN",
            "entrypoint_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "created_at": utc_now(), "network_telemetry": False}
        try:
            target = Path(args.invocation_receipt)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as handle:
                json.dump(receipt, handle, ensure_ascii=False)
        except OSError as exc:
            result["invocation_receipt_error"] = type(exc).__name__
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 2 if result.get("status") in {"BLOCKED", "FAIL", "PARTIAL", "BLOCKED_BOOTSTRAP"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
