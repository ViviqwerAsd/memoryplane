from __future__ import annotations

from memoryplane.paths import MemoryPlanePaths
from memoryplane.storage import CanonicalStore
from memoryplane.services.write_service import WriteService


class MergeService:
    def __init__(self, paths: MemoryPlanePaths):
        self.canonical = CanonicalStore(paths)
        self.write = WriteService(paths)

    def merge(self, memory_id_a: str, memory_id_b: str, *, dry_run: bool = False) -> dict[str, object]:
        if not dry_run:
            raise ValueError("DRY_RUN_REQUIRED")
        first = self.canonical.get_memory(memory_id_a)
        second = self.canonical.get_memory(memory_id_b)
        if first is None or second is None:
            raise FileNotFoundError("memory")
        merged_memory = self.write.create_memory(
            type=first.type if first.type == second.type else "summary",
            space=first.space if first.space == second.space else "summary",
            entity=first.entity,
            content=f"{first.content}; {second.content}",
            source="system:merge",
            durability="durable",
            confidence=max(first.confidence, second.confidence),
        )
        candidate = self.write.create_candidate(
            operation="merge",
            memory=merged_memory,
            metadata={"source_memory_ids": [memory_id_a, memory_id_b]},
        )
        return {"candidate": candidate.model_dump(mode="json")}
