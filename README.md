# memoryplane

`memoryplane` is a local-first memory control plane for agents.

It makes memory explicit, inspectable, and scriptable through:

- a CLI for reviewable operations
- a Python SDK for runtime integration
- JSONL canonical storage plus readable filesystem projections

## Features

- explicit two-phase durable writes
- candidate review and commit flow
- lexical search with metadata filters
- prompt packing
- merge, distill, and eval workflows
- batch write and batch search
- Chinese and mixed-language tokenization

## Install

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Run the CLI:

```bash
.venv/bin/memoryplane --help
```

If you do not want to install the script entrypoint yet, run the module directly:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli --help
```

## Quick Start

Initialize a workspace:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli init --root /tmp/memoryplane-demo --json
```

Write a durable memory in one step:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli write \
  --root /tmp/memoryplane-demo \
  --type preference \
  --space preference \
  --entity user \
  --content "User prefers concise answers" \
  --source chat:sess_001 \
  --durability durable \
  --commit \
  --json
```

Or keep the review flow:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli write \
  --root /tmp/memoryplane-demo \
  --type preference \
  --space preference \
  --entity user \
  --content "User prefers concise answers" \
  --source chat:sess_001 \
  --durability durable \
  --dry-run \
  --json
```

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli commit cand_xxx --root /tmp/memoryplane-demo --json
```

List committed memories:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli list \
  --root /tmp/memoryplane-demo \
  --space preference \
  --json
```

Search committed memories:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli search \
  --root /tmp/memoryplane-demo \
  --query "concise answers" \
  --space preference \
  --limit 5 \
  --explain \
  --json
```

Inspect aggregate stats:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli stats --root /tmp/memoryplane-demo --json
```

Pack prompt-ready context:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli pack \
  --root /tmp/memoryplane-demo \
  --query "user preferences" \
  --budget 200 \
  --format prompt \
  --json
```

## Data Model

### Predefined `type` values

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

### Predefined `entity` values

- `user`
- `project`
- `system`
- `topic`

### `source` format

`source` uses `kind:session_id`.

- Allowed `kind` values: `chat`, `tool`, `system`
- `session_id` is required
- Examples:
  - `chat:sess_001`
  - `tool:buildkite_42`
  - `system:distill`

Use `chat` for conversational observations, `tool` for tool or workflow output, and `system` for internally generated memories such as merge or distill summaries.

### `durability` values

- `tentative`: write directly to canonical storage
- `durable`: requires either `--dry-run` or `--commit`

## CLI Usage

Core commands:

- `init`
- `write`
- `commit`
- `reject`
- `list`
- `stats`
- `search`
- `pack`
- `inspect`
- `merge`
- `distill`
- `eval`
- `write-batch`
- `search-batch`

### Important rules

- `--json` is the preferred output mode for agent and runtime usage
- use `list` when you want to browse memories without a query
- use `search` when you want lexical ranking over query terms
- `search` is BM25-lite lexical search, not embedding or semantic search
- durable writes require either:
  - `--dry-run` followed by `commit`
  - `--commit` for an inline create-and-commit flow

### Common write flows

Tentative write:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli write \
  --root /tmp/memoryplane-demo \
  --type event \
  --space event \
  --entity project \
  --content "Kickoff completed" \
  --source chat:sess_001 \
  --durability tentative \
  --json
```

Durable review flow:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli write \
  --root /tmp/memoryplane-demo \
  --type preference \
  --space preference \
  --entity user \
  --content "User prefers concise answers" \
  --source chat:sess_001 \
  --durability durable \
  --dry-run \
  --json
```

Durable one-step flow:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli write \
  --root /tmp/memoryplane-demo \
  --type preference \
  --space preference \
  --entity user \
  --content "User prefers concise answers" \
  --source chat:sess_001 \
  --durability durable \
  --commit \
  --json
```

### `list`

`list` returns committed memories without scores.

Supported filters:

- `--limit`
- `--space`
- `--entity`
- repeated `--type`
- `--after`
- `--before`

