from __future__ import annotations

import csv
import errno
import json
import os
from pathlib import Path
import sys
from typing import Annotated

import click
import typer

from memoryplane.config_runtime import resolve_json_output, resolve_root
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
    with_fix,
)
from memoryplane.utils.text import parse_recent_to_after


class AgentTyperGroup(typer.core.TyperGroup):
    def _format_click_exception(self, exc: click.ClickException) -> str:
        if isinstance(exc, click.MissingParameter):
            param = exc.param
            if param is not None and getattr(param, "opts", None):
                target = f"{param.opts[0]} <value>"
            elif param is not None and getattr(param, "name", None):
                target = f"{param.name} <value>"
            else:
                target = "the missing required parameter"
            return with_fix(exc.format_message(), f"provide {target} and rerun")
        if isinstance(exc, click.NoSuchOption):
            return with_fix(exc.format_message(), "run --help to inspect the supported options")
        if isinstance(exc, click.BadParameter):
            return with_fix(exc.format_message(), "check the parameter value and rerun")
        return exc.format_message()

    def main(
        self,
        args=None,
        prog_name=None,
        complete_var=None,
        standalone_mode=True,
        windows_expand_args=True,
        **extra,
    ):
        if args is None:
            args = sys.argv[1:]
            if os.name == "nt" and windows_expand_args:
                args = click.utils._expand_args(args)
        else:
            args = list(args)

        if prog_name is None:
            prog_name = click.core._detect_program_name()

        self._main_shell_completion(extra, prog_name, complete_var)

        try:
            try:
                with self.make_context(prog_name, args, **extra) as ctx:
                    rv = self.invoke(ctx)
                    if not standalone_mode:
                        return rv
                    ctx.exit()
            except (EOFError, KeyboardInterrupt) as exc:
                click.echo(file=sys.stderr)
                raise click.Abort() from exc
            except click.ClickException as exc:
                if not standalone_mode:
                    raise
                click.echo(self._format_click_exception(exc), err=True)
                sys.exit(exc.exit_code)
            except OSError as exc:
                if exc.errno == errno.EPIPE:
                    sys.stdout = click.utils.PacifyFlushWrapper(sys.stdout)
                    sys.stderr = click.utils.PacifyFlushWrapper(sys.stderr)
                    sys.exit(1)
                raise
        except click.exceptions.Exit as exc:
            if standalone_mode:
                sys.exit(exc.exit_code)
            return exc.exit_code
        except click.Abort:
            if not standalone_mode:
                raise
            click.echo("Aborted!", err=True)
            sys.exit(1)


app = typer.Typer(add_completion=False, cls=AgentTyperGroup)


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


RootOption = Annotated[Path | None, typer.Option("--root", file_okay=False, dir_okay=True, writable=True, resolve_path=True)]
JsonOption = Annotated[bool | None, typer.Option("--json/--no-json")]


def _resolved_root(root: Path | None) -> Path:
    return resolve_root(root)


def _resolved_json(json_output: bool | None) -> bool:
    return resolve_json_output(json_output)


def _paths(root: Path | None) -> MemoryPlanePaths:
    return MemoryPlanePaths(root=_resolved_root(root))


def _template_items() -> list[dict[str, object]]:
    return [
        {
            "type": "preference",
            "space": "preference",
            "entity": "user",
            "content": "User prefers concise answers",
            "source": "chat:sess_001",
            "durability": "durable",
            "dry_run": True,
        },
        {
            "type": "event",
            "space": "event",
            "entity": "project",
            "content": "Kickoff completed",
            "source": "tool:job_42",
            "durability": "durable",
            "commit": True,
            "confidence": 0.9,
        },
    ]


def _csv_items(file: Path) -> list[dict[str, object]]:
    def parse_value(key: str, value: str) -> object:
        cleaned = value.strip()
        if cleaned == "":
            return ""
        if key in {"dry_run", "commit"}:
            return cleaned.lower() in {"1", "true", "yes", "on"}
        if key == "confidence":
            return float(cleaned)
        return cleaned

    with file.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            {key: parse_value(key, value) for key, value in row.items() if key and value is not None and value != ""}
            for row in reader
        ]


def _emit_list_text(data: dict[str, object], *, full: bool) -> None:
    results = data.get("results", [])
    if not isinstance(results, list):
        typer.echo("list: ok")
        raise typer.Exit(code=0)
    if full:
        typer.echo(json.dumps(results, indent=2))
        raise typer.Exit(code=0)
    for item in results:
        if not isinstance(item, dict):
            continue
        typer.echo(
            " | ".join(
                [
                    str(item.get("memory_id", "")),
                    str(item.get("type", "")),
                    str(item.get("timestamp", "")),
                    str(item.get("content_preview", "")),
                ]
            )
        )
    raise typer.Exit(code=0)


@app.command()
def init(root: RootOption = None, json_output: JsonOption = None) -> None:
    resolved_json = _resolved_json(json_output)
    data = InitService(_paths(root)).run()
    _emit("init", data=data, json_output=resolved_json)


