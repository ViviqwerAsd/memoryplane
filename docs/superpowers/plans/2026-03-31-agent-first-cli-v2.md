# Agent-First CLI V2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `memoryplane` more comfortable for agents by shortening common command usage, defaulting to compact browse output, adding recent/time/confidence retrieval helpers, supporting batch templates and CSV import, and making errors tell the agent how to recover.

**Architecture:** Add a lightweight config/default-resolution layer that merges CLI flags, environment variables, workspace config, and built-in defaults. Keep canonical storage unchanged while teaching the CLI and services to emit agent-friendly compact views and actionable errors. Extend batch ingestion and retrieval sorting without changing existing JSON envelope structure.

**Tech Stack:** Python 3.11+, Typer, Pydantic, pytest

---

## Chunk 1: Config And Defaults

### Task 1: Add config resolution for root/json defaults

**Files:**
- Create: `src/memoryplane/config_runtime.py`
- Modify: `src/memoryplane/cli.py`
- Test: `tests/test_agent_cli_v2.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**

### Task 2: Support workspace `.memoryplane.conf` and env precedence

**Files:**
- Modify: `src/memoryplane/config_runtime.py`
- Modify: `src/memoryplane/cli.py`
- Test: `tests/test_agent_cli_v2.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**

## Chunk 2: Retrieval Ergonomics

### Task 3: Make `list` compact by default and add `--full`

**Files:**
- Modify: `src/memoryplane/services/catalog_service.py`
- Modify: `src/memoryplane/cli.py`
- Test: `tests/test_agent_cli_v2.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**

### Task 4: Add `--recent` filtering and confidence/time sorting

**Files:**
- Modify: `src/memoryplane/services/catalog_service.py`
- Modify: `src/memoryplane/services/search_service.py`
- Modify: `src/memoryplane/cli.py`
- Modify: `src/memoryplane/utils/validation.py`
- Modify: `src/memoryplane/utils/text.py`
- Test: `tests/test_agent_cli_v2.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**

## Chunk 3: Batch And Errors

### Task 5: Add `write-batch --template` and CSV import

**Files:**
- Modify: `src/memoryplane/cli.py`
- Modify: `src/memoryplane/client.py`
- Modify: `src/memoryplane/utils/validation.py`
- Test: `tests/test_agent_cli_v2.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**

### Task 6: Add actionable recovery guidance to CLI errors

**Files:**
- Modify: `src/memoryplane/cli.py`
- Modify: `src/memoryplane/utils/validation.py`
- Test: `tests/test_agent_cli_v2.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**

## Chunk 4: Docs And Verification

### Task 7: Rewrite README around the new default workflows

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update examples to use `memoryplane` directly**
- [ ] **Step 2: Document config precedence, compact output, recent filters, sorting, template, and CSV**

### Task 8: Run full verification

**Files:**
- Test: `tests/test_agent_cli_v2.py`
- Test: `tests/`

- [ ] **Step 1: Run targeted tests**
- [ ] **Step 2: Run full test suite**
- [ ] **Step 3: Run CLI smoke checks for compact list, config defaults, and batch template**
