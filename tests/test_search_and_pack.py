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


def test_search_filters_by_space_and_ranks_matching_content(tmp_path):
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
        content="Kickoff meeting happened yesterday",
    )

    result = runner.invoke(
        app,
        ["search", "--root", str(tmp_path), "--query", "concise answers", "--space", "preference", "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert len(payload["data"]["results"]) == 1
    assert payload["data"]["results"][0]["memory"]["content"] == "User prefers concise answers"
    assert payload["data"]["results"][0]["score"] > 0


def test_search_supports_chinese_content(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    write_and_commit(
        runner,
        tmp_path,
        type_="preference",
        space="preference",
        entity="user",
        content="用户偏好简洁回答",
    )

    result = runner.invoke(
        app,
        ["search", "--root", str(tmp_path), "--query", "简洁回答", "--space", "preference", "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert len(payload["data"]["results"]) == 1
    assert payload["data"]["results"][0]["memory"]["content"] == "用户偏好简洁回答"
    assert payload["data"]["results"][0]["score"] > 0


def test_pack_respects_budget_and_returns_prompt_format(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    write_and_commit(
        runner,
        tmp_path,
        type_="preference",
        space="preference",
        entity="user",
        content="User prefers concise answers and direct summaries",
    )

    result = runner.invoke(
        app,
        ["pack", "--root", str(tmp_path), "--query", "preferences", "--budget", "80", "--format", "prompt", "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert len(payload["data"]["packed_text"]) <= 80
    assert "Query:" in payload["data"]["packed_text"]


def test_inspect_returns_memory_record_by_id(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    memory = write_and_commit(
        runner,
        tmp_path,
        type_="preference",
        space="preference",
        entity="user",
        content="User prefers concise answers",
    )

    result = runner.invoke(app, ["inspect", memory["memory_id"], "--root", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["memory"]["memory_id"] == memory["memory_id"]


def test_search_supports_multi_type_filter_and_timestamp_sort(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    older = write_and_commit(
        runner,
        tmp_path,
        type_="profile",
        space="preference",
        entity="user",
        content="Python engineer with backend focus",
    )
    newer = write_and_commit(
        runner,
        tmp_path,
        type_="event",
        space="event",
        entity="project",
        content="Python service shipped today",
    )

    result = runner.invoke(
        app,
        [
            "search",
            "--root",
            str(tmp_path),
            "--query",
            "Python",
            "--type",
            "profile",
            "--type",
            "event",
            "--sort-by",
            "timestamp",
            "--json",
        ],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert [item["memory"]["memory_id"] for item in payload["data"]["results"]] == [
        newer["memory_id"],
        older["memory_id"],
    ]
