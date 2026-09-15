"""Append-only historical experiment ledger and Do-Not-Repeat registry."""

from __future__ import annotations

import hashlib
import json
import csv
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from .atomic_io import optional_report_bytes, atomic_write_json, runtime_root, project_output_directory
from .canonical import sha256_obj
from .models import utc_now
from .structured import read_structured, write_structured


class HistoryError(RuntimeError):
    """Raised when history cannot be imported without upgrading uncertainty."""


VALID_STATUSES = frozenset({"VERIFIED", "FAILED", "INVALID", "INCONCLUSIVE", "UNKNOWN", "UNREPRODUCIBLE"})
VALID_DECISIONS = frozenset({"KEEP", "REJECT", "SUPERSEDED", "UNKNOWN"})


_SEMANTIC_ALIASES = {"init": "initialization", "initialisation": "initialization", "init_params": "initialization", "lazyrepair": "lazy_repair", "lazy-repair": "lazy_repair"}


def _semantic(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {(_SEMANTIC_ALIASES.get(str(key).lower(), str(key).lower()) if str(key).lower() not in {"name", "label", "display_name"} else "_label"): _semantic(item) for key, item in sorted(value.items(), key=lambda item: str(item[0])) if str(key).lower() not in {"name", "label", "display_name"}}
    if isinstance(value, list):
        return [_semantic(item) for item in value]
    if isinstance(value, str):
        normalized = value.strip().lower()
        return _SEMANTIC_ALIASES.get(normalized, normalized)
    return value


def trial_fingerprint(record: Mapping[str, Any]) -> str:
    """Hash the substantive trial content, excluding provenance and status."""

    selected = {
        key: record.get(key)
        for key in ("hypothesis", "change_summary", "changed_components", "code", "configuration", "environment", "dataset", "execution", "metrics", "metric_versions")
    }
    return sha256_obj(_semantic(selected))


def _confidence(record: Mapping[str, Any]) -> str:
    if record.get("code", {}).get("commit") and record.get("configuration", {}).get("sha256") and record.get("environment", {}).get("fingerprint"):
        return "high"
    if record.get("hypothesis") or record.get("metrics"):
        return "medium"
    return "low"


def _metric_versions(metrics: Any, explicit: Any = None) -> dict[str, str]:
    """Return explicitly declared metric versions without inventing versions."""

    versions: dict[str, str] = {}
    if isinstance(explicit, Mapping):
        versions.update({str(key): str(value) for key, value in explicit.items() if value not in (None, "")})
    if isinstance(metrics, Mapping):
        for name, value in metrics.items():
            if isinstance(value, Mapping):
                version = value.get("metric_version", value.get("version", value.get("version_id")))
                if version not in (None, ""):
                    versions.setdefault(str(name), str(version))
    return versions


def normalize_record(raw: Mapping[str, Any], *, origin: str = "imported", source: str = "") -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise HistoryError("history record must be an object")
    code = dict(raw.get("code", {})) if isinstance(raw.get("code", {}), Mapping) else {}
    configuration = dict(raw.get("configuration", {})) if isinstance(raw.get("configuration", {}), Mapping) else {}
    environment = dict(raw.get("environment", {})) if isinstance(raw.get("environment", {}), Mapping) else {}
    execution = dict(raw.get("execution", {})) if isinstance(raw.get("execution", {}), Mapping) else {}
    status = str(raw.get("status", "UNKNOWN")).upper()
    if status not in VALID_STATUSES:
        status = "UNKNOWN"
    has_binding = bool(code.get("commit") and configuration.get("sha256") and environment.get("fingerprint"))
    if status == "VERIFIED" and not has_binding:
        status = "UNKNOWN"
    failure_class = str(raw.get("failure_class", ""))
    if failure_class in {"implementation_bug", "test_harness_bug", "environment_bug", "data_corruption"}:
        status = "INVALID"
    decision = str(raw.get("user_decision", "UNKNOWN")).upper()
    if decision not in VALID_DECISIONS:
        decision = "UNKNOWN"
    record: dict[str, Any] = {
        "schema_version": "robotics-ar-trial-ledger.v1",
        "trial_id": str(raw.get("trial_id", raw.get("experiment_id", ""))) or f"imported-{hashlib.sha256((source or utc_now()).encode()).hexdigest()[:12]}",
        "origin": origin,
        "hypothesis": raw.get("hypothesis", ""),
        "change_summary": raw.get("change_summary", raw.get("change", "")),
        "changed_components": list(raw.get("changed_components", [])) if isinstance(raw.get("changed_components", []), list) else [str(raw.get("change", ""))],
        "code": code,
        "configuration": configuration,
        "environment": environment,
        "dataset": raw.get("dataset", {}),
        "execution": execution,
        "metrics": raw.get("metrics", {}),
        "metric_versions": _metric_versions(raw.get("metrics", {}), raw.get("metric_versions")),
        "artifacts": list(raw.get("artifacts", [])) if isinstance(raw.get("artifacts", []), list) else [],
        "status": status,
        "failure_class": failure_class,
        "interpretation": raw.get("interpretation", ""),
        "user_decision": decision,
        "eligible_for_retry": bool(raw.get("eligible_for_retry", decision != "REJECT" and status not in {"INVALID"})),
        "confidence": str(raw.get("confidence", _confidence(raw))),
        "source_receipts": list(raw.get("source_receipts", [])) if isinstance(raw.get("source_receipts", []), list) else [],
        "source": source,
        "imported_at": utc_now(),
    }
    record["trial_fingerprint"] = trial_fingerprint(record)
    return record


class DoNotRepeatRegistry:
    """Persist reasons and substantive fingerprints for no-repeat enforcement."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.entries: list[dict[str, Any]] = []
        if self.path.exists():
            value = read_structured(self.path)
            if isinstance(value, Mapping):
                if value.get("registry_sha256") and value.get("registry_sha256") != sha256_obj({key: item for key, item in value.items() if key != "registry_sha256"}):
                    raise HistoryError("Do-Not-Repeat Registry hash mismatch")
                self.entries = list(value.get("entries", []))
            elif isinstance(value, list):
                self.entries = list(value)

    def add(self, record_or_proposal: Mapping[str, Any], *, reason: str, category: str = "KNOWN_FAILURE") -> dict[str, Any]:
        fingerprint = str(record_or_proposal.get("trial_fingerprint") or trial_fingerprint(record_or_proposal))
        entry = {"fingerprint": fingerprint, "reason": reason, "category": category, "source_trial_id": record_or_proposal.get("trial_id"), "material_difference_required": True, "created_at": utc_now()}
        if not any(item.get("fingerprint") == fingerprint for item in self.entries):
            self.entries.append(entry)
        self.save()
        return entry

    def match(self, proposal: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        fingerprint = str(proposal.get("trial_fingerprint") or trial_fingerprint(proposal))
        for entry in self.entries:
            if entry.get("fingerprint") == fingerprint:
                return dict(entry)
        return None

    @staticmethod
    def _material_difference(proposal: Mapping[str, Any]) -> Optional[Any]:
        """Return an explicit, non-empty difference for a requested retry.

        A retry cannot be justified by a keyword in free text.  The proposal
        must carry a structured or textual statement of what changed in the
        experimental condition, implementation, metric, data, or protocol.
        """

        change = proposal.get("change", {})
        candidate = change.get("material_difference") if isinstance(change, Mapping) else None
        if candidate in (None, "", [], {}):
            candidate = proposal.get("material_difference")
        if isinstance(candidate, Mapping):
            if not candidate or not any(value not in (None, "", [], {}) for value in candidate.values()):
                return None
            return dict(candidate)
        if isinstance(candidate, list):
            values = [item for item in candidate if item not in (None, "", [], {})]
            return values or None
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return None

    def retry_evidence(self, proposal: Mapping[str, Any], *, justification: str = "") -> Optional[dict[str, Any]]:
        """Build auditable retry evidence, or return ``None`` when absent."""

        match = self.match(proposal)
        if match is None:
            return None
        difference = self._material_difference(proposal)
        text = str(justification or "").strip()
        if difference is None or not text:
            return None
        return {
            "parent_fingerprint": match.get("fingerprint"),
            "material_difference": difference,
            "justification": text,
            "recorded_at": utc_now(),
        }

    def can_retry(self, proposal: Mapping[str, Any], *, justification: str = "") -> bool:
        return self.match(proposal) is None or self.retry_evidence(proposal, justification=justification) is not None

    def save(self) -> Path:
        value = {"schema_version": "robotics-ar-do-not-repeat.v1", "entries": self.entries, "updated_at": utc_now()}
        value["registry_sha256"] = sha256_obj(value)
        return write_structured(self.path, value)


class ExperimentLedger:
    """Append-only JSONL ledger with content-hash deduplication."""

    def __init__(self, path: Path | str, registry_path: Optional[Path | str] = None) -> None:
        self.path = Path(path)
        self.registry = DoNotRepeatRegistry(registry_path or self.path.with_name("do-not-repeat.yaml"))

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.strip():
                source = f"{self.path.as_posix()}#{line_number}"
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    value = None
                if isinstance(value, Mapping):
                    rows.append(dict(value))
                    continue
                line_hash = hashlib.sha256(line.encode("utf-8", errors="replace")).hexdigest()
                rows.append(
                    normalize_record(
                        {
                            "trial_id": f"{self.path.stem}-invalid-{line_number:04d}",
                            "status": "INVALID",
                            "failure_class": "malformed_history_record",
                            "change_summary": f"malformed-history:{line_hash}",
                            "interpretation": f"Malformed JSONL record at line {line_number}",
                            "eligible_for_retry": False,
                            "raw_line_sha256": line_hash,
                        },
                        origin="imported",
                        source=source,
                    )
                )
        return rows

    def append(self, record: Mapping[str, Any], *, add_to_no_repeat: Optional[str] = None) -> dict[str, Any]:
        normalized = normalize_record(record, origin=str(record.get("origin", "robot_ar_v3")))
        existing = self._read()
        if any(item.get("trial_fingerprint") == normalized["trial_fingerprint"] for item in existing):
            return next(item for item in existing if item.get("trial_fingerprint") == normalized["trial_fingerprint"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        if normalized.get("user_decision") == "REJECT" or normalized.get("status") in {"INVALID", "FAILED"}:
            self.registry.add(normalized, reason=add_to_no_repeat or normalized.get("failure_class") or "historical failure", category="USER_REJECTED" if normalized.get("user_decision") == "REJECT" else "KNOWN_FAILURE")
        return normalized

    def import_sources(self, sources: Iterable[Path | str]) -> list[dict[str, Any]]:
        imported: list[dict[str, Any]] = []
        for source_value in sources:
            source = Path(source_value)
            if not source.exists() or source.is_dir():
                continue
            if source.suffix.lower() in {".json", ".jsonl", ".yaml", ".yml"}:
                if source.suffix.lower() == ".jsonl":
                    candidates = []
                    for line_number, line in enumerate(source.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        if not line.strip():
                            continue
                        try:
                            value = json.loads(line)
                        except json.JSONDecodeError:
                            candidates.append(
                                {
                                    "trial_id": f"{source.stem}-invalid-{line_number:04d}",
                                    "status": "INVALID",
                                    "failure_class": "malformed_history_record",
                                    "change_summary": f"malformed-history:{hashlib.sha256(line.encode('utf-8', errors='replace')).hexdigest()}",
                                    "interpretation": f"Malformed JSONL record at line {line_number}",
                                    "eligible_for_retry": False,
                                }
                            )
                            continue
                        if isinstance(value, Mapping):
                            candidates.append(value)
                else:
                    candidates = []
                try:
                    if source.suffix.lower() != ".jsonl":
                        value = read_structured(source)
                except Exception:
                    continue
                if source.suffix.lower() != ".jsonl":
                    candidates = value if isinstance(value, list) else value.get("trials", value.get("experiments", [value])) if isinstance(value, Mapping) else []
                if isinstance(candidates, Mapping):
                    candidates = [candidates]
                for candidate in candidates:
                    if isinstance(candidate, Mapping):
                        imported.append(self.append(normalize_record(candidate, origin="imported", source=source.as_posix())))
            elif source.suffix.lower() == ".csv":
                try:
                    with source.open("r", encoding="utf-8", newline="") as handle:
                        for index, row in enumerate(csv.DictReader(handle), 1):
                            candidate = dict(row)
                            candidate.setdefault("trial_id", f"{source.stem}-{index:04d}")
                            imported.append(self.append(normalize_record(candidate, origin="imported", source=source.as_posix())))
                except (OSError, csv.Error):
                    continue
            elif source.suffix.lower() in {".md", ".txt", ".log"}:
                imported.append(self.append(normalize_record({"trial_id": f"imported-{sha256_obj({'path': source.as_posix()})[:12]}", "interpretation": source.read_text(encoding="utf-8", errors="replace")[:4000], "status": "UNKNOWN"}, origin="imported", source=source.as_posix())))
        return imported

    def records(self) -> list[dict[str, Any]]:
        return self._read()


def reconstruct_history(project_root: Path | str, *, sources: Optional[Iterable[Path | str]] = None, output_dir: Optional[Path | str] = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    target = project_output_directory(root, output_dir or runtime_root(root) / "takeover" / "history")
    target.mkdir(parents=True, exist_ok=True)
    selected = list(sources or [])
    if not selected:
        excluded = {".git", ".venv", "venv", "node_modules", "__pycache__"}
        selected = []
        for path in root.rglob("*"):
            if not path.is_file() or any(part in excluded for part in path.parts):
                continue
            if target in path.parents:
                continue
            lower_path = path.as_posix().lower()
            if path.name in {"report.md", "handoff.md", "task.md", "experiment-ledger.jsonl"} or any(token in lower_path for token in ("/experiment", "/result", "/log", "/history")) and path.suffix.lower() in {".json", ".jsonl", ".yaml", ".yml", ".csv", ".log", ".txt"}:
                selected.append(path)
    ledger = ExperimentLedger(target / "experiment-ledger.jsonl", target / "do-not-repeat.yaml")
    records = ledger.import_sources(selected)
    known_failures = [record for record in records if record.get("status") in {"FAILED", "INVALID"}]
    best = [record for record in records if record.get("status") == "VERIFIED" and record.get("user_decision") != "REJECT"]
    optional_report_bytes(target / "known-failures.md", ("# Known failures\n\n" + "\n".join(f"- `{item['trial_id']}`: {item.get('failure_class') or item.get('interpretation', '')}" for item in known_failures) + "\n").encode("utf-8"))
    write_structured(target / "best-known-candidates.yaml", {"schema_version": "robotics-ar-best-known-candidates.v1", "candidates": best})
    unknown_ids = [item["trial_id"] for item in records if item.get("status") in {"UNKNOWN", "UNREPRODUCIBLE"}]
    metric_versions: dict[str, dict[str, list[str]]] = {}
    for record in records:
        for metric, version in _metric_versions(record.get("metrics", {}), record.get("metric_versions")).items():
            metric_versions.setdefault(metric, {}).setdefault(version, []).append(str(record.get("trial_id")))
    metric_conflicts = [
        {"metric": metric, "versions": [{"version": version, "trial_ids": trial_ids} for version, trial_ids in versions.items()]}
        for metric, versions in metric_versions.items()
        if len(versions) > 1
    ]
    write_structured(target / "metric-version-conflicts.json", {"schema_version": "robotics-ar-metric-version-conflicts.v1", "conflicts": metric_conflicts, "requires_reconciliation": bool(metric_conflicts)})
    unresolved_ids = list(unknown_ids)
    if metric_conflicts:
        unresolved_ids.extend(f"metric-version:{item['metric']}" for item in metric_conflicts)
    optional_report_bytes(target / "unresolved-history.md", ("# Unresolved history\n\n" + "\n".join(f"- `{item}`" for item in unresolved_ids) + "\n").encode("utf-8"))
    receipt = {"schema_version": "robotics-ar-history-reconstruction-receipt.v1", "status": "PASS", "records_imported": len(records), "verified_count": sum(item.get("status") == "VERIFIED" for item in records), "unknown_count": sum(item.get("status") in {"UNKNOWN", "UNREPRODUCIBLE"} for item in records), "invalid_count": sum(item.get("status") == "INVALID" for item in records), "metric_version_conflicts": metric_conflicts, "unresolved_count": len(unresolved_ids), "requires_reconciliation": bool(metric_conflicts), "created_at": utc_now()}
    receipt["receipt_sha256"] = sha256_obj(receipt)
    atomic_write_json(target / "history-reconstruction-receipt.json", receipt)
    return {"status": "PASS", "records": records, "receipt": receipt, "output_dir": target.as_posix()}
