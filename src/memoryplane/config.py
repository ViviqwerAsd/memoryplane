from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemctlConfig:
    schema_version: str = "v1"
    search_algorithm: str = "bm25-lite"


DEFAULT_CONFIG = MemctlConfig()
