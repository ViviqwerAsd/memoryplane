from __future__ import annotations

import json

from memoryplane.models import MemoryRecord
from memoryplane.paths import MemoryPlanePaths


class ProjectionStore:
    def __init__(self, paths: MemoryPlanePaths):
        self.paths = paths

    def write_memory(self, memory: MemoryRecord) -> None:
        path = self.paths.projection_file(memory.space, memory.memory_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(memory.model_dump(mode="json"), indent=2))
