from __future__ import annotations

from memoryplane.paths import MemoryPlanePaths
from memoryplane.services.search_service import SearchService


class EvalService:
    def __init__(self, paths: MemoryPlanePaths):
        self.search = SearchService(paths)

    def evaluate(self, *, queries: list[str], topk: int) -> dict[str, object]:
        query_results: list[dict[str, object]] = []
        total_results = 0
        for query in queries:
            search_result = self.search.search(query=query, topk=topk)
            result_count = len(search_result["results"])
            total_results += result_count
            query_results.append(
                {
                    "query": query,
                    "topk": topk,
                    "result_count": result_count,
                    "results": search_result["results"],
                }
            )
        aggregate = {
            "query_count": len(queries),
            "total_results": total_results,
            "average_results": total_results / len(queries) if queries else 0.0,
        }
        return {"queries": query_results, "aggregate": aggregate}
