from __future__ import annotations

import json
from typing import Any

from memoryplane.models import MemoryRecord
from memoryplane.paths import MemoryPlanePaths


class CanonicalStore:
    def __init__(self, paths: MemoryPlanePaths):
        self.paths = paths

    def append_memory(self, memory: MemoryRecord) -> None:
        self.paths.memories_file.parent.mkdir(parents=True, exist_ok=True)
        with self.paths.memories_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(memory.model_dump(mode="json")) + "\n")

    def list_memories(self) -> list[MemoryRecord]:
        if not self.paths.memories_file.exists():
            return []
        memories: list[MemoryRecord] = []
        for line in self.paths.memories_file.read_text().splitlines():
            if line.strip():
                memories.append(MemoryRecord.model_validate_json(line))
        return memories

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        for memory in self.list_memories():
            if memory.memory_id == memory_id:
                return memory
        return None

    def append_revision(self, event: dict[str, Any]) -> None:
        with self.paths.revisions_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")

    def append_tombstone(self, event: dict[str, Any]) -> None:
        with self.paths.tombstones_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
