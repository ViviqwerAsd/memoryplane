from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from memoryplane.models import DURABILITY_VALUES, ENTITY_TYPES, MEMORY_TYPES, SOURCE_KINDS
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
from memoryplane.utils.json_output import error_response, success_response
from memoryplane.utils.validation import (
    InputValidationError,
    friendly_missing_fields_message,
    format_allowed_values,
    validate_sort_by,
    validate_type_filters,
)


app = typer.Typer(add_completion=False)


def _emit(command: str, *, data: dict | None = None, json_output: bool = False) -> None:
    if json_output:
        typer.echo(success_response(command, data))
        raise typer.Exit(code=0)
    typer.echo(f"{command}: ok")
    raise typer.Exit(code=0)


def _fail(command: str, code: str, message: str, exit_code: int, *, json_output: bool = False) -> None:
    if json_output:
        typer.echo(error_response(command, code, message))
        raise typer.Exit(code=exit_code)
    typer.echo(f"{command}: {code} {message}")
    raise typer.Exit(code=exit_code)


def _paths(root: Path) -> MemoryPlanePaths:
    return MemoryPlanePaths(root=root.resolve())


RootOption = Annotated[Path, typer.Option("--root", file_okay=False, dir_okay=True, writable=True, resolve_path=True)]
JsonOption = Annotated[bool, typer.Option("--json")]


@app.command()
def init(root: RootOption = Path("."), json_output: JsonOption = False) -> None:
    data = InitService(_paths(root)).run()
    _emit("init", data=data, json_output=json_output)


@app.command()
def write(
    root: RootOption = Path("."),
    type: Annotated[
        str,
        typer.Option("--type", help=f"Memory type. Allowed: {format_allowed_values(MEMORY_TYPES)}"),
    ] = ...,
    space: Annotated[str, typer.Option("--space", help="Logical namespace for the memory, for example preference or event.")] = ...,
    entity: Annotated[
        str,
        typer.Option("--entity", help=f"Entity owner for the memory. Allowed: {format_allowed_values(ENTITY_TYPES)}"),
    ] = ...,
    content: Annotated[str, typer.Option("--content", help="Natural-language memory content to store.")] = ...,
    source: Annotated[
        str,
        typer.Option(
            "--source",
            help=f"Origin in kind:session_id format. Allowed kinds: {format_allowed_values(SOURCE_KINDS)}",
        ),
    ] = ...,
    durability: Annotated[
        str,
        typer.Option("--durability", help=f"Write mode. Allowed: {format_allowed_values(DURABILITY_VALUES)}"),
    ] = "tentative",
    confidence: Annotated[float, typer.Option("--confidence", help="Confidence score between 0 and 1.")] = 1.0,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Create a candidate without committing it.")] = False,
    commit: Annotated[
        bool,
        typer.Option("--commit", help="Create and immediately commit a durable write in one step."),
    ] = False,
    json_output: JsonOption = False,
) -> None:
    service = WriteService(_paths(root))
    try:
        _, data = service.write(
            type=type,
            space=space,
            entity=entity,
            content=content,
            source=source,
            durability=durability,
            confidence=confidence,
            dry_run=dry_run,
            commit=commit,
        )
    except InputValidationError as exc:
        _fail("write", exc.code, exc.message, 1, json_output=json_output)
    except ValueError as exc:
        if str(exc) == "DRY_RUN_REQUIRED":
            _fail("write", "DRY_RUN_REQUIRED", "Durable writes require --dry-run first", 3, json_output=json_output)
        _fail("write", "WRITE_ERROR", str(exc), 1, json_output=json_output)
    _emit("write", data=data, json_output=json_output)


@app.command()
def commit(
    candidate_id: str,
    root: RootOption = Path("."),
    json_output: JsonOption = False,
) -> None:
    service = WriteService(_paths(root))
    try:
        memory = service.commit(candidate_id)
    except FileNotFoundError:
        _fail("commit", "CANDIDATE_NOT_FOUND", f"Candidate {candidate_id} does not exist", 1, json_output=json_output)
    except ValueError as exc:
        _fail("commit", str(exc), "Candidate cannot be committed", 1, json_output=json_output)
    _emit("commit", data={"memory": memory.model_dump(mode="json")}, json_output=json_output)


