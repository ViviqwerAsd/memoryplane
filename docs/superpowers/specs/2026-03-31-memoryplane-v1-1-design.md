# memoryplane v1.1 Design Spec

Date: 2026-03-31
Status: Approved design, pending implementation

## Overview

This document defines the next iteration of the local memory control plane previously prototyped as `memoryplane`.

The project is renamed to `memoryplane`.

This version introduces three major improvements:

- full product and package rename from `memoryplane` to `memoryplane`
- a first-class Python SDK for agent/runtime integration
- batch operations and stronger search filtering/sorting

The storage model remains local-first and file-based:

- committed memories in JSONL
- reviewable candidates as individual JSON files
- derived readable projections
- lexical retrieval as the default search mode

## Rename Goals

The old name must be removed completely from the codebase.

The new primary identity is:

- project name: `memoryplane`
- Python package: `memoryplane`
- CLI command: `memoryplane`
- SDK import: `from memoryplane import MemoryPlaneClient`

No compatibility layer or alias is retained in this iteration.

## Scope

This iteration includes:

- full rename to `memoryplane`
- Python SDK
- batch write
- batch search
- stronger search filters
- configurable result sorting
- updated docs, tests, and local skill

This iteration does not include:

- semantic retrieval
- embeddings
- graph links between memories
- importance/feedback system
- time decay scoring
- patch/update lifecycle beyond the existing candidate-based workflow

## Architecture

The layered shape remains:

1. CLI
2. SDK facade
3. application and service layer
4. storage layer

The SDK is thin and directly composes the same service layer used by the CLI.

This keeps logic centralized while offering both human-facing and runtime-facing interfaces.

## SDK Design

Primary entrypoint:

```python
from memoryplane import MemoryPlaneClient
```

Constructor:

```python
client = MemoryPlaneClient(root="./data")
```

Primary methods:

- `init()`
- `write(...)`
- `commit(candidate_id)`
- `reject(candidate_id)`
- `inspect(memory_id)`
- `search(...)`
- `pack(...)`
- `merge(...)`
- `distill(...)`
- `eval(...)`
- `write_batch(items)`
- `search_batch(queries, ...)`

### SDK return shape

SDK methods return Python dictionaries mirroring the JSON payload `data` section where possible.

Errors are raised as Python exceptions with stable error codes.

## Batch Operations

### Batch write

Input is a list of write payloads. Each item is validated independently and returns its own result.

The first version is non-transactional by design.

Behavior:

- one bad item does not invalidate the whole batch
- each item returns either a candidate or a committed memory result
- the batch response includes per-item success and failure details

### Batch search

Input is a list of queries plus shared filters.

Behavior:

- each query executes independently
- output is a list of search results preserving input order

## Search Improvements

Current lexical ranking remains the default.

This iteration adds:

- `limit`
- `sort_by` with `relevance` and `timestamp`
- multiple `type` filters
- existing `space`, `entity`, `after`, `before`

CLI behavior and SDK behavior must match.

### Sorting

- `sort_by=relevance`: score descending, then timestamp descending
- `sort_by=timestamp`: timestamp descending, then score descending

## File Layout

The package root changes from `src/memoryplane/` to `src/memoryplane/`.

New file:

- `src/memoryplane/client.py`

The skill also changes from `skills/using-memoryplane/` to `skills/using-memoryplane/`.

## Testing Strategy

Add tests for:

- renamed CLI entrypoint/module
- SDK write/search/pack flow
- batch write partial success behavior
- batch search ordering and filtering
- multi-type filtering
- timestamp sorting

All previous behavior tests must continue to pass after rename and refactor.

## Final Recommendation

Implement `memoryplane v1.1` as a full rename plus runtime-facing API improvement release:

- rename everything cleanly
- add SDK facade without duplicating business logic
- add batch operations
- strengthen lexical search filters and sorting

This keeps the system coherent while materially improving agent ergonomics.