Example:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli list \
  --root /tmp/memoryplane-demo \
  --type preference \
  --limit 10 \
  --json
```

### `stats`

`stats` returns aggregate counts for:

- committed memories
- memory status, type, space, entity, and durability breakdowns
- candidate totals grouped by status and operation

### `search`

`search` supports:

- `--query`
- `--space`
- `--entity`
- repeated `--type`
- `--after`
- `--before`
- `--sort-by relevance|timestamp`
- `--limit`
- `--explain`

Example:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli search \
  --root /tmp/memoryplane-demo \
  --query "Python" \
  --type profile \
  --type event \
  --sort-by timestamp \
  --explain \
  --limit 10 \
  --json
```

Notes:

- `score` is only meaningful for non-empty queries
- if you want a plain inventory view, use `list` instead of `search`
- `--explain` includes the matched lexical terms so you can see why a result was returned

### Batch commands

Batch write from a JSON file. Each item accepts the same keys as `write`.

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
    "source": "chat:sess_001",
    "durability": "durable",
    "commit": true
  },
  {
    "type": "task",
    "space": "ops",
    "entity": "project",
    "content": "Prepare weekly summary",
    "source": "tool:cron_001",
    "durability": "tentative"
  }
]
```

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli write-batch \
  --root /tmp/memoryplane-demo \
  --file ./memories.json \
  --json
```

If a batch item is missing required fields, the CLI returns a friendly message such as `Missing required fields: durability, space`.

Batch search from a newline-delimited query file:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli search-batch \
  --root /tmp/memoryplane-demo \
  --file ./queries.txt \
  --space preference \
  --limit 5 \
  --json
```

## Python SDK

Use the SDK when an agent or application needs to call memoryplane frequently without spawning subprocesses.

```python
from memoryplane import MemoryPlaneClient

client = MemoryPlaneClient(root="/tmp/memoryplane-demo")
client.init()

candidate = client.write(
    type="preference",
    space="preference",
    entity="user",
    content="User prefers concise answers",
    source="chat:sess_001",
    durability="durable",
    commit=True,
)["memory"]

listed = client.list(space="preference", limit=10)

results = client.search(
    query="concise",
    space="preference",
    limit=5,
)

stats = client.stats()

packed = client.pack(
    query="user preferences",
    budget=200,
)
```

### SDK methods

- `init()`
- `write(...)`
- `commit(candidate_id)`
- `reject(candidate_id)`
- `list(...)`
- `stats()`
- `inspect(memory_id)`
- `search(...)`
- `pack(...)`
- `merge(...)`
- `distill(...)`
- `eval(...)`
- `write_batch(items)`
- `search_batch(queries, ...)`

Example batch usage:

```python
from memoryplane import MemoryPlaneClient

client = MemoryPlaneClient(root="/tmp/memoryplane-demo")
client.init()

batch = client.write_batch(
    [
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
            "source": "chat:sess_001",
            "durability": "durable",
            "dry_run": True,
        },
    ]
)

searches = client.search_batch(
    ["concise", "kickoff"],
    limit=5,
)
```

## Storage Layout

Each workspace gets a `.memoryplane/` directory:

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

### Storage roles

- `store/memories.jsonl`: committed source of truth
- `candidates/`: proposal files waiting for commit or reject
- `indexes/search_cache.json`: lightweight lexical index
- `projections/`: readable per-memory JSON views
- `logs/operations.jsonl`: operation history

## Development

Run tests:

```bash
PYTHONPATH=src .venv/bin/pytest -v
```

Smoke test the CLI:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli init --root /tmp/memoryplane-demo --json
```

Smoke test the SDK:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
from memoryplane import MemoryPlaneClient
client = MemoryPlaneClient('/tmp/memoryplane-sdk-demo')
print(client.init())
print(client.write(type='preference', space='preference', entity='user', content='User prefers concise answers', source='chat:sess_001', durability='durable', dry_run=True))
PY
```
