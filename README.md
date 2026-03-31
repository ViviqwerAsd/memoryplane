# memoryplane

Agent-first local memory CLI.

## Default Invocation

Preferred command:

```bash
memoryplane
```

Fallback from repo root:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli
```

If the console script is missing:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Default Resolution

Default values are resolved in this order:

1. CLI flags
2. Environment variables
3. `.memoryplane.conf`
4. Built-in defaults

Supported defaults:

- `root`
- `json`

Environment variables:

- `MEMORYPLANE_ROOT`
- `MEMORYPLANE_JSON`

Workspace config file: `.memoryplane.conf`

Example:

```json
{
  "root": "/tmp/memoryplane-demo",
  "json": true
}
```

This lets an agent omit repeated `--root` and `--json`.

## Rules

- Use `--json` or set `json=true` in `.memoryplane.conf` for agent workflows.
- Treat the CLI as the source of truth.
- Do not edit `.memoryplane/` files directly unless repairing storage manually.
- `search` is lexical BM25-lite search, not semantic vector search.
- Use `list` to browse what exists.
- Use `search` when query terms matter.

## Allowed Values

`type`:

- `preference`
- `profile`
- `entity`
- `event`
- `task`
- `procedure`
- `case`
- `pattern`
- `summary`
- `scratch`

`entity`:

- `user`
- `project`
- `system`
- `topic`

`durability`:

- `tentative`
- `durable`

`source` format:

- `kind:session_id`
- allowed `kind`: `chat`, `tool`, `system`
- examples: `chat:sess_001`, `tool:job_42`, `system:distill`

## Common Flows

Initialize:

```bash
memoryplane init
```

One-step durable write:

```bash
memoryplane write \
  --type preference \
  --space preference \
  --entity user \
  --content "User prefers concise answers" \
  --source chat:sess_001 \
  --durability durable \
  --commit
```

Proposal flow:

```bash
memoryplane write \
  --type preference \
  --space preference \
  --entity user \
  --content "User prefers concise answers" \
  --source chat:sess_001 \
  --durability durable \
  --dry-run \
  --json
```

Commit candidate:

```bash
memoryplane commit cand_xxx
```

Reject candidate:

```bash
memoryplane reject cand_xxx
```

## Retrieval

Compact browse is the default.

Compact list:

```bash
memoryplane list
```

Compact JSON list:

```bash
memoryplane list --json
```

Full records:

```bash
memoryplane list --full --json
```

Recent records:

```bash
memoryplane list --recent 1h
memoryplane list --recent 1d
memoryplane list --recent 7d
```

Search by relevance:

```bash
memoryplane search --query "concise answers" --json
```

Search by time:

```bash
memoryplane search --query "concise answers" --sort-by time --json
```

Search by confidence:

```bash
memoryplane search --query "concise answers" --sort-by confidence --json
```

Explain lexical matches:

```bash
memoryplane search --query "concise answers" --explain --json
```

Read aggregate counts:

```bash
memoryplane stats --json
```

Inspect one memory:

```bash
memoryplane inspect mem_xxx --json
```

Pack retrieval context:

```bash
memoryplane pack --query "user preferences" --budget 200 --format prompt --json
```

## Batch Operations

Print a JSON template:

```bash
memoryplane write-batch --template
```

Run JSON batch:

```bash
memoryplane write-batch --file ./memories.json --json
```

Example JSON batch:

```json
[
  {
    "type": "preference",
    "space": "preference",
    "entity": "user",
    "content": "User prefers concise answers",
    "source": "chat:sess_001",
    "durability": "durable",
    "dry_run": true
  },
  {
    "type": "event",
    "space": "event",
    "entity": "project",
    "content": "Kickoff completed",
    "source": "tool:job_42",
    "durability": "durable",
    "commit": true,
    "confidence": 0.9
  }
]
```

Run CSV batch:

```bash
memoryplane write-batch --csv ./memories.csv --json
```

Example CSV row:

```text
preference,preference,user,Likes Python,chat:csv_test,durable,0.95,false,true
```

CSV columns:

- `type`
- `space`
- `entity`
- `content`
- `source`
- `durability`
- `confidence`
- `dry_run`
- `commit`

Batch search:

```bash
memoryplane search-batch --file ./queries.txt --json
```

## JSON Expectations

- Success: `ok=true`, payload in `data`
- Failure: `ok=false`, inspect `errors[0].code` and `errors[0].message`
- Errors include a direct recovery hint in `Fix: ...`
- `list --json` returns compact records by default
- `list --full --json` returns full memory objects
- `write --dry-run` returns `data.candidate.candidate_id`
- `write --commit` returns `data.memory` and `data.committed_from_candidate_id`

## Storage Layout

```text
.memoryplane/
  candidates/
  indexes/search_cache.json
  logs/operations.jsonl
  projections/<space>/
  store/memories.jsonl
  store/revisions.jsonl
  store/tombstones.jsonl
```
