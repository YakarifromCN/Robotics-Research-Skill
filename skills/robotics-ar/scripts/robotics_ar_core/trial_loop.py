"""Bounded trial execution contracts and KEEP/REVERT/INVESTIGATE/ESCALATE."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable, Mapping, Optional

from .atomic_io import atomic_write_json
from .canonical import sha256_obj
from .models import utc_now
from .schema_validation import SchemaValidationError, validate_artifact
from .structured import write_structured
from .trial_contract import TrialContractError, TrialContractManager, validate_contract
from .trial_queue import validate_proposal


class TrialLoopError(RuntimeError):
    """Raised when a trial cannot be evaluated safely."""


DECISIONS = frozenset({"KEEP", "REVERT", "INVESTIGATE", "ESCALATE", "CONTINUE", "COMPLETE"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GOOD_RUN_STATUSES = frozenset({"PASS", "ONLINE_VERIFIED", "VERIFIED"})
_ROLLBACK_OK = frozenset({"PASS", "ROLLED_BACK", "REVERTED", "NOT_REQUESTED"})


def _number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iter_sha256_claims(value: Any):
    """Yield every explicit SHA-256 claim nested in a raw-evidence receipt."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if key_text == "sha256" or key_text.endswith("_sha256"):
                yield key_text, child
            else:
                yield from _iter_sha256_claims(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_sha256_claims(child)


def raw_evidence_complete(receipt: Mapping[str, Any]) -> bool:
    """Require non-empty raw evidence with complete, valid hash receipts."""

    raw = receipt.get("raw_evidence", receipt.get("raw_paths"))
    if not raw:
        return False
    claims = list(_iter_sha256_claims(raw))
    return bool(claims) and all(isinstance(value, str) and _SHA256.fullmatch(value) for _, value in claims)


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    return sha256_obj({key: value for key, value in receipt.items() if key != "receipt_sha256"})


def _has_hash(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _first_present(receipt: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = receipt.get(key)
        if value not in (None, ""):
            return value
    return None


def _binding_errors(
    *,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
    code_receipt: Mapping[str, Any],
    test_receipt: Mapping[str, Any],
    run_receipt: Mapping[str, Any],
    analysis: Mapping[str, Any],
    environment_receipt_sha256: str = "",
    environment_fingerprint: str = "",
) -> list[str]:
    """Validate the evidence chain before a positive decision is possible.

    A status flag is not evidence.  Every successful stage must be a
    self-hashed receipt tied to the exact proposal and contract; the runner
    must carry the environment and metric versions; the analyst must carry
    the runner receipt reference.  This remains domain-neutral while making a
    hand-written ``{"status": "PASS"}`` unable to become KEEP.
    """

    errors: list[str] = []
    trial_id = str(proposal.get("trial_id", ""))
    proposal_hash_value = str(proposal.get("proposal_sha256", ""))
    contract_hash_value = str(contract.get("contract_sha256", ""))

    def common(receipt: Mapping[str, Any], label: str) -> None:
        if not isinstance(receipt, Mapping):
            errors.append(f"{label} receipt is not an object")
            return
        if receipt.get("trial_id") != trial_id:
            errors.append(f"{label} receipt trial binding is missing or mismatched")
        if receipt.get("proposal_sha256") != proposal_hash_value:
            errors.append(f"{label} receipt proposal binding is missing or mismatched")
        if receipt.get("contract_sha256") != contract_hash_value:
            errors.append(f"{label} receipt contract binding is missing or mismatched")
        if not _has_hash(receipt.get("receipt_sha256")) or receipt.get("receipt_sha256") != _receipt_digest(receipt):
            errors.append(f"{label} receipt self-hash is missing or invalid")

    if code_receipt.get("status") in {"PASS", "SINGLE_AGENT_MODE"}:
        common(code_receipt, "code")
        if _first_present(code_receipt, "code_version", "commit", "code.commit") is None:
            errors.append("code receipt must bind a code version")
        configuration = code_receipt.get("configuration")
        if not _has_hash(_first_present(code_receipt, "configuration_sha256", "config_sha256")) and not (isinstance(configuration, Mapping) and _has_hash(configuration.get("sha256"))):
            errors.append("code receipt must bind a configuration hash")

    if test_receipt.get("status") == "PASS":
        common(test_receipt, "test")
        if test_receipt.get("code_receipt_sha256") != code_receipt.get("receipt_sha256"):
            errors.append("test receipt is not bound to the code receipt")
        if _first_present(test_receipt, "test_version", "test_suite_sha256") is None:
            errors.append("test receipt must bind a test version")

    if run_receipt.get("status") in _GOOD_RUN_STATUSES:
        common(run_receipt, "run")
        if run_receipt.get("code_receipt_sha256") != code_receipt.get("receipt_sha256"):
            errors.append("run receipt is not bound to the code receipt")
        if run_receipt.get("test_receipt_sha256") != test_receipt.get("receipt_sha256"):
            errors.append("run receipt is not bound to the test receipt")
        if not _has_hash(run_receipt.get("environment_receipt_sha256")):
            errors.append("run receipt must bind an environment receipt")
        if environment_receipt_sha256 and run_receipt.get("environment_receipt_sha256") != environment_receipt_sha256:
            errors.append("run receipt environment binding drift")
        if not _has_hash(run_receipt.get("environment_fingerprint")):
            errors.append("run receipt must bind an environment fingerprint")
        if environment_fingerprint and run_receipt.get("environment_fingerprint") != environment_fingerprint:
            errors.append("run receipt environment fingerprint drift")
        versions = run_receipt.get("metric_versions")
        if not isinstance(versions, Mapping) or not versions:
            errors.append("run receipt must bind metric versions")

    if analysis.get("status") == "PASS":
        common(analysis, "analysis")
        if analysis.get("run_receipt_sha256") != run_receipt.get("receipt_sha256"):
            errors.append("analysis is not bound to the run receipt")
        if not _has_hash(analysis.get("environment_receipt_sha256")):
            errors.append("analysis must bind an environment receipt")
        if environment_receipt_sha256 and analysis.get("environment_receipt_sha256") != environment_receipt_sha256:
            errors.append("analysis environment binding drift")
        if not _has_hash(analysis.get("environment_fingerprint")):
            errors.append("analysis must bind an environment fingerprint")
        if environment_fingerprint and analysis.get("environment_fingerprint") != environment_fingerprint:
            errors.append("analysis environment fingerprint drift")
        versions = analysis.get("metric_versions")
        run_versions = run_receipt.get("metric_versions")
        if not isinstance(versions, Mapping) or not versions:
            errors.append("analysis must bind metric versions")
        elif isinstance(run_versions, Mapping) and any(run_versions.get(key) != value for key, value in versions.items()):
            errors.append("analysis metric versions drift from the run receipt")
        if analysis.get("valid") is not True:
            errors.append("analysis must explicitly mark evidence valid")
        if analysis.get("reproducible") is not True:
            errors.append("analysis must explicitly mark evidence reproducible")
    return errors


def _improvement(analysis: Mapping[str, Any], objective: Mapping[str, Any]) -> bool:
    if analysis.get("improved") is True or analysis.get("uncertainty_reduced") is True:
        return True
    metric = objective.get("metric")
    baseline = _number(analysis.get("baseline", analysis.get("baseline_metrics", {}).get(metric) if isinstance(analysis.get("baseline_metrics", {}), Mapping) else None))
    observed = _number(analysis.get("observed", analysis.get("metrics", {}).get(metric) if isinstance(analysis.get("metrics", {}), Mapping) else None))
    direction = objective.get("direction", "maximize")
    target = _number(objective.get("target"))
    if target is not None and observed is not None:
        return observed >= target if direction != "minimize" else observed <= target
    if baseline is not None and observed is not None:
        return observed >= baseline if direction != "minimize" else observed <= baseline
    return False


class TrialDecisionEngine:
    def decide(self, *, proposal: Mapping[str, Any], contract: Mapping[str, Any], code_receipt: Mapping[str, Any], test_receipt: Mapping[str, Any], run_receipt: Mapping[str, Any], analysis: Mapping[str, Any], expert_consensus: Optional[Mapping[str, Any]] = None, environment_receipt_sha256: str = "", environment_fingerprint: str = "") -> dict[str, Any]:
        validate_proposal(proposal)
        validate_contract(contract)
        if contract.get("status") != "APPROVED" or contract.get("approval", {}).get("approved_by_user") is not True:
            raise TrialLoopError("an approved Trial Contract is required for trial decisions")
        reasons: list[str] = []
        decision = "REVERT"
        binding_errors = _binding_errors(
            proposal=proposal,
            contract=contract,
            code_receipt=code_receipt,
            test_receipt=test_receipt,
            run_receipt=run_receipt,
            analysis=analysis,
            environment_receipt_sha256=environment_receipt_sha256,
            environment_fingerprint=environment_fingerprint,
        )
        if int(proposal.get("change", {}).get("tier", 3)) >= 3:
            decision = "ESCALATE"
            reasons.append("Tier 3 method or claim pivot")
        elif code_receipt.get("status") not in {"PASS", "SINGLE_AGENT_MODE"}:
            decision = "REVERT"
            reasons.append("code implementation did not pass")
        elif test_receipt.get("status") != "PASS":
            decision = "REVERT"
            reasons.append("independent test failed")
        elif run_receipt.get("status") not in _GOOD_RUN_STATUSES:
            decision = "ESCALATE" if run_receipt.get("status") == "BLOCKED_ENVIRONMENT" else "REVERT"
            reasons.append("online run is not valid evidence")
        elif binding_errors:
            decision = "REVERT"
            reasons.extend(binding_errors)
        elif not raw_evidence_complete(run_receipt):
            decision = "REVERT"
            reasons.append("raw evidence is missing or lacks complete SHA-256 receipts")
        elif analysis.get("valid") is False or analysis.get("manual_operation") is True or analysis.get("reproducible") is False:
            decision = "REVERT"
            reasons.append("analysis evidence is invalid, manually altered, or not reproducible")
        elif expert_consensus and expert_consensus.get("status") == "CRITICAL_BLOCK":
            decision = "ESCALATE"
            reasons.append("dynamic expert panel has an unresolved Critical Block")
        elif analysis.get("contradictory") or analysis.get("needs_discriminative_experiment"):
            decision = "INVESTIGATE"
            reasons.append("analysis requires one minimal discriminative experiment")
        elif _improvement(analysis, contract.get("primary_objective", {})):
            decision = "KEEP"
            reasons.append("primary objective improved or uncertainty was reduced")
        else:
            reasons.append("no reproducible improvement or information gain")
        result = {
            "schema_version": "robotics-ar-trial-decision.v1",
            "trial_id": proposal.get("trial_id"),
            "decision": decision,
            "reasons": reasons,
            "code_receipt_sha256": sha256_obj(dict(code_receipt)),
            "test_receipt_sha256": sha256_obj(dict(test_receipt)),
            "run_receipt_sha256": sha256_obj(dict(run_receipt)),
            "analysis_sha256": sha256_obj(dict(analysis)),
            "expert_consensus_sha256": sha256_obj(dict(expert_consensus)) if expert_consensus else None,
            "created_at": utc_now(),
        }
        result["decision_sha256"] = sha256_obj(result)
        try:
            validate_artifact("robotics-ar-trial-decision.v1", result)
        except SchemaValidationError as exc:
            raise TrialLoopError(str(exc)) from exc
        return result


class TrialLoop:
    """Run a single proposal through deterministic callbacks and persist receipts."""

    def __init__(self, experiment_root: Path | str, *, decision_engine: Optional[TrialDecisionEngine] = None, manager: Any = None, best_known: Any = None) -> None:
        self.root = Path(experiment_root)
        self.engine = decision_engine or TrialDecisionEngine()
        self.manager = manager
        self.best_known = best_known

    @staticmethod
    def _callback(callbacks: Mapping[str, Callable[..., Mapping[str, Any]]], name: str, *args: Any) -> dict[str, Any]:
        callback = callbacks.get(name)
        if callback is None:
            return {"status": "BLOCKED", "error": f"required callback is missing: {name}", "callback": name}
        try:
            value = callback(*args)
        except Exception as exc:  # callback failures become auditable receipts
            return {"status": "FAILED", "error": str(exc), "exception": type(exc).__name__, "callback": name}
        if not isinstance(value, Mapping):
            return {"status": "FAILED", "error": f"callback {name} did not return a mapping", "callback": name}
        return dict(value)

    def run(self, proposal: Mapping[str, Any], contract: Mapping[str, Any], *, callbacks: Mapping[str, Callable[..., Mapping[str, Any]]], environment_receipt_sha256: str = "", environment_fingerprint: str = "", used_trials: int = 0, parallel_jobs: int = 0) -> dict[str, Any]:
        validate_proposal(proposal)
        contract_binding = str(proposal.get("parent_contract", ""))
        if contract_binding and contract_binding not in {str(contract.get("contract_sha256")), str(contract.get("contract_id"))}:
            result = {"schema_version": "robotics-ar-trial-decision.v1", "trial_id": proposal.get("trial_id"), "decision": "ESCALATE", "reasons": ["trial proposal is bound to a different contract"], "created_at": utc_now()}
            result["decision_sha256"] = sha256_obj(result)
            self._save(proposal["trial_id"], result)
            return result
        try:
            TrialContractManager.check_trial(contract, proposal, used_trials=used_trials, parallel_jobs=parallel_jobs, environment_receipt_sha256=environment_receipt_sha256)
        except TrialContractError as exc:
            result = {"schema_version": "robotics-ar-trial-decision.v1", "trial_id": proposal.get("trial_id"), "decision": "ESCALATE", "reasons": [str(exc)], "created_at": utc_now()}
            result["decision_sha256"] = sha256_obj(result)
            self._save(proposal["trial_id"], result)
            return result

        trial_dir = self.root / str(proposal["trial_id"])
        trial_dir.mkdir(parents=True, exist_ok=True)
        if self.manager is not None and self.manager.state.get("state") == "TRIAL_BATCH_READY":
            self.manager.transition("TRIAL_PLANNING", "TRIAL_PLANNING_STARTED", {"trial_id": proposal["trial_id"]})
        self._advance("TRIAL_IMPLEMENTING", "TRIAL_CODE_STARTED", {"trial_id": proposal["trial_id"]})
        code = self._callback(callbacks, "code", proposal)
        self._advance("TRIAL_TESTING", "TRIAL_CODE_COMPLETED", {"trial_id": proposal["trial_id"]})

        execution_issue = ""
        if code.get("status") not in {"PASS", "SINGLE_AGENT_MODE"}:
            execution_issue = "code_failure"
            test = {"status": "CODE_BLOCKED", "error": "code callback did not pass"}
            run = {"status": "CODE_BLOCKED", "raw_evidence": {}}
            analysis = {"status": "NOT_ANALYZED", "valid": False}
            expert = None
            self._advance("TRIAL_DEBUGGING", "TRIAL_CODE_FAILED", {"trial_id": proposal["trial_id"]})
        else:
            test = self._callback(callbacks, "test", proposal, code)
            if test.get("status") != "PASS":
                execution_issue = "test_failure"
                run = {"status": "TEST_BLOCKED", "raw_evidence": {}}
                analysis = {"status": "NOT_ANALYZED", "valid": False}
                expert = None
                self._advance("TRIAL_DEBUGGING", "TRIAL_TEST_FAILED", {"trial_id": proposal["trial_id"]})
            else:
                self._advance("TRIAL_RUNNING", "TRIAL_TEST_COMPLETED", {"trial_id": proposal["trial_id"]})
                run = self._callback(callbacks, "run", proposal, code, test)
                if run.get("status") not in _GOOD_RUN_STATUSES:
                    execution_issue = "environment_failure" if run.get("status") == "BLOCKED_ENVIRONMENT" else "run_failure"
                    analysis = {"status": "NOT_ANALYZED", "valid": False}
                    expert = None
                    target = "BLOCKED_ENVIRONMENT" if execution_issue == "environment_failure" else "FAILED_RECOVERABLE"
                    self._advance(target, "TRIAL_RUN_FAILED", {"trial_id": proposal["trial_id"], "status": run.get("status")})
                elif not raw_evidence_complete(run):
                    execution_issue = "raw_evidence_failure"
                    analysis = {"status": "RAW_EVIDENCE_INVALID", "valid": False}
                    expert = None
                    self._advance("TRIAL_ANALYZING", "TRIAL_RUN_COMPLETED", {"trial_id": proposal["trial_id"]})
                    self._advance("AWAITING_USER_DIRECTION", "RAW_EVIDENCE_REJECTED", {"trial_id": proposal["trial_id"]})
                else:
                    self._advance("TRIAL_ANALYZING", "TRIAL_RUN_COMPLETED", {"trial_id": proposal["trial_id"]})
                    analysis = self._callback(callbacks, "analysis", proposal, run)
                    if analysis.get("status") != "PASS":
                        execution_issue = "analysis_failure"
                        analysis.setdefault("valid", False)
                        expert = None
                        self._advance("AWAITING_USER_DIRECTION", "TRIAL_ANALYSIS_FAILED", {"trial_id": proposal["trial_id"]})
                    else:
                        self._advance("TRIAL_EXPERT_REVIEW", "TRIAL_ANALYSIS_COMPLETED", {"trial_id": proposal["trial_id"]})
                        expert = self._callback(callbacks, "expert", proposal, analysis) if "expert" in callbacks else None
                        if expert is not None and expert.get("status") in {"FAILED", "BLOCKED"}:
                            execution_issue = "expert_failure"
                            self._advance("AWAITING_USER_DIRECTION", "TRIAL_EXPERT_REVIEW_FAILED", {"trial_id": proposal["trial_id"]})

        if self.manager is not None and self.manager.state.get("state") in {"TRIAL_EXPERT_REVIEW", "TRIAL_ANALYZING"} and execution_issue:
            # The explicit failure routes above normally handle this.  This is
            # a defensive guard for custom managers and callback combinations.
            self._advance("AWAITING_USER_DIRECTION", "TRIAL_FAILURE_REQUIRES_DIRECTION", {"trial_id": proposal["trial_id"], "failure": execution_issue})

        if not execution_issue and self.manager is not None and self.manager.state.get("state") == "TRIAL_EXPERT_REVIEW":
            self._advance("TRIAL_DECIDING", "TRIAL_EXPERT_REVIEW_COMPLETED", {"trial_id": proposal["trial_id"]})

        decision = self.engine.decide(proposal=proposal, contract=contract, code_receipt=code, test_receipt=test, run_receipt=run, analysis=analysis, expert_consensus=expert, environment_receipt_sha256=environment_receipt_sha256, environment_fingerprint=environment_fingerprint)
        rollback: dict[str, Any] = {"status": "NOT_REQUESTED", "reason": "decision was not REVERT"}
        if decision.get("decision") == "REVERT":
            if "rollback" in callbacks:
                rollback = self._callback(callbacks, "rollback", proposal, code, run, analysis)
                if rollback.get("status") not in _ROLLBACK_OK:
                    decision = dict(decision)
                    decision["decision"] = "ESCALATE"
                    decision.setdefault("reasons", []).append("rollback callback did not confirm a safe rollback")
                    decision["decision_sha256"] = sha256_obj({key: value for key, value in decision.items() if key != "decision_sha256"})
            else:
                rollback = {"status": "NOT_REQUESTED", "reason": "no rollback callback supplied"}

        receipt = {"schema_version": "robotics-ar-trial-run-receipt.v1", "trial_id": proposal["trial_id"], "proposal_sha256": proposal.get("proposal_sha256"), "code": code, "test": test, "run": run, "analysis": analysis, "expert": expert, "rollback": rollback, "decision": decision, "created_at": utc_now()}
        receipt["receipt_sha256"] = sha256_obj(receipt)
        atomic_write_json(trial_dir / "decision-receipt.json", receipt)
        if decision.get("decision") == "KEEP" and self.best_known is not None and "candidate" in callbacks:
            candidate = callbacks["candidate"](proposal, run, analysis)
            self.best_known.promote(candidate)

        if not execution_issue:
            if decision.get("decision") in {"KEEP", "REVERT"}:
                self._advance("BATCH_CHECKPOINT", "TRIAL_KEPT" if decision["decision"] == "KEEP" else "TRIAL_REVERTED", {"trial_id": proposal["trial_id"], "decision_sha256": decision["decision_sha256"]})
            elif decision.get("decision") in {"INVESTIGATE", "ESCALATE"}:
                self._advance("AWAITING_USER_DIRECTION", "TRIAL_INVESTIGATION_REQUESTED" if decision["decision"] == "INVESTIGATE" else "USER_DIRECTION_REQUESTED", {"trial_id": proposal["trial_id"], "decision_sha256": decision["decision_sha256"]})
        if self.manager is not None and hasattr(self.manager, "paths"):
            # A trial receipt alone is not enough for human re-entry.  Refresh
            # the supervisor-owned report/handoff after every decision so a
            # new process can recover the just-completed trial from disk.
            from .reporting_v3 import write_checkpoint_artifacts

            context: dict[str, Any] = {"trial_id": proposal["trial_id"]}
            if decision.get("decision") == "KEEP":
                context["kept_results"] = [proposal["trial_id"]]
            elif decision.get("decision") == "REVERT":
                context["negative_results"] = [proposal["trial_id"]]
            elif decision.get("decision") in {"INVESTIGATE", "ESCALATE"}:
                context["decisions_required"] = [str(item) for item in decision.get("reasons", [])]
            write_checkpoint_artifacts(self.manager, context=context, reason=f"trial-{proposal['trial_id']}-{decision.get('decision', 'UNKNOWN').lower()}")
        return decision

    def _save(self, trial_id: str, result: Mapping[str, Any]) -> None:
        target = self.root / str(trial_id)
        target.mkdir(parents=True, exist_ok=True)
        write_structured(target / "decision-receipt.json", dict(result))

    def _advance(self, target: str, event_type: str, payload: Mapping[str, Any]) -> None:
        if self.manager is None or self.manager.state.get("state") == target:
            return
        try:
            self.manager.transition(target, event_type, payload)
        except Exception as exc:
            raise TrialLoopError(f"trial state transition failed: {target}") from exc
