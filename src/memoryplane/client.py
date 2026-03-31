from __future__ import annotations

from pathlib import Path
from typing import Any

from memoryplane.paths import MemoryPlanePaths
from memoryplane.services.catalog_service import CatalogService
from memoryplane.services.distill_service import DistillService
from memoryplane.services.eval_service import EvalService
from memoryplane.services.init_service import InitService
from memoryplane.services.inspect_service import InspectService
from memoryplane.services.merge_service import MergeService
from memoryplane.services.pack_service import PackService
from memoryplane.services.search_service import SearchService
from memoryplane.services.write_service import WriteService
from memoryplane.utils.validation import InputValidationError, friendly_missing_fields_message


class MemoryPlaneError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class MemoryPlaneClient:
    def __init__(self, root: str | Path):
        self.paths = MemoryPlanePaths(root=Path(root).resolve())

    def init(self) -> dict[str, object]:
        return InitService(self.paths).run()

    def write(self, **kwargs: Any) -> dict[str, object]:
        try:
            _, data = WriteService(self.paths).write(**kwargs)
            return data
        except InputValidationError as exc:
            raise MemoryPlaneError(exc.code, exc.message) from exc
        except Exception as exc:  # noqa: BLE001
            raise MemoryPlaneError("WRITE_FAILED", str(exc)) from exc

    def commit(self, candidate_id: str) -> dict[str, object]:
        try:
            memory = WriteService(self.paths).commit(candidate_id)
            return {"memory": memory.model_dump(mode="json")}
        except FileNotFoundError as exc:
            raise MemoryPlaneError("CANDIDATE_NOT_FOUND", f"Candidate {candidate_id} does not exist") from exc

    def reject(self, candidate_id: str) -> dict[str, object]:
        try:
            candidate = WriteService(self.paths).reject(candidate_id)
            return {"candidate": candidate.model_dump(mode="json")}
        except FileNotFoundError as exc:
            raise MemoryPlaneError("CANDIDATE_NOT_FOUND", f"Candidate {candidate_id} does not exist") from exc

    def inspect(self, memory_id: str) -> dict[str, object]:
        payload = InspectService(self.paths).inspect(memory_id)
        if payload is None:
            raise MemoryPlaneError("MEMORY_NOT_FOUND", f"Memory {memory_id} does not exist")
        return payload

    def search(
        self,
        *,
        query: str,
        limit: int = 5,
        space: str | None = None,
        entity: str | None = None,
        types: list[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        sort_by: str = "relevance",
        explain: bool = False,
    ) -> dict[str, object]:
        return SearchService(self.paths).search(
            query=query,
            topk=limit,
            space=space,
            entity=entity,
            types=types,
            after=after,
            before=before,
            sort_by=sort_by,
            explain=explain,
        )

    def pack(self, *, query: str, budget: int, format: str = "prompt", topk: int = 5) -> dict[str, object]:
        return PackService(self.paths).pack(query=query, budget=budget, format=format, topk=topk)

    def list(
        self,
        *,
        limit: int = 20,
        space: str | None = None,
        entity: str | None = None,
        types: list[str] | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> dict[str, object]:
        return CatalogService(self.paths).list_memories(
            limit=limit,
            space=space,
            entity=entity,
            types=types,
            after=after,
            before=before,
        )

    def stats(self) -> dict[str, object]:
        return CatalogService(self.paths).stats()

    def merge(self, memory_id_a: str, memory_id_b: str, *, dry_run: bool = False) -> dict[str, object]:
        return MergeService(self.paths).merge(memory_id_a, memory_id_b, dry_run=dry_run)

    def distill(self, *, window: str, into: str) -> dict[str, object]:
        return DistillService(self.paths).distill(window=window, into=into)

    def eval(self, *, queries: list[str], topk: int) -> dict[str, object]:
        return EvalService(self.paths).evaluate(queries=queries, topk=topk)

    def write_batch(self, items: list[dict[str, Any]]) -> dict[str, object]:
        results: list[dict[str, object]] = []
        for item in items:
            try:
                result = self.write(**item)
                results.append({"ok": True, "result": result})
            except MemoryPlaneError as exc:
                results.append({"ok": False, "error": {"code": "BATCH_ITEM_FAILED", "message": exc.message}})
            except TypeError as exc:
                results.append(
                    {
                        "ok": False,
                        "error": {"code": "BATCH_ITEM_FAILED", "message": friendly_missing_fields_message(exc)},
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append({"ok": False, "error": {"code": "BATCH_ITEM_FAILED", "message": str(exc)}})
        return {"results": results}

    def search_batch(
        self,
        queries: list[str],
        *,
        limit: int = 5,
        space: str | None = None,
        entity: str | None = None,
        types: list[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        sort_by: str = "relevance",
    ) -> dict[str, object]:
        results = [
            self.search(
                query=query,
                limit=limit,
                space=space,
                entity=entity,
                types=types,
                after=after,
                before=before,
                sort_by=sort_by,
            )
            for query in queries
        ]
        return {"queries": results}
