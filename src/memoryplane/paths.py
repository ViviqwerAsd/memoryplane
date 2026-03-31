from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MemoryPlanePaths:
    root: Path

    @property
    def memoryplane_root(self) -> Path:
        return self.root / ".memoryplane"

    @property
    def config_file(self) -> Path:
        return self.memoryplane_root / "config.json"

    @property
    def store_dir(self) -> Path:
        return self.memoryplane_root / "store"

    @property
    def memories_file(self) -> Path:
        return self.store_dir / "memories.jsonl"

    @property
    def revisions_file(self) -> Path:
        return self.store_dir / "revisions.jsonl"

    @property
    def tombstones_file(self) -> Path:
        return self.store_dir / "tombstones.jsonl"

    @property
    def candidates_dir(self) -> Path:
        return self.memoryplane_root / "candidates"

    @property
    def indexes_dir(self) -> Path:
        return self.memoryplane_root / "indexes"

    @property
    def search_cache_file(self) -> Path:
        return self.indexes_dir / "search_cache.json"

    @property
    def projections_dir(self) -> Path:
        return self.memoryplane_root / "projections"

    @property
    def logs_dir(self) -> Path:
        return self.memoryplane_root / "logs"

    @property
    def operations_log_file(self) -> Path:
        return self.logs_dir / "operations.jsonl"

    def candidate_file(self, candidate_id: str) -> Path:
        return self.candidates_dir / f"{candidate_id}.json"

    def projection_file(self, space: str, memory_id: str) -> Path:
        return self.projections_dir / space / f"{memory_id}.json"
