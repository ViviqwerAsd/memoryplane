from __future__ import annotations

import re
from typing import Iterable

from memoryplane.models import DURABILITY_VALUES, ENTITY_TYPES, MEMORY_TYPES, SOURCE_KINDS


class InputValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def format_allowed_values(values: Iterable[str]) -> str:
    return ", ".join(values)


def with_fix(message: str, fix: str) -> str:
    suffix = "" if message.endswith((".", "!", "?")) else "."
    return f"{message}{suffix} Fix: {fix}"


def validate_choice(*, field_name: str, value: str, allowed: Iterable[str], code: str) -> None:
    allowed_values = tuple(allowed)
    if value in allowed_values:
        return
    raise InputValidationError(
        code,
        with_fix(
            f"Invalid {field_name} '{value}'. Allowed values: {format_allowed_values(allowed_values)}",
            f"choose one of: {format_allowed_values(allowed_values)}",
        ),
    )


def validate_source(value: str) -> None:
    if ":" not in value:
        raise InputValidationError(
            "INVALID_SOURCE",
            with_fix(
                f"Invalid source '{value}'. Expected format kind:session_id where kind is one of: {format_allowed_values(SOURCE_KINDS)}",
                "use a value like chat:sess_001",
            ),
        )
    kind, session_id = value.split(":", 1)
    if kind not in SOURCE_KINDS:
        raise InputValidationError(
            "INVALID_SOURCE_KIND",
            with_fix(
                f"Invalid source kind '{kind}'. Allowed values: {format_allowed_values(SOURCE_KINDS)}",
                f"use one of: {format_allowed_values(SOURCE_KINDS)}",
            ),
        )
    if not session_id:
        raise InputValidationError(
            "INVALID_SOURCE",
            with_fix("Source session_id cannot be empty. Expected format kind:session_id", "use a value like chat:sess_001"),
        )


def validate_write_inputs(
    *,
    type: str,
    entity: str,
    durability: str,
    source: str,
    dry_run: bool,
    commit: bool,
) -> None:
    validate_choice(field_name="type", value=type, allowed=MEMORY_TYPES, code="INVALID_TYPE")
    validate_choice(field_name="entity", value=entity, allowed=ENTITY_TYPES, code="INVALID_ENTITY")
    validate_choice(
        field_name="durability",
        value=durability,
        allowed=DURABILITY_VALUES,
        code="INVALID_DURABILITY",
    )
    validate_source(source)
    if dry_run and commit:
        raise InputValidationError(
            "INVALID_WRITE_MODE",
            with_fix("--dry-run and --commit cannot be used together", "pick one mode: proposal with --dry-run or immediate durable write with --commit"),
        )
    if commit and durability != "durable":
        raise InputValidationError(
            "COMMIT_ONLY_FOR_DURABLE",
            with_fix("--commit can only be used with --durability durable", "set --durability durable or remove --commit"),
        )


def validate_type_filters(types: list[str]) -> None:
    for value in types:
        validate_choice(field_name="type", value=value, allowed=MEMORY_TYPES, code="INVALID_TYPE")


def validate_sort_by(*, value: str, allowed: Iterable[str]) -> None:
    validate_choice(field_name="sort-by", value=value, allowed=allowed, code="INVALID_SORT")


def friendly_missing_fields_message(exc: TypeError) -> str:
    fields = sorted(set(re.findall(r"'([^']+)'", str(exc))))
    if not fields:
        return str(exc)
    return with_fix(f"Missing required fields: {', '.join(fields)}", "add these fields to each batch item")
