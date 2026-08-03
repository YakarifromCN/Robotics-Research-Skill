"""Small dependency-free JSON-Schema subset used at runtime.

The Robot-AR schemas are intentionally shallow contracts.  Runtime code still
needs to validate the actual artifacts it writes; checking that schema files
exist is not enough.  This module implements the subset used by the checked-in
schemas so the skill does not require ``jsonschema`` at runtime.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any, Mapping


class SchemaValidationError(ValueError):
    """Raised when a structured artifact violates its declared schema."""


_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def _schema_for(schema_id: str) -> dict[str, Any]:
    if schema_id in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[schema_id]
    for path in sorted(_SCHEMA_ROOT.glob("*.schema.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if schema.get("$id") == schema_id:
            _SCHEMA_CACHE[schema_id] = schema
            return schema
    raise SchemaValidationError(f"runtime schema is not available: {schema_id}")


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _ensure_finite(value: Any, path: str = "$") -> None:
    """Reject non-JSON values before applying the structural schema subset."""

    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SchemaValidationError(f"{path}: non-finite number")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SchemaValidationError(f"{path}: object keys must be strings")
            _ensure_finite(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _ensure_finite(child, f"{path}[{index}]")
        return
    raise SchemaValidationError(f"{path}: unsupported JSON value {type(value).__name__}")


def _resolve_ref(schema: Mapping[str, Any], root: Mapping[str, Any]) -> Mapping[str, Any]:
    reference = str(schema["$ref"])
    if not reference.startswith("#/"):
        raise SchemaValidationError(f"unsupported schema reference: {reference}")
    value: Any = root
    for part in reference[2:].split("/"):
        if not isinstance(value, Mapping) or part not in value:
            raise SchemaValidationError(f"unresolved schema reference: {reference}")
        value = value[part]
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"schema reference is not an object: {reference}")
    return value


def _validate(schema: Mapping[str, Any], value: Any, *, root: Mapping[str, Any], path: str) -> None:
    if "$ref" in schema:
        _validate(_resolve_ref(schema, root), value, root=root, path=path)
        return
    if "const" in schema and value != schema["const"]:
        raise SchemaValidationError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaValidationError(f"{path}: value is outside enum")
    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_type_matches(value, str(item)) for item in types):
            raise SchemaValidationError(f"{path}: expected type {expected!r}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            raise SchemaValidationError(f"{path}: string is shorter than minLength")
        if "pattern" in schema and re.search(str(schema["pattern"]), value) is None:
            raise SchemaValidationError(f"{path}: string does not match pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaValidationError(f"{path}: number is below minimum")
    if isinstance(value, Mapping):
        for required in schema.get("required", []):
            if required not in value:
                raise SchemaValidationError(f"{path}: missing required property {required!r}")
        properties = schema.get("properties", {})
        if isinstance(properties, Mapping):
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, Mapping):
                    _validate(child_schema, value[key], root=root, path=f"{path}.{key}")
    if isinstance(value, list) and isinstance(schema.get("items"), Mapping):
        for index, item in enumerate(value):
            _validate(schema["items"], item, root=root, path=f"{path}[{index}]")


def validate_artifact(schema_id: str, value: Any) -> None:
    """Validate ``value`` against one checked-in Robot-AR schema."""

    schema = _schema_for(schema_id)
    _ensure_finite(value)
    _validate(schema, value, root=schema, path="$" )


__all__ = ["SchemaValidationError", "validate_artifact"]