@app.command()
def reject(
    candidate_id: str,
    root: RootOption = Path("."),
    json_output: JsonOption = False,
) -> None:
    service = WriteService(_paths(root))
    try:
        candidate = service.reject(candidate_id)
    except FileNotFoundError:
        _fail("reject", "CANDIDATE_NOT_FOUND", f"Candidate {candidate_id} does not exist", 1, json_output=json_output)
    _emit("reject", data={"candidate": candidate.model_dump(mode="json")}, json_output=json_output)


@app.command()
def search(
    root: RootOption = Path("."),
    query: Annotated[str, typer.Option("--query", help="Search query. Search is lexical BM25-lite, not semantic embeddings.")] = "",
    limit: Annotated[int, typer.Option("--limit", help="Maximum number of results to return.")] = 5,
    space: Annotated[str | None, typer.Option("--space", help="Optional space filter.")] = None,
    entity: Annotated[str | None, typer.Option("--entity", help="Optional entity filter.")] = None,
    type: Annotated[list[str], typer.Option("--type", help="Repeat to filter by one or more memory types.")] = [],
    after: Annotated[str | None, typer.Option("--after")] = None,
    before: Annotated[str | None, typer.Option("--before")] = None,
    sort_by: Annotated[str, typer.Option("--sort-by", help="Sort by relevance or timestamp.")] = "relevance",
    explain: Annotated[bool, typer.Option("--explain", help="Include matched lexical terms in each result.")] = False,
    json_output: JsonOption = False,
) -> None:
    try:
        validate_type_filters(type)
        validate_sort_by(value=sort_by, allowed=("relevance", "timestamp"))
    except InputValidationError as exc:
        _fail("search", exc.code, exc.message, 1, json_output=json_output)
    data = SearchService(_paths(root)).search(
        query=query,
        topk=limit,
        space=space,
        entity=entity,
        types=type or None,
        after=after,
        before=before,
        sort_by=sort_by,
        explain=explain,
    )
    _emit("search", data=data, json_output=json_output)


@app.command("list")
def list_memories(
    root: RootOption = Path("."),
    limit: Annotated[int, typer.Option("--limit", help="Maximum number of memories to return.")] = 20,
    space: Annotated[str | None, typer.Option("--space", help="Optional space filter.")] = None,
    entity: Annotated[str | None, typer.Option("--entity", help="Optional entity filter.")] = None,
    type: Annotated[list[str], typer.Option("--type", help="Repeat to filter by one or more memory types.")] = [],
    after: Annotated[str | None, typer.Option("--after")] = None,
    before: Annotated[str | None, typer.Option("--before")] = None,
    json_output: JsonOption = False,
) -> None:
    try:
        validate_type_filters(type)
    except InputValidationError as exc:
        _fail("list", exc.code, exc.message, 1, json_output=json_output)
    data = CatalogService(_paths(root)).list_memories(
        limit=limit,
        space=space,
        entity=entity,
        types=type or None,
        after=after,
        before=before,
    )
    _emit("list", data=data, json_output=json_output)


@app.command()
def stats(root: RootOption = Path("."), json_output: JsonOption = False) -> None:
    data = CatalogService(_paths(root)).stats()
    _emit("stats", data=data, json_output=json_output)


@app.command()
def pack(
    root: RootOption = Path("."),
    query: Annotated[str, typer.Option("--query")] = "",
    budget: Annotated[int, typer.Option("--budget")] = 1000,
    format: Annotated[str, typer.Option("--format")] = "prompt",
    topk: Annotated[int, typer.Option("--topk")] = 5,
    json_output: JsonOption = False,
) -> None:
    data = PackService(_paths(root)).pack(query=query, budget=budget, format=format, topk=topk)
    _emit("pack", data=data, json_output=json_output)


@app.command()
def inspect(
    memory_id: str,
    root: RootOption = Path("."),
    json_output: JsonOption = False,
) -> None:
    data = InspectService(_paths(root)).inspect(memory_id)
    if data is None:
        _fail("inspect", "MEMORY_NOT_FOUND", f"Memory {memory_id} does not exist", 1, json_output=json_output)
    _emit("inspect", data=data, json_output=json_output)


