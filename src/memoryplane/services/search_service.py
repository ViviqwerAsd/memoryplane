from __future__ import annotations

from typing import Any

from memoryplane.models import MemoryRecord
from memoryplane.paths import MemoryPlanePaths
from memoryplane.storage import CanonicalStore, SearchIndexStore


class SearchService:
    def __init__(self, paths: MemoryPlanePaths):
        self.paths = paths
        self.canonical = CanonicalStore(paths)
        self.index = SearchIndexStore(paths)

    def search(
        self,
        *,
        query: str,
        topk: int = 5,
        space: str | None = None,
        entity: str | None = None,
        types: list[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        sort_by: str = "relevance",
        explain: bool = False,
    ) -> dict[str, Any]:
        memories = self.canonical.list_memories()
        filtered = [
            memory
            for memory in memories
            if self._matches_filters(memory, space=space, entity=entity, types=types, after=after, before=before)
        ]

        results: list[dict[str, Any]] = []
        for memory in filtered:
            score, matched_terms = self.index.score(query, memory)
            if query and score <= 0:
                continue
            record: dict[str, Any] = {
                "memory": memory.model_dump(mode="json"),
                "score": round(score, 6),
            }
            if explain:
                record["matched_terms"] = matched_terms
            results.append(record)

        if sort_by in {"timestamp", "time"}:
            results.sort(key=lambda item: (item["memory"]["timestamp"], item["score"]), reverse=True)
        elif sort_by == "confidence":
            results.sort(
                key=lambda item: (item["memory"]["confidence"], item["score"], item["memory"]["timestamp"]),
                reverse=True,
            )
        else:
            results.sort(key=lambda item: (item["score"], item["memory"]["timestamp"]), reverse=True)
        return {
            "query": query,
            "limit": topk,
            "sort_by": sort_by,
            "results": results[:topk],
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
