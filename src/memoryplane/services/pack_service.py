from __future__ import annotations

from memoryplane.paths import MemoryPlanePaths
from memoryplane.services.search_service import SearchService


class PackService:
    def __init__(self, paths: MemoryPlanePaths):
        self.search = SearchService(paths)

    def pack(self, *, query: str, budget: int, format: str = "prompt", topk: int = 5) -> dict[str, object]:
        search_result = self.search.search(query=query, topk=topk)
        lines = [f"Query: {query}"]
        seen_contents: set[str] = set()
        for result in search_result["results"]:
            content = result["memory"]["content"]
            if content in seen_contents:
                continue
            candidate = f"- {result['memory']['memory_id']}: {content}"
            joined = "\n".join(lines + [candidate])
            if len(joined) > budget:
                break
            seen_contents.add(content)
            lines.append(candidate)
        packed_text = "\n".join(lines)[:budget]
        return {
            "query": query,
            "budget": budget,
            "format": format,
            "packed_text": packed_text,
            "results": search_result["results"],
        }
