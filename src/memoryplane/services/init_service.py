from __future__ import annotations

import json

from memoryplane.config import DEFAULT_CONFIG
from memoryplane.paths import MemoryPlanePaths
from memoryplane.utils.text import utc_now


class InitService:
    def __init__(self, paths: MemoryPlanePaths):
        self.paths = paths

    def run(self) -> dict[str, object]:
        self.paths.memoryplane_root.mkdir(parents=True, exist_ok=True)
        self.paths.store_dir.mkdir(parents=True, exist_ok=True)
        self.paths.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.paths.indexes_dir.mkdir(parents=True, exist_ok=True)
        self.paths.logs_dir.mkdir(parents=True, exist_ok=True)
        for space in ("profile", "preference", "event"):
            (self.paths.projections_dir / space).mkdir(parents=True, exist_ok=True)

        self.paths.config_file.write_text(
            json.dumps(
                {
                    "schema_version": DEFAULT_CONFIG.schema_version,
                    "search_algorithm": DEFAULT_CONFIG.search_algorithm,
                    "created_at": utc_now(),
                },
                indent=2,
            )
        )
        for file_path, default in (
            (self.paths.memories_file, ""),
            (self.paths.revisions_file, ""),
            (self.paths.tombstones_file, ""),
            (
                self.paths.search_cache_file,
                json.dumps(
                    {
                        "version": 1,
                        "documents": {},
                        "doc_freq": {},
                        "avg_doc_length": 0.0,
                    },
                    indent=2,
                ),
            ),
            (self.paths.operations_log_file, ""),
        ):
            if not file_path.exists():
                file_path.write_text(default)

        return {
            "root": str(self.paths.root),
            "memoryplane_root": str(self.paths.memoryplane_root),
        }
