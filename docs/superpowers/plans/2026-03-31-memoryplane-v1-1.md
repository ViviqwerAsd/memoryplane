# memoryplane v1.1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `memoryplane` to `memoryplane` and add a first-class Python SDK, batch operations, and stronger search filtering/sorting without changing the local-first storage model.

**Architecture:** The existing service and storage layers remain the execution core, while the package and CLI move to `memoryplane`. A new `MemoryPlaneClient` wraps service modules directly, and CLI batch commands reuse the same underlying services to keep behavior aligned across interfaces.

**Tech Stack:** Python 3.11+, Typer, Pydantic, pytest

---

## File Structure

- Create: `src/memoryplane/client.py`
- Create: `src/memoryplane/...` mirrors the old package after rename
- Create: `tests/test_sdk.py`
- Modify: `pyproject.toml`
- Modify: all existing tests to import `memoryplane`
- Move/replace: `skills/using-memoryplane/SKILL.md`
- Update: spec and plan references where needed

## Chunk 1: Rename Package And CLI

### Task 1: Rename Python package and tests

**Files:**
- Move: `src/memoryplane/*` -> `src/memoryplane/*`
- Modify: `pyproject.toml`
- Modify: `tests/conftest.py`
- Modify: all existing test files

- [ ] **Step 1: Write the failing rename test**
- [ ] **Step 2: Run it to confirm imports break until rename is complete**
- [ ] **Step 3: Rename package, scripts, and imports**
- [ ] **Step 4: Run renamed tests**
- [ ] **Step 5: Commit**

## Chunk 2: SDK

### Task 2: Add `MemoryPlaneClient`

**Files:**
- Create: `src/memoryplane/client.py`
- Modify: `src/memoryplane/__init__.py`
- Test: `tests/test_sdk.py`

- [ ] **Step 1: Write failing SDK tests**
- [ ] **Step 2: Run to confirm failure**
- [ ] **Step 3: Implement minimal client methods over existing services**
- [ ] **Step 4: Run SDK tests**
- [ ] **Step 5: Commit**

## Chunk 3: Batch Operations

### Task 3: Add `write_batch` and `search_batch` to SDK and CLI

**Files:**
- Modify: `src/memoryplane/client.py`
- Modify: `src/memoryplane/cli.py`
- Add or modify service helpers as needed
- Test: `tests/test_sdk.py`

- [ ] **Step 1: Write failing batch tests**
- [ ] **Step 2: Run to confirm failure**
- [ ] **Step 3: Implement batch methods and CLI commands**
- [ ] **Step 4: Run batch tests**
- [ ] **Step 5: Commit**

## Chunk 4: Search Enhancements

### Task 4: Add richer filters and sorting

**Files:**
- Modify: `src/memoryplane/services/search_service.py`
- Modify: `src/memoryplane/cli.py`
- Modify: `src/memoryplane/client.py`
- Test: `tests/test_search_and_pack.py`
- Test: `tests/test_sdk.py`

- [ ] **Step 1: Write failing tests for multi-type filters and timestamp sort**
- [ ] **Step 2: Run to confirm failure**
- [ ] **Step 3: Implement search enhancements**
- [ ] **Step 4: Run search tests**
- [ ] **Step 5: Commit**

## Chunk 5: Skill And Final Verification

### Task 5: Rename and refresh the local usage skill

**Files:**
- Move/replace: `skills/using-memoryplane/SKILL.md`

- [ ] **Step 1: Update the skill to use `memoryplane` terminology and commands**
- [ ] **Step 2: Review for correctness**

### Task 6: Run end-to-end verification

**Files:**
- Modify tests only if verification reveals real issues

- [ ] **Step 1: Run the full test suite**
- [ ] **Step 2: Run CLI smoke tests with `python -m memoryplane.cli`**
- [ ] **Step 3: Run SDK smoke tests**
- [ ] **Step 4: Summarize changes**

Plan complete and saved to `docs/superpowers/plans/2026-03-31-memoryplane-v1-1.md`. Execution will proceed in this session.
