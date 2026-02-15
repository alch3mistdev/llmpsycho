"""Profile payload validation utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_KEYS = {
    "run_id",
    "model_id",
    "regimes",
    "diagnostics",
    "risk_flags",
    "budget",
    "stop_reason",
}


def load_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object")
    return payload


def validate_profile_payload(payload: dict[str, Any], schema_path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    # Primary path: full JSON Schema validation.
    try:
        import jsonschema  # type: ignore

        with schema_path.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
        validator = jsonschema.Draft202012Validator(schema)
        for err in validator.iter_errors(payload):
            path = ".".join(str(part) for part in err.path)
            if path:
                errors.append(f"{path}: {err.message}")
            else:
                errors.append(err.message)
        return len(errors) == 0, errors
    except Exception:
        # Fallback path when jsonschema is unavailable.
        pass

    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(payload.keys()))
    if missing:
        errors.append(f"Missing required keys: {', '.join(missing)}")

    regimes = payload.get("regimes")
    if not isinstance(regimes, list) or not regimes:
        errors.append("regimes must be a non-empty list")

    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        errors.append("diagnostics must be an object")

    risk_flags = payload.get("risk_flags")
    if not isinstance(risk_flags, dict):
        errors.append("risk_flags must be an object")

    budget = payload.get("budget")
    if not isinstance(budget, dict):
        errors.append("budget must be an object")

    return len(errors) == 0, errors
