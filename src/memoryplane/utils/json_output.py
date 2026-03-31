from __future__ import annotations

import json
from dataclasses import dataclass

from memoryplane.models import ErrorDetail, ResponseEnvelope


@dataclass(frozen=True)
class CommandFailure(Exception):
    code: str
    message: str
    exit_code: int


def success_response(command: str, data: dict | None = None, warnings: list[str] | None = None) -> str:
    envelope = ResponseEnvelope(ok=True, command=command, data=data or {}, warnings=warnings or [], errors=[])
    return envelope.model_dump_json(indent=2)


def error_response(command: str, code: str, message: str) -> str:
    envelope = ResponseEnvelope(
        ok=False,
        command=command,
        data=None,
        warnings=[],
        errors=[ErrorDetail(code=code, message=message)],
    )
    return envelope.model_dump_json(indent=2)
