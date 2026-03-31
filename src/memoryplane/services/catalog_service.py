from __future__ import annotations

from collections import Counter
from typing import Any

from memoryplane.models import MemoryRecord
from memoryplane.paths import MemoryPlanePaths
from memoryplane.storage import CandidateStore, CanonicalStore
from memoryplane.utils.text import truncate_text


class CatalogService:
    def __init__(self, paths: MemoryPlanePaths):
        self.paths = paths
        self.canonical = CanonicalStore(paths)
        self.candidates = CandidateStore(paths)

    def list_memories(
        self,
        *,
        limit: int = 20,
        space: str | None = None,
        entity: str | None = None,
        types: list[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        full: bool = False,
    ) -> dict[str, Any]:
        memories = [
            memory
            for memory in self.canonical.list_memories()
            if self._matches_filters(memory, space=space, entity=entity, types=types, after=after, before=before)
        ]
        memories.sort(key=lambda memory: memory.timestamp, reverse=True)
        if full:
            results = [{"memory": memory.model_dump(mode="json")} for memory in memories[:limit]]
        else:
            results = [self._compact_record(memory) for memory in memories[:limit]]
        return {
            "limit": limit,
            "mode": "full" if full else "compact",
            "results": results,
        }

    def stats(self) -> dict[str, Any]:
        memories = self.canonical.list_memories()
        candidates = self.candidates.list_candidates()

        memory_by_status = Counter(memory.status for memory in memories)
        memory_by_space = Counter(memory.space for memory in memories)
        memory_by_type = Counter(memory.type for memory in memories)
        memory_by_entity = Counter(memory.entity for memory in memories)
        memory_by_durability = Counter(memory.durability for memory in memories)
        candidate_by_status = Counter(candidate.status for candidate in candidates)
        candidate_by_operation = Counter(candidate.operation for candidate in candidates)

        return {
            "memories": {
                "total": len(memories),
                "by_status": dict(memory_by_status),
                "by_space": dict(memory_by_space),
                "by_type": dict(memory_by_type),
                "by_entity": dict(memory_by_entity),
                "by_durability": dict(memory_by_durability),
            },
            "candidates": {
                "total": len(candidates),
                "by_status": dict(candidate_by_status),
                "by_operation": dict(candidate_by_operation),
            },
        }

    def _matches_filters(
        self,
        memory: MemoryRecord,
        *,
        space: str | None,
        entity: str | None,
        types: list[str] | None,
        after: str | None,
        before: str | None,
    ) -> bool:
        if memory.status != "active":
            return False
        if space and memory.space != space:
            return False
        if entity and memory.entity != entity:
            return False
        if types and memory.type not in types:
            return False
        if after and memory.timestamp < after:
            return False
        if before and memory.timestamp > before:
            return False
        return True

    def _compact_record(self, memory: MemoryRecord) -> dict[str, Any]:
        return {
            "memory_id": memory.memory_id,
            "type": memory.type,
            "space": memory.space,
            "entity": memory.entity,
            "confidence": memory.confidence,
            "timestamp": memory.timestamp,
            "content_preview": truncate_text(memory.content, 50),
        }
