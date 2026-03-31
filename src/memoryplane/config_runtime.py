from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from memoryplane.utils.validation import InputValidationError


CONFIG_FILENAME = ".memoryplane.conf"


def _load_workspace_config(cwd: Path | None = None) -> dict[str, Any]:
    base_dir = cwd or Path.cwd()
    config_path = base_dir / CONFIG_FILENAME
    if not config_path.exists():
        return {}
    try:
        payload = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        raise InputValidationError(
            "INVALID_CONFIG",
            f"Failed to parse {CONFIG_FILENAME}: {exc.msg}. Fix: write valid JSON such as {{\"root\": \"/tmp/memoryplane\", \"json\": true}}",
        ) from exc
    if not isinstance(payload, dict):
        raise InputValidationError(
            "INVALID_CONFIG",
            f"{CONFIG_FILENAME} must contain a JSON object. Fix: use key/value pairs such as {{\"root\": \"/tmp/memoryplane\", \"json\": true}}",
        )
    return payload


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def resolve_root(root: Path | None, *, cwd: Path | None = None) -> Path:
    if root is not None:
        return root.resolve()
    env_root = os.getenv("MEMORYPLANE_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    config = _load_workspace_config(cwd)
    config_root = config.get("root")
    if isinstance(config_root, str) and config_root.strip():
        return Path(config_root).expanduser().resolve()
    return Path(".").resolve()


def resolve_json_output(json_output: bool | None, *, cwd: Path | None = None) -> bool:
    if json_output is not None:
        return json_output
    env_json = _parse_bool(os.getenv("MEMORYPLANE_JSON"))
    if env_json is not None:
        return env_json
    config = _load_workspace_config(cwd)
    config_json = config.get("json")
    if isinstance(config_json, bool):
        return config_json
    return False
