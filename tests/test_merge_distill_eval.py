import json

from typer.testing import CliRunner

from memoryplane.cli import app


def init_workspace(runner, tmp_path):
    runner.invoke(app, ["init", "--root", str(tmp_path), "--json"])


def write_and_commit(runner, tmp_path, *, type_, space, entity, content):
    dry_run = runner.invoke(
        app,
        [
            "write",
            "--root",
            str(tmp_path),
            "--type",
            type_,
            "--space",
            space,
            "--entity",
            entity,
            "--content",
            content,
            "--source",
            "chat:sess_001",
            "--durability",
            "durable",
            "--dry-run",
            "--json",
        ],
    )
    candidate_id = json.loads(dry_run.stdout)["data"]["candidate"]["candidate_id"]
    commit = runner.invoke(app, ["commit", candidate_id, "--root", str(tmp_path), "--json"])
    return json.loads(commit.stdout)["data"]["memory"]


def test_merge_creates_dry_run_candidate_from_two_memories(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    first = write_and_commit(
        runner,
        tmp_path,
        type_="preference",
        space="preference",
        entity="user",
        content="User prefers concise answers",
    )
    second = write_and_commit(
        runner,
        tmp_path,
        type_="preference",
        space="preference",
        entity="user",
        content="User likes bullet points",
    )

    result = runner.invoke(
        app,
        ["merge", first["memory_id"], second["memory_id"], "--root", str(tmp_path), "--dry-run", "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["candidate"]["operation"] == "merge"
    assert "concise answers" in payload["data"]["candidate"]["memory"]["content"]


def test_distill_creates_summary_candidate_for_window(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    write_and_commit(
        runner,
        tmp_path,
        type_="event",
        space="event",
        entity="project",
        content="Kickoff completed",
    )
    write_and_commit(
        runner,
        tmp_path,
        type_="event",
        space="event",
        entity="project",
        content="Search prototype implemented",
    )

    result = runner.invoke(
        app,
        ["distill", "--root", str(tmp_path), "--window", "7d", "--into", "summary", "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["candidate"]["memory"]["type"] == "summary"
    assert "Kickoff completed" in payload["data"]["candidate"]["memory"]["content"]


def test_eval_returns_structured_metrics_for_queries(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    write_and_commit(
        runner,
        tmp_path,
        type_="preference",
        space="preference",
        entity="user",
        content="User prefers concise answers",
    )

    result = runner.invoke(
        app,
        ["eval", "--root", str(tmp_path), "--query", "preferences", "--query", "concise", "--topk", "3", "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert len(payload["data"]["queries"]) == 2
    assert "aggregate" in payload["data"]
