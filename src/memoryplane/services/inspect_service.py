from __future__ import annotations

from memoryplane.paths import MemoryPlanePaths
from memoryplane.storage import CanonicalStore


class InspectService:
    def __init__(self, paths: MemoryPlanePaths):
        self.canonical = CanonicalStore(paths)

    def inspect(self, memory_id: str) -> dict[str, object] | None:
        memory = self.canonical.get_memory(memory_id)
        if memory is None:
            return None
        return {"memory": memory.model_dump(mode="json")}