@app.command()
def write(
    root: RootOption = None,
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
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
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
        _fail("write", exc.code, exc.message, 1, json_output=resolved_json)
    except ValueError as exc:
        if str(exc) == "DRY_RUN_REQUIRED":
            _fail(
                "write",
                "DRY_RUN_REQUIRED",
                with_fix("Durable writes require --dry-run first", "add --dry-run for proposal flow or use --commit for one-step commit"),
                3,
                json_output=resolved_json,
            )
        _fail("write", "WRITE_ERROR", str(exc), 1, json_output=resolved_json)
    _emit("write", data=data, json_output=resolved_json)


@app.command()
def commit(
    candidate_id: str,
    root: RootOption = None,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    service = WriteService(_paths(root))
    try:
        memory = service.commit(candidate_id)
    except FileNotFoundError:
        _fail(
            "commit",
            "CANDIDATE_NOT_FOUND",
            with_fix(f"Candidate {candidate_id} does not exist", "run write --dry-run first or use a valid candidate_id"),
            1,
            json_output=resolved_json,
        )
    except ValueError as exc:
        _fail("commit", str(exc), with_fix("Candidate cannot be committed", "check candidate status before committing"), 1, json_output=resolved_json)
    _emit("commit", data={"memory": memory.model_dump(mode="json")}, json_output=resolved_json)


@app.command()
def reject(
    candidate_id: str,
    root: RootOption = None,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    service = WriteService(_paths(root))
    try:
        candidate = service.reject(candidate_id)
    except FileNotFoundError:
        _fail(
            "reject",
            "CANDIDATE_NOT_FOUND",
            with_fix(f"Candidate {candidate_id} does not exist", "use a valid candidate_id from write --dry-run"),
            1,
            json_output=resolved_json,
        )
    _emit("reject", data={"candidate": candidate.model_dump(mode="json")}, json_output=resolved_json)


@app.command()
def search(
    root: RootOption = None,
    query: Annotated[str, typer.Option("--query", help="Search query. Search is lexical BM25-lite, not semantic embeddings.")] = "",
    limit: Annotated[int, typer.Option("--limit", help="Maximum number of results to return.")] = 5,
    space: Annotated[str | None, typer.Option("--space", help="Optional space filter.")] = None,
    entity: Annotated[str | None, typer.Option("--entity", help="Optional entity filter.")] = None,
    type: Annotated[list[str], typer.Option("--type", help="Repeat to filter by one or more memory types.")] = [],
    after: Annotated[str | None, typer.Option("--after")] = None,
    before: Annotated[str | None, typer.Option("--before")] = None,
    sort_by: Annotated[str, typer.Option("--sort-by", help="Sort by relevance, time, timestamp, or confidence.")] = "relevance",
    explain: Annotated[bool, typer.Option("--explain", help="Include matched lexical terms in each result.")] = False,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    try:
        validate_type_filters(type)
        validate_sort_by(value=sort_by, allowed=("relevance", "time", "timestamp", "confidence"))
    except InputValidationError as exc:
        _fail("search", exc.code, exc.message, 1, json_output=resolved_json)
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
    _emit("search", data=data, json_output=resolved_json)


@app.command("list")
def list_memories(
    root: RootOption = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum number of memories to return.")] = 20,
    space: Annotated[str | None, typer.Option("--space", help="Optional space filter.")] = None,
    entity: Annotated[str | None, typer.Option("--entity", help="Optional entity filter.")] = None,
    type: Annotated[list[str], typer.Option("--type", help="Repeat to filter by one or more memory types.")] = [],
    after: Annotated[str | None, typer.Option("--after")] = None,
    before: Annotated[str | None, typer.Option("--before")] = None,
    recent: Annotated[str | None, typer.Option("--recent", help="Quick recent filter such as 1h, 1d, or 7d.")] = None,
    compact: Annotated[bool, typer.Option("--compact", help="Return compact records. This is the default mode.")] = False,
    full: Annotated[bool, typer.Option("--full", help="Return full memory objects instead of compact records.")] = False,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    try:
        validate_type_filters(type)
        if compact and full:
            raise InputValidationError("INVALID_LIST_MODE", with_fix("--compact and --full cannot be used together", "pick one output mode"))
        if recent:
            after = parse_recent_to_after(recent)
    except ValueError:
        _fail("list", "INVALID_RECENT", with_fix("Unsupported recent format", "use values like 1h, 1d, or 7d"), 1, json_output=resolved_json)
    except InputValidationError as exc:
        _fail("list", exc.code, exc.message, 1, json_output=resolved_json)
    data = CatalogService(_paths(root)).list_memories(
        limit=limit,
        space=space,
        entity=entity,
        types=type or None,
        after=after,
        before=before,
        full=full,
    )
    if resolved_json:
        _emit("list", data=data, json_output=True)
    _emit_list_text(data, full=full)


@app.command()
def stats(root: RootOption = None, json_output: JsonOption = None) -> None:
    resolved_json = _resolved_json(json_output)
    data = CatalogService(_paths(root)).stats()
    _emit("stats", data=data, json_output=resolved_json)


@app.command()
def pack(
    root: RootOption = None,
    query: Annotated[str, typer.Option("--query")] = "",
    budget: Annotated[int, typer.Option("--budget")] = 1000,
    format: Annotated[str, typer.Option("--format")] = "prompt",
    topk: Annotated[int, typer.Option("--topk")] = 5,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    data = PackService(_paths(root)).pack(query=query, budget=budget, format=format, topk=topk)
    _emit("pack", data=data, json_output=resolved_json)


@app.command()
def inspect(
    memory_id: str,
    root: RootOption = None,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    data = InspectService(_paths(root)).inspect(memory_id)
    if data is None:
        _fail(
            "inspect",
            "MEMORY_NOT_FOUND",
            with_fix(f"Memory {memory_id} does not exist", "run list or search to find a valid memory_id"),
            1,
            json_output=resolved_json,
        )
    _emit("inspect", data=data, json_output=resolved_json)


@app.command()
def merge(
    memory_id_a: str,
    memory_id_b: str,
    root: RootOption = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    service = MergeService(_paths(root))
    try:
        data = service.merge(memory_id_a, memory_id_b, dry_run=dry_run)
    except ValueError:
        _fail("merge", "DRY_RUN_REQUIRED", with_fix("Merge requires --dry-run first", "add --dry-run to preview the candidate"), 3, json_output=resolved_json)
    except FileNotFoundError:
        _fail("merge", "MEMORY_NOT_FOUND", with_fix("One or more memories do not exist", "run list or search to find valid memory ids"), 1, json_output=resolved_json)
    _emit("merge", data=data, json_output=resolved_json)


@app.command()
def distill(
    root: RootOption = None,
    window: Annotated[str, typer.Option("--window")] = "7d",
    into: Annotated[str, typer.Option("--into")] = "summary",
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    try:
        data = DistillService(_paths(root)).distill(window=window, into=into)
    except ValueError as exc:
        _fail("distill", "INVALID_WINDOW", with_fix(str(exc), "use a window like 7d"), 1, json_output=resolved_json)
    _emit("distill", data=data, json_output=resolved_json)


@app.command()
def eval(
    root: RootOption = None,
    query: Annotated[list[str], typer.Option("--query")] = [],
    topk: Annotated[int, typer.Option("--topk")] = 5,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    data = EvalService(_paths(root)).evaluate(queries=query, topk=topk)
    _emit("eval", data=data, json_output=resolved_json)


@app.command("write-batch")
def write_batch(
    root: RootOption = None,
    file: Annotated[Path | None, typer.Option("--file", exists=True, dir_okay=False, resolve_path=True)] = None,
    csv_file: Annotated[Path | None, typer.Option("--csv", exists=True, dir_okay=False, resolve_path=True)] = None,
    template: Annotated[bool, typer.Option("--template", help="Print a sample JSON batch payload and exit.")] = False,
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    selected_sources = sum(bool(value) for value in (file, csv_file, template))
    if selected_sources != 1:
        _fail(
            "write-batch",
            "INVALID_BATCH_INPUT",
            with_fix("Choose exactly one batch input source", "use one of --file, --csv, or --template"),
            1,
            json_output=resolved_json,
        )
    if template:
        template_payload = _template_items()
        typer.echo(json.dumps(template_payload, indent=2))
        raise typer.Exit(code=0)
    if csv_file is not None:
        items = _csv_items(csv_file)
    else:
        items = json.loads(file.read_text()) if file is not None else []
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
    _emit("write-batch", data={"results": results}, json_output=resolved_json)


@app.command("search-batch")
def search_batch(
    root: RootOption = None,
    file: Annotated[Path, typer.Option("--file", exists=True, dir_okay=False, resolve_path=True)] = ...,
    limit: Annotated[int, typer.Option("--limit")] = 5,
    space: Annotated[str | None, typer.Option("--space")] = None,
    entity: Annotated[str | None, typer.Option("--entity")] = None,
    type: Annotated[list[str], typer.Option("--type", help="Repeat to filter by one or more memory types.")] = [],
    after: Annotated[str | None, typer.Option("--after")] = None,
    before: Annotated[str | None, typer.Option("--before")] = None,
    sort_by: Annotated[str, typer.Option("--sort-by", help="Sort by relevance, time, timestamp, or confidence.")] = "relevance",
    json_output: JsonOption = None,
) -> None:
    resolved_json = _resolved_json(json_output)
    try:
        validate_type_filters(type)
        validate_sort_by(value=sort_by, allowed=("relevance", "time", "timestamp", "confidence"))
    except InputValidationError as exc:
        _fail("search-batch", exc.code, exc.message, 1, json_output=resolved_json)
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
    _emit("search-batch", data={"queries": results}, json_output=resolved_json)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
