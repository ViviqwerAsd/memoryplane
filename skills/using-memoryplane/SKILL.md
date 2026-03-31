---
name: using-memoryplane
description: Use when working in the CLI-Memory repository and needing to create, review, commit, search, pack, inspect, merge, distill, or evaluate memories through the local memoryplane CLI.
---

# Using memoryplane

## Overview

`memoryplane` is a local memory control plane. Treat the CLI as the source of truth for operations and prefer `--json` for any agent-facing usage.

Run commands from the repository root: `/Users/vivi8n24/Desktop/Project/CLI-Memory`.

Default invocation:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli
```

If `.venv` is missing, create it and install the project:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## When to Use

Use this skill when an agent needs to:

- initialize a memory workspace
- propose or commit durable memories
- retrieve memory context for another task
- inspect raw memory state on disk
- merge or distill memories
- run lightweight retrieval evaluation

Do not bypass `memoryplane` by editing `.memoryplane/` files directly unless the user explicitly asks for manual repair.

## Core Rules

- Prefer `--json` so downstream agents can parse stable envelopes.
- Durable writes must be proposed first with `--dry-run`, then committed with `commit`.
- Candidate files live in `.memoryplane/candidates/`.
- Committed memories live in `.memoryplane/store/memories.jsonl`.
- Readable projections live in `.memoryplane/projections/<space>/`.

## Quick Workflow

Initialize a workspace:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli init --root /tmp/memoryplane-demo --json
```

Create a durable candidate:

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

Commit the returned `candidate_id`:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli commit cand_xxx --root /tmp/memoryplane-demo --json
```

Search:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli search \
  --root /tmp/memoryplane-demo \
  --query "concise answers" \
  --space preference \
  --json
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

Inspect a memory:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli inspect mem_xxx --root /tmp/memoryplane-demo --json
```

## Command Patterns

Reject a candidate:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli reject cand_xxx --root /tmp/memoryplane-demo --json
```

Merge two memories into a candidate:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli merge mem_a mem_b --root /tmp/memoryplane-demo --dry-run --json
```

Distill recent memories into a summary candidate:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli distill --root /tmp/memoryplane-demo --window 7d --into summary --json
```

Evaluate retrieval:

```bash
PYTHONPATH=src .venv/bin/python -m memoryplane.cli eval \
  --root /tmp/memoryplane-demo \
  --query "preferences" \
  --query "concise" \
  --topk 3 \
  --json
```

## Agent Guidance

- For personalized or stateful work, search before answering.
- For stable new observations, write a candidate instead of assuming memory changed.
- Use `inspect` or read `.memoryplane/` only after the CLI result if you need debugging detail.
- Treat `ok=false` JSON responses as authoritative and branch on `errors[].code`.
