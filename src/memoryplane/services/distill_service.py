from __future__ import annotations

from datetime import timedelta

from memoryplane.paths import MemoryPlanePaths
from memoryplane.storage import CanonicalStore
from memoryplane.services.write_service import WriteService
from memoryplane.utils.text import parse_window_to_days, utc_now_datetime


class DistillService:
    def __init__(self, paths: MemoryPlanePaths):
        self.canonical = CanonicalStore(paths)
        self.write = WriteService(paths)

    def distill(self, *, window: str, into: str) -> dict[str, object]:
        days = parse_window_to_days(window)
        cutoff = utc_now_datetime() - timedelta(days=days)
        selected = [
            memory
            for memory in self.canonical.list_memories()
            if memory.timestamp >= cutoff.isoformat().replace("+00:00", "Z")
        ]
        summary_lines = [memory.content for memory in selected]
        memory = self.write.create_memory(
            type="summary",
            space=into,
            entity="system",
            content=" | ".join(summary_lines),
            source="system:distill",
            durability="durable",
            confidence=1.0,
        )
        candidate = self.write.create_candidate(
            operation="distill",
            memory=memory,
            metadata={"window": window, "source_memory_ids": [memory.memory_id for memory in selected]},
        )
        return {"candidate": candidate.model_dump(mode="json")}