@app.command()
def merge(
    memory_id_a: str,
    memory_id_b: str,
    root: RootOption = Path("."),
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    json_output: JsonOption = False,
) -> None:
    service = MergeService(_paths(root))
    try:
        data = service.merge(memory_id_a, memory_id_b, dry_run=dry_run)
    except ValueError:
        _fail("merge", "DRY_RUN_REQUIRED", "Merge requires --dry-run first", 3, json_output=json_output)
    except FileNotFoundError:
        _fail("merge", "MEMORY_NOT_FOUND", "One or more memories do not exist", 1, json_output=json_output)
    _emit("merge", data=data, json_output=json_output)


@app.command()
def distill(
    root: RootOption = Path("."),
    window: Annotated[str, typer.Option("--window")] = "7d",
    into: Annotated[str, typer.Option("--into")] = "summary",
    json_output: JsonOption = False,
) -> None:
    try:
        data = DistillService(_paths(root)).distill(window=window, into=into)
    except ValueError as exc:
        _fail("distill", "INVALID_WINDOW", str(exc), 1, json_output=json_output)
    _emit("distill", data=data, json_output=json_output)


@app.command()
def eval(
    root: RootOption = Path("."),
    query: Annotated[list[str], typer.Option("--query")] = [],
    topk: Annotated[int, typer.Option("--topk")] = 5,
    json_output: JsonOption = False,
) -> None:
    data = EvalService(_paths(root)).evaluate(queries=query, topk=topk)
    _emit("eval", data=data, json_output=json_output)


@app.command("write-batch")
def write_batch(
    root: RootOption = Path("."),
    file: Annotated[Path, typer.Option("--file", exists=True, dir_okay=False, resolve_path=True)] = ...,
    json_output: JsonOption = False,
) -> None:
    items = json.loads(file.read_text())
    service = WriteService(_paths(root))
    results: list[dict[str, object]] = []
    for item in items:
        try:
            _, data = service.write(**item)
            results.append({"ok": True, "result": data})
        except InputValidationError as exc:
            results.append({"ok": False, "error": {"code": exc.code, "message": exc.message}})
        except TypeError as exc:
            results.append(
                {
                    "ok": False,
                    "error": {"code": "BATCH_ITEM_FAILED", "message": friendly_missing_fields_message(exc)},
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "error": {"code": "BATCH_ITEM_FAILED", "message": str(exc)}})
    _emit("write-batch", data={"results": results}, json_output=json_output)


@app.command("search-batch")
def search_batch(
    root: RootOption = Path("."),
    file: Annotated[Path, typer.Option("--file", exists=True, dir_okay=False, resolve_path=True)] = ...,
    limit: Annotated[int, typer.Option("--limit")] = 5,
    space: Annotated[str | None, typer.Option("--space")] = None,
    entity: Annotated[str | None, typer.Option("--entity")] = None,
    type: Annotated[list[str], typer.Option("--type", help="Repeat to filter by one or more memory types.")] = [],
    after: Annotated[str | None, typer.Option("--after")] = None,
    before: Annotated[str | None, typer.Option("--before")] = None,
    sort_by: Annotated[str, typer.Option("--sort-by", help="Sort by relevance or timestamp.")] = "relevance",
    json_output: JsonOption = False,
) -> None:
    try:
        validate_type_filters(type)
        validate_sort_by(value=sort_by, allowed=("relevance", "timestamp"))
    except InputValidationError as exc:
        _fail("search-batch", exc.code, exc.message, 1, json_output=json_output)
    queries = [line.strip() for line in file.read_text().splitlines() if line.strip()]
    service = SearchService(_paths(root))
    results = [
        service.search(
            query=query,
            topk=limit,
            space=space,
            entity=entity,
            types=type or None,
            after=after,
            before=before,
            sort_by=sort_by,
        )
        for query in queries
    ]
    _emit("search-batch", data={"queries": results}, json_output=json_output)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
