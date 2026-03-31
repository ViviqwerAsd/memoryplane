import json

from typer.testing import CliRunner

from memoryplane.cli import app


def init_workspace(runner, tmp_path):
    result = runner.invoke(app, ["init", "--root", str(tmp_path), "--json"])
    assert result.exit_code == 0


def write_and_commit(runner, tmp_path, *, type_, space, entity, content):
    result = runner.invoke(
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
            "--commit",
            "--json",
        ],
    )
    assert result.exit_code == 0
    return json.loads(result.stdout)["data"]["memory"]


def test_write_commit_option_commits_durable_memory_in_one_step(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)

    result = runner.invoke(
        app,
        [
            "write",
            "--root",
            str(tmp_path),
            "--type",
            "preference",
            "--space",
            "preference",
            "--entity",
            "user",
            "--content",
            "User prefers concise answers",
            "--source",
            "chat:sess_001",
            "--durability",
            "durable",
            "--commit",
            "--json",
        ],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["memory"]["durability"] == "durable"
    assert payload["data"]["committed_from_candidate_id"].startswith("cand_")
    assert "User prefers concise answers" in (tmp_path / ".memoryplane" / "store" / "memories.jsonl").read_text()
    assert list((tmp_path / ".memoryplane" / "candidates").glob("*.json")) == []


def test_write_batch_reports_missing_fields_clearly(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    batch_file = tmp_path / "batch.json"
    batch_file.write_text(
        json.dumps(
            [
                {
                    "type": "preference",
                    "entity": "user",
                    "content": "User prefers concise answers",
                    "source": "chat:sess_001",
                    "dry_run": True,
                }
            ]
        )
    )

    result = runner.invoke(app, ["write-batch", "--root", str(tmp_path), "--file", str(batch_file), "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["data"]["results"][0]["ok"] is False
    assert payload["data"]["results"][0]["error"]["message"] == (
        "Missing required fields: durability, space. Fix: add these fields to each batch item"
    )


def test_write_rejects_unknown_type_with_allowed_values(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)

    result = runner.invoke(
        app,
        [
            "write",
            "--root",
            str(tmp_path),
            "--type",
            "unknown",
            "--space",
            "preference",
            "--entity",
            "user",
            "--content",
            "User prefers concise answers",
            "--source",
            "chat:sess_001",
            "--durability",
            "durable",
            "--dry-run",
            "--json",
        ],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["errors"][0]["code"] == "INVALID_TYPE"
    assert "preference" in payload["errors"][0]["message"]
    assert "summary" in payload["errors"][0]["message"]


def test_list_returns_committed_memories_with_filters(tmp_path):
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
    write_and_commit(
        runner,
        tmp_path,
        type_="event",
        space="event",
        entity="project",
        content="Kickoff completed",
    )

    result = runner.invoke(
        app,
        [
            "list",
            "--root",
            str(tmp_path),
            "--space",
            "preference",
            "--json",
        ],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert len(payload["data"]["results"]) == 1
    assert payload["data"]["results"][0]["space"] == "preference"
    assert "score" not in payload["data"]["results"][0]


def test_stats_reports_memory_and_candidate_counts(tmp_path):
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
    draft = runner.invoke(
        app,
        [
            "write",
            "--root",
            str(tmp_path),
            "--type",
            "event",
            "--space",
            "event",
            "--entity",
            "project",
            "--content",
            "Kickoff completed",
            "--source",
            "chat:sess_001",
            "--durability",
            "durable",
            "--dry-run",
            "--json",
        ],
    )
    candidate_id = json.loads(draft.stdout)["data"]["candidate"]["candidate_id"]
    runner.invoke(app, ["reject", candidate_id, "--root", str(tmp_path), "--json"])

    result = runner.invoke(app, ["stats", "--root", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["memories"]["total"] == 1
    assert payload["data"]["memories"]["by_type"]["preference"] == 1
    assert payload["data"]["candidates"]["total"] == 1
    assert payload["data"]["candidates"]["by_status"]["rejected"] == 1
