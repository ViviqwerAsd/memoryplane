from __future__ import annotations

import json
from uuid import uuid4

from memoryplane.models import CandidateRecord, MemoryRecord, SourceRef
from memoryplane.paths import MemoryPlanePaths
from memoryplane.storage import CandidateStore, CanonicalStore, ProjectionStore, SearchIndexStore
from memoryplane.utils.text import parse_source, utc_now
from memoryplane.utils.validation import validate_write_inputs


class WriteService:
    def __init__(self, paths: MemoryPlanePaths):
        self.paths = paths
        self.candidates = CandidateStore(paths)
        self.canonical = CanonicalStore(paths)
        self.projections = ProjectionStore(paths)
        self.index = SearchIndexStore(paths)

    def create_memory(
        self,
        *,
        type: str,
        space: str,
        entity: str,
        content: str,
        source: str,
        durability: str,
        confidence: float,
    ) -> MemoryRecord:
        kind, session_id = parse_source(source)
        source_ref = SourceRef(kind=kind, session_id=session_id, turn_ids=[])
        return MemoryRecord(
            memory_id=f"mem_{uuid4().hex[:12]}",
            type=type,
            space=space,
            entity=entity,
            content=content,
            source=source_ref,
            timestamp=utc_now(),
            confidence=confidence,
            durability=durability,
            schema_version="v1",
            evidence_refs=[],
            revision=1,
            status="active",
        )

    def create_candidate(self, *, operation: str, memory: MemoryRecord, metadata: dict | None = None) -> CandidateRecord:
        candidate = CandidateRecord(
            candidate_id=f"cand_{uuid4().hex[:12]}",
            proposed_at=utc_now(),
            operation=operation,
            dry_run=True,
            memory=memory,
            metadata=metadata or {},
        )
        self.candidates.save(candidate)
        self._log("candidate_created", {"candidate_id": candidate.candidate_id, "operation": operation})
        return candidate

    def write(
        self,
        *,
        type: str,
        space: str,
        entity: str,
        content: str,
        source: str,
        durability: str,
        confidence: float = 1.0,
        dry_run: bool = False,
        commit: bool = False,
    ) -> tuple[str, dict[str, object]]:
        validate_write_inputs(
            type=type,
            entity=entity,
            durability=durability,
            source=source,
            dry_run=dry_run,
            commit=commit,
        )
        memory = self.create_memory(
            type=type,
            space=space,
            entity=entity,
            content=content,
            source=source,
            durability=durability,
            confidence=confidence,
        )
        if durability == "durable" and commit:
            candidate = self.create_candidate(operation="write", memory=memory)
            committed = self.commit(candidate.candidate_id)
            return "memory", {
                "memory": committed.model_dump(mode="json"),
                "committed_from_candidate_id": candidate.candidate_id,
            }
        if durability == "durable" and not dry_run:
            raise ValueError("DRY_RUN_REQUIRED")
        if dry_run:
            candidate = self.create_candidate(operation="write", memory=memory)
            return "candidate", {"candidate": candidate.model_dump(mode="json")}
        self.canonical.append_memory(memory)
        self.projections.write_memory(memory)
        self.index.add_memory(memory)
        self._log("memory_committed", {"memory_id": memory.memory_id, "operation": "write"})
        return "memory", {"memory": memory.model_dump(mode="json")}

    def commit(self, candidate_id: str) -> MemoryRecord:
        candidate = self.candidates.load(candidate_id)
        if candidate is None:
            raise FileNotFoundError(candidate_id)
        if candidate.status != "proposed":
            raise ValueError("CANDIDATE_NOT_COMMITTABLE")
        memory = candidate.memory
        self.canonical.append_memory(memory)
        self.projections.write_memory(memory)
        self.index.add_memory(memory)

        if candidate.operation == "merge" and candidate.metadata.get("source_memory_ids"):
            self.canonical.append_revision(
                {
                    "timestamp": utc_now(),
                    "kind": "merge",
                    "new_memory_id": memory.memory_id,
                    "source_memory_ids": candidate.metadata["source_memory_ids"],
                }
            )

        self.candidates.delete(candidate_id)
        self._log("candidate_committed", {"candidate_id": candidate_id, "memory_id": memory.memory_id})
        return memory

    def reject(self, candidate_id: str) -> CandidateRecord:
        candidate = self.candidates.mark_rejected(candidate_id)
        if candidate is None:
            raise FileNotFoundError(candidate_id)
        self._log("candidate_rejected", {"candidate_id": candidate_id})
        return candidate

    def _log(self, event: str, payload: dict[str, object]) -> None:
        log_entry = {"timestamp": utc_now(), "event": event, **payload}
        with self.paths.operations_log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(log_entry) + "\n")
