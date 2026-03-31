# memoryplane Design Spec

Date: 2026-03-31
Status: Approved design, pending implementation plan

## Overview

`memoryplane` is a local-first memory control plane for agents. It makes memory explicit, inspectable, auditable, and evolvable through a deterministic CLI and stable JSON output contract.

This MVP targets:

- explicit memory writes
- human-readable review before durable changes
- stable `--json` output for agent/runtime integration
- file-based storage using JSONL plus readable projections
- lightweight structured retrieval with metadata filtering and BM25/TF-IDF-style ranking

## Goals

### Agent-facing

- Explicit tool usage only
- Deterministic command behavior
- Stable `--json` contract as a first-class interface
- Token-efficient retrieval and packing

### Human-facing

- Inspectable files on disk
- Auditable write and revision flow
- Safe dry-run before durable changes
- Reversible operational model

### System-facing

- Incremental updates
- No full re-index on every write
- Storage abstraction that can evolve later
- Clear separation between retrieval, packing, and storage

### Research-facing

- Schema versioning
- Policy experimentation later without redesigning the CLI
- Basic evaluation hooks in the MVP

## MVP Scope

The MVP includes:

- `init`
- `write`
- `commit`
- `reject`
- `search`
- `pack`
- `inspect`
- `merge`
- `distill`
- `eval`

The MVP memory spaces are:

- `profile`
- `preference`
- `event`

Durability levels:

- `tentative`
- `durable`

Rule:

- all durable writes require a prior dry-run candidate

The MVP does not include:

- vector retrieval
- full hybrid retrieval
- schema mutation workflows
- physical deletion
- automatic session ingestion
- advanced lifecycle commands beyond what is needed to support the core loop

## Architecture

The system is organized into four layers:

1. `cli`
   - command parsing
   - human-readable output
   - stable `--json` output
   - exit code handling
2. `application`
   - command orchestration
   - policy enforcement
   - validation flow such as dry-run requirements
3. `engine`
   - memory domain logic
   - ranking, packing, merge, distill, eval behaviors
4. `storage`
   - JSONL canonical store
   - candidate JSON files
   - index cache
   - readable projections

This structure keeps the command surface stable while allowing later storage changes without breaking callers.

## Storage Design

The working directory root contains a `.memoryplane/` folder:

```text
.memoryplane/
  config.json
  store/
    memories.jsonl
    revisions.jsonl
    tombstones.jsonl
  candidates/
    cand_<id>.json
  indexes/
    search_cache.json
  projections/
    profile/
    preference/
    event/
  logs/
    operations.jsonl
```

### Canonical store

`store/memories.jsonl` is the source of truth for committed memories.

Reasons:

- append-friendly
- easy to audit
- simple to inspect
- compatible with later replay or migration workflows

### Candidates

Each proposed change is written to its own file under `candidates/`.

Reasons:

- easy human review
- easy rollback and rejection
- clean support for the two-phase write flow

### Revisions and tombstones

`revisions.jsonl` records mutation events such as merge and revise-like updates.

`tombstones.jsonl` records state transitions for deprecations or soft-delete semantics if needed later. The MVP does not expose physical delete.

### Projection

`projections/` contains readable filesystem views grouped by space. These are derived artifacts, not the source of truth.

### Search cache

`indexes/search_cache.json` stores lightweight search metadata such as normalized terms, term frequencies, and document lengths to avoid recomputing ranking state on every query.

## Memory Model

The canonical memory schema for MVP is:

```json
{
  "memory_id": "mem_xxx",
  "type": "preference",
  "space": "preference",
  "entity": "user",
  "content": "User prefers concise answers",
  "source": {
    "kind": "chat",
    "session_id": "sess_001",
    "turn_ids": ["turn_12"]
  },
  "timestamp": "2026-03-31T12:00:00Z",
  "confidence": 0.92,
  "durability": "tentative",
  "schema_version": "v1",
  "evidence_refs": [],
  "revision": 1,
  "status": "active"
}
```

### Field notes

- `space` is explicit to simplify filtering and projection
- `revision` supports future mutation history
- `status` starts with `active` and can later include `deprecated`, `deleted`, or `merged`
- provenance fields are mandatory for committed memories

## Command Design

### `init`

Creates the `.memoryplane/` directory structure and default config.

### `write`

Creates a candidate proposal. For durable content, `--dry-run` is mandatory.

Example:

```bash
memoryplane write \
  --type preference \
  --space preference \
  --entity user \
  --content "User prefers concise answers" \
  --source chat:sess_001 \
  --durability durable \
  --dry-run
```

Behavior:

1. Validate input
2. Build canonical memory payload
3. Wrap it in a candidate envelope
4. Save to `candidates/cand_<id>.json`
5. Return candidate details

### `commit`

Commits a previously created candidate into the canonical store.

Behavior:

1. Load candidate file
2. Re-run policy checks
3. Append memory to `memories.jsonl`
4. Update projection and search cache
5. Remove or archive candidate file
6. Append operation metadata to logs if enabled

### `reject`

Rejects a candidate and prevents it from entering the canonical store.

Behavior:

- move or mark candidate as rejected in a recoverable way

