"""Small, deterministic structured-artifact helpers used by v3.

The runtime writes canonical JSON even for ``.yaml`` artifacts. JSON is a valid
YAML subset, keeps hashes reproducible without a mandatory dependency, and can
still be read by normal YAML tooling. If a user supplies YAML, PyYAML is used
when available; otherwise callers receive an explicit parse error.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .atomic_io import atomic_write_json, read_json
from .canonical import sha256_obj


class StructuredArtifactError(ValueError):
    """Raised for malformed or unsupported structured artifacts."""


def read_structured(path: Path | str) -> Any:
    """Read JSON or YAML without silently accepting a non-object when one is needed."""

    target = Path(path)
    try:
        return read_json(target)
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    try:
        import yaml  # type: ignore

        value = yaml.safe_load(target.read_text(encoding="utf-8"))
    except ImportError as exc:
        raise StructuredArtifactError(f"YAML input requires PyYAML: {target}") from exc
    except Exception as exc:
        raise StructuredArtifactError(f"cannot parse structured artifact: {target}") from exc
    return value


def read_mapping(path: Path | str) -> dict[str, Any]:
    """Read a structured object and require a mapping root."""

    value = read_structured(path)
    if not isinstance(value, Mapping):
        raise StructuredArtifactError(f"mapping required: {path}")
    return dict(value)


def write_structured(path: Path | str, value: Any) -> Path:
    """Write canonical JSON bytes to a JSON/YAML-named artifact."""

    target = Path(path)
    atomic_write_json(target, value)
    return target


def artifact_hash(value: Mapping[str, Any], *, field: str) -> str:
    """Hash a mapping after excluding its self-hash field."""

    return sha256_obj({key: item for key, item in value.items() if key != field})


def set_artifact_hash(value: Mapping[str, Any], *, field: str) -> dict[str, Any]:
    """Copy a mapping and set a canonical self hash."""

    result = dict(value)
    result[field] = artifact_hash(result, field=field)
    return result
