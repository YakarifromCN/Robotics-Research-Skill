"""外部执行的预算预留与幂等接纳；不启动工作。 / Reserve budgets and accept external results idempotently; never launch work."""
import re
import time
import uuid
from pathlib import Path

from .atomic_io import atomic_write_json, read_json
from .canonical import sha256_obj
from .transaction import writer_lock


class ExecutionRegistry:
    def __init__(self, manager):
        self.manager = manager
        self.path = manager.paths.root / "execution-registry.json"

    def read(self):
        return read_json(self.path) if self.path.exists() else {"schema_version": "robotics-ar-executions.v1", "executions": {}}

    def reserve(self, spec_path, approval_path):
        """先保存准备状态再消费批准；崩溃后不自动重试。 / Persist preparation before consuming approval; no blind crash retry."""
        spec = read_json(spec_path)
        identifier = spec.get("execution_id", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identifier):
            raise ValueError("invalid execution_id")
        with writer_lock(self.path.parent):
            data = self.read()
            rows = data["executions"]
            if identifier in rows:
                old = rows[identifier]
                if old.get("spec_sha256") != sha256_obj(spec):
                    raise ValueError("execution ID reused with different specification")
                if old["status"] == "PREPARING":
                    raise ValueError("uncertain reservation; inspect approval and ledger before recovery")
                return old
            if any(row["status"] == "PREPARING" for row in rows.values()):
                raise ValueError("uncertain prior reservation; reconcile before further spending")
            if any(row.get("accounting_status") == "BUDGET_EXCEEDED" for row in rows.values()):
                raise ValueError("budget exhausted by measured usage; user budget decision required")
            state = self.manager.state
            if state["mode"] != "EXECUTION_ENABLED" or state["state"] in {"COMPLETE", "TAKEOVER_COMPLETE", "ABORTED", "PAUSED"}:
                raise ValueError("execution is not enabled in this state")
            if not spec.get("task_id") or spec.get("design_timing") != "prospective":
                raise ValueError("prospective specification and task_id required")
            if not state.get("environment_fingerprint") or spec.get("environment_fingerprint") != state["environment_fingerprint"]:
                raise ValueError("verified environment fingerprint required")
            parent = spec.get("parent_execution_id")
            if parent and parent not in rows:
                raise ValueError("orphan parent execution")
            costs = spec.get("costs", {})
            if not costs or any(key not in {"trials", "batches", "gpu_hours", "disk_gb", "wall_time_minutes"} for key in costs):
                raise ValueError("explicit supported resource costs required")
            budget = state["exploration_budget"]
            for key, amount in costs.items():
                if type(amount) not in (int, float) or amount < 0:
                    raise ValueError("costs must be finite nonnegative numbers")
                if key in {"trials", "batches"} and amount != int(amount):
                    raise ValueError("trial and batch counts must be integers")
                used_key = "wall_time_used_minutes" if key == "wall_time_minutes" else key + "_used"
                if budget.get(used_key, 0) + amount > budget.get("max_" + key, 0):
                    raise ValueError(f"budget exhausted: {key}")
            active = sum(row["status"] in {"PREPARING", "RESERVED", "RUNNING"} for row in rows.values())
            if active >= budget.get("max_parallel_jobs", 1):
                raise ValueError("parallel execution budget exhausted")
            row = {"execution_id": identifier, "spec_sha256": sha256_obj(spec), "spec": spec,
                   "task_id": spec["task_id"], "parent_execution_id": parent, "attempt_id": str(uuid.uuid4()),
                   "design_timing": "prospective", "costs": costs, "status": "PREPARING"}
            rows[identifier] = row
            atomic_write_json(self.path, data)
            approval = self.manager.consume_approval(approval_path, expected_gate=("TASK", "EXPERIMENT", "BASELINE"), expected_subject_path=spec_path)
            # 预算预留按已消费计入共享状态，失败也不自动退还。 / Charge reservations conservatively to shared state, even on failure.
            updated = self.manager.state
            updated["exploration_budget"] = dict(budget)
            for key, amount in costs.items():
                used_key = "wall_time_used_minutes" if key == "wall_time_minutes" else key + "_used"
                updated["exploration_budget"][used_key] = budget.get(used_key, 0) + amount
            atomic_write_json(self.manager.paths.state, updated)
            self.manager._state = updated
            row.update(status="RESERVED", approval_id=approval["approval_id"], lease_token=str(uuid.uuid4()), lease_expires=time.time() + 3600)
            atomic_write_json(self.path, data)
            self.manager.record_event("EXECUTION_RESERVED", {"execution_id": identifier, "spec_sha256": row["spec_sha256"]})
            return row

    def start(self, identifier, token):
        with writer_lock(self.path.parent):
            if self.manager.state["state"] in {"COMPLETE", "TAKEOVER_COMPLETE", "ABORTED", "PAUSED"}:
                raise ValueError("session is stopped")
            data = self.read()
            row = data["executions"][identifier]
            self._check_lease(row, token)
            if row["status"] != "RESERVED":
                raise ValueError("execution already launched or closed; reconcile before retry")
            row.update(status="RUNNING", launched_at=time.time())
            atomic_write_json(self.path, data)
            return row

    @staticmethod
    def _check_lease(row, token):
        if token != row.get("lease_token") or time.time() >= row.get("lease_expires", 0):
            raise ValueError("stale or invalid execution lease")

    def finish(self, identifier, token, result):
        with writer_lock(self.path.parent):
            data = self.read()
            row = data["executions"][identifier]
            digest = sha256_obj(result)
            if row["status"] in {"COMPLETE", "FAILED"}:
                if token == row.get("lease_token") and row["result_sha256"] == digest:
                    return row
                raise ValueError("conflicting duplicate completion")
            self._check_lease(row, token)
            if row["status"] != "RUNNING":
                raise ValueError("durable launch record required")
            if result.get("execution_id") != identifier or result.get("status") not in {"PASS", "FAIL"}:
                raise ValueError("bound PASS/FAIL result required")
            actual = result.get("actual_costs")
            row["accounting_status"] = "USAGE_UNVERIFIED"
            if actual is not None:
                if not isinstance(actual, dict) or not actual or any(key not in {"trials", "batches", "gpu_hours", "disk_gb", "wall_time_minutes"} for key in actual):
                    raise ValueError("actual_costs must contain supported resource measurements")
                from .canonical import ensure_finite
                for amount in actual.values():
                    if type(amount) not in (int, float) or amount < 0:
                        raise ValueError("actual costs must be finite nonnegative measurements")
                    ensure_finite(amount)
                if any(key in {"trials", "batches"} and amount != int(amount) for key, amount in actual.items()):
                    raise ValueError("measured trial and batch counts must be integers")
                self.manager._state = None
                state = self.manager.state
                charges = dict(state.get("execution_usage_charges", {}))
                actual_digest = sha256_obj(actual)
                if identifier in charges and charges[identifier] != actual_digest:
                    raise ValueError("conflicting measured usage after an interrupted settlement")
                if identifier not in charges:
                    budget = dict(state["exploration_budget"])
                    for key, amount in actual.items():
                        used_key = "wall_time_used_minutes" if key == "wall_time_minutes" else key + "_used"
                        budget[used_key] = budget.get(used_key, 0) + max(0, amount - row["costs"].get(key, 0))
                    charges[identifier] = actual_digest
                    state.update(exploration_budget=budget, execution_usage_charges=charges)
                    atomic_write_json(self.manager.paths.state, state)
                    self.manager._state = state
                    self.manager.record_event("EXECUTION_USAGE_RECORDED", {"execution_id": identifier, "actual_costs_sha256": actual_digest})
                budget = self.manager.state["exploration_budget"]
                exceeded = any(budget.get("wall_time_used_minutes" if key == "wall_time_minutes" else key + "_used", 0) > budget.get("max_" + key, 0) for key in actual)
                row["accounting_status"] = "BUDGET_EXCEEDED" if exceeded else ("RECONCILED" if set(row["costs"]) <= set(actual) else "PARTIAL_USAGE")
            row.update(status="COMPLETE" if result["status"] == "PASS" else "FAILED", result_sha256=digest, result=result)
            atomic_write_json(self.path, data)
            return row

    def import_history(self, identifier, result):
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identifier):
            raise ValueError("invalid execution_id")
        with writer_lock(self.path.parent):
            data = self.read()
            row = {"execution_id": identifier, "design_timing": "retrospective", "status": "IMPORTED",
                   "result": result, "result_sha256": sha256_obj(result), "authorized_execution": False}
            previous = data["executions"].get(identifier)
            if previous is not None and previous != row:
                raise ValueError("conflicting execution history")
            data["executions"][identifier] = row
            atomic_write_json(self.path, data)
            return row

    def reconcile(self, resolution_path, approval_path):
        """批准后关闭未知执行，保留未知证据状态与已耗预算。 / Close an approved uncertain execution without upgrading evidence or refunding budget."""
        resolution = read_json(resolution_path)
        with writer_lock(self.path.parent):
            data = self.read()
            row = data["executions"][resolution["execution_id"]]
            digest = sha256_obj(resolution)
            if row.get("reconciliation_sha256") == digest:
                return row
            if row["status"] not in {"PREPARING", "RESERVED", "RUNNING"}:
                raise ValueError("only unresolved executions require reconciliation")
            if resolution.get("previous_sha256") != sha256_obj(row) or resolution.get("external_process_stopped") is not True or not resolution.get("evidence_ref"):
                raise ValueError("bind the prior row and provide an explicit stopped-process evidence reference")
            evidence = Path(resolution["evidence_ref"]).resolve(strict=True)
            evidence.relative_to(self.manager.paths.project_root)
            from .receipts import file_sha256
            if file_sha256(evidence) != resolution.get("evidence_sha256"):
                raise ValueError("reconciliation evidence digest mismatch")
            approval = self.manager.consume_approval(approval_path, expected_gate="TASK", expected_subject_path=resolution_path)
            row.update(status="CLOSED_UNVERIFIED", reconciliation=resolution, reconciliation_sha256=digest,
                       reconciliation_approval_id=approval["approval_id"])
            atomic_write_json(self.path, data)
            self.manager.record_event("EXECUTION_RECONCILED", {"execution_id": row["execution_id"], "resolution_sha256": digest})
            return row