### `search`

Returns raw memory candidates with filtering and ranking.

Filters:

- `space`
- `entity`
- `type`
- `after`
- `before`
- `durability`
- active status only

Ranking:

- metadata filter first
- lightweight lexical scoring second
- sort by score and recency

### `pack`

Builds prompt-ready context from search results.

Behavior:

1. run `search`
2. deduplicate
3. prioritize by score and freshness
4. compress to the requested budget
5. emit prompt-friendly or JSON structured output

### `inspect`

Returns a full memory record and related state for a specific memory id.

### `merge`

Combines two memories into a new memory through a dry-run-first workflow.

Behavior:

1. inspect source memories
2. construct merged candidate
3. require review
4. commit merged memory
5. record prior memories as merged through revision state

### `distill`

Summarizes a selected time window or memory subset into a summary memory candidate. The MVP defaults to dry-run behavior for safety.

### `eval`

Runs retrieval or packing evaluation against a provided query set and emits a structured report. This is intentionally lightweight in the MVP.

## Two-Phase Write Contract

All durable writes follow:

`write --dry-run` -> human or agent review -> `commit`

Candidate file shape:

```json
{
  "candidate_id": "cand_001",
  "proposed_at": "2026-03-31T12:00:00Z",
  "operation": "write",
  "dry_run": true,
  "memory": {
    "memory_id": "mem_xxx",
    "type": "preference",
    "space": "preference",
    "entity": "user",
    "content": "User prefers concise answers",
    "source": {
      "kind": "chat",
      "session_id": "sess_001",
      "turn_ids": ["turn_12"]
    },
    "timestamp": "2026-03-31T12:00:00Z",
    "confidence": 0.92,
    "durability": "durable",
    "schema_version": "v1",
    "evidence_refs": [],
    "revision": 1,
    "status": "active"
  },
  "validation": {
    "ok": true,
    "warnings": []
  }
}
```

This lets both humans and runtimes inspect the exact payload that would be committed.

## Retrieval Pipeline

The MVP retrieval flow is:

1. candidate selection by metadata filter
2. lexical scoring using a simple BM25/TF-IDF-style ranking
3. sorting and top-k truncation
4. optional explanation output

The ranking implementation should be lightweight and local:

- normalized tokenization
- per-document term frequencies
- document lengths
- corpus document frequencies

No external search service is required.

## JSON Output Contract

All commands support `--json` and return a stable envelope.

Success:

```json
{
  "ok": true,
  "command": "search",
  "data": {},
  "warnings": [],
  "errors": []
}
```

Failure:

```json
{
  "ok": false,
  "command": "commit",
  "data": null,
  "warnings": [],
  "errors": [
    {
      "code": "CANDIDATE_NOT_FOUND",
      "message": "Candidate cand_001 does not exist"
    }
  ]
}
```

### Exit codes

- `0`: success
- `1`: user input or validation error
- `2`: storage or runtime failure
- `3`: policy rejection

## Implementation Stack

Recommended stack:

- Python 3.11+
- `typer` for CLI
- `pydantic` for schema validation
- `pytest` for tests
- standard library for file, JSON, path, datetime, and id generation

Suggested source tree:

```text
src/memoryplane/
  cli.py
  models.py
  config.py
  paths.py
  storage/
    canonical.py
    candidates.py
    projections.py
    index.py
  services/
    write_service.py
    search_service.py
    pack_service.py
    merge_service.py
    distill_service.py
    eval_service.py
  utils/
    json_output.py
    text.py
tests/
```

## Testing Strategy

The implementation should follow TDD.

Priority behavior tests:

- `init` creates the expected directory structure
- `write --dry-run` creates a candidate file
- durable `write` without dry-run is rejected
- `commit` promotes a candidate into `memories.jsonl`
- `search` applies filters and ranking
- `pack` respects budget limits
- `merge` follows the dry-run-first flow
- all commands return a stable `--json` envelope

Tests should focus on externally visible behavior rather than internal implementation details.

## Tradeoffs and Rationale

### Why JSONL as canonical store

- better append semantics than a single JSON object file
- easier auditability
- simpler future replay or migration

### Why candidates as individual JSON files

- best fit for explicit review and rollback
- easiest for humans to inspect
- matches the desired write-review-commit control plane

### Why not event sourcing for MVP

- event sourcing fits the long-term vision
- it would add complexity too early
- JSONL plus revision logs gives enough structure for the first version

### Why not per-memory JSON files as source of truth

- convenient for manual browsing
- less efficient and less coherent for append-heavy workflows
- harder to support ranking, compaction, and replay cleanly

## Open Future Extensions

Future versions can add:

- vector retrieval
- hybrid ranking
- lifecycle commands such as decay and expire
- schema mutation workflows
- richer evaluation benchmarks
- alternate canonical stores such as SQLite or DuckDB
- automatic session ingestion

## Final Recommendation

Build the MVP as a local Python CLI with:

- JSONL canonical store
- per-candidate JSON review files
- stable `--json` API surface
- lightweight lexical search
- explicit two-phase durable writes

This gives `memoryplane` a strong control-plane foundation without overbuilding the first version.
