from __future__ import annotations

from typing import Any, Literal, get_args

from pydantic import BaseModel, Field


MemoryType = Literal[
    "preference",
    "profile",
    "entity",
    "event",
    "task",
    "procedure",
    "case",
    "pattern",
    "summary",
    "scratch",
]
EntityType = Literal["user", "project", "system", "topic"]
Durability = Literal["tentative", "durable"]
SourceKind = Literal["chat", "tool", "system"]
CandidateStatus = Literal["proposed", "rejected"]
MemoryStatus = Literal["active", "deprecated", "deleted", "merged"]

MEMORY_TYPES = get_args(MemoryType)
ENTITY_TYPES = get_args(EntityType)
DURABILITY_VALUES = get_args(Durability)
SOURCE_KINDS = get_args(SourceKind)


class SourceRef(BaseModel):
    kind: SourceKind
    session_id: str
    turn_ids: list[str] = Field(default_factory=list)


class MemoryRecord(BaseModel):
    memory_id: str
    type: MemoryType
    space: str
    entity: EntityType
    content: str
    source: SourceRef
    timestamp: str
    confidence: float
    durability: Durability
    schema_version: str = "v1"
    evidence_refs: list[str] = Field(default_factory=list)
    revision: int = 1
    status: MemoryStatus = "active"


class CandidateValidation(BaseModel):
    ok: bool = True
    warnings: list[str] = Field(default_factory=list)


class CandidateRecord(BaseModel):
    candidate_id: str
    proposed_at: str
    operation: str
    dry_run: bool = True
    memory: MemoryRecord
    validation: CandidateValidation = Field(default_factory=CandidateValidation)
    status: CandidateStatus = "proposed"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ResponseEnvelope(BaseModel):
    ok: bool
    command: str
    data: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)
