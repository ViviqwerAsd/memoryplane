import json

from typer.testing import CliRunner

from memoryplane.cli import app


def init_workspace(runner, tmp_path):
    result = runner.invoke(app, ["init", "--root", str(tmp_path), "--json"])
    assert result.exit_code == 0


def test_missing_candidate_returns_stable_json_error(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)

    result = runner.invoke(app, ["commit", "cand_missing", "--root", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["ok"] is False
    assert payload["command"] == "commit"
    assert payload["errors"][0]["code"] == "CANDIDATE_NOT_FOUND"


def test_dry_run_write_creates_candidate_file(tmp_path):
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
            "--dry-run",
            "--json",
        ],
    )
    payload = json.loads(result.stdout)
    candidate_id = payload["data"]["candidate"]["candidate_id"]

    assert result.exit_code == 0
    assert (tmp_path / ".memoryplane" / "candidates" / f"{candidate_id}.json").exists()


def test_durable_write_without_dry_run_is_rejected(tmp_path):
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
            "--json",
        ],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 3
    assert payload["ok"] is False
    assert payload["errors"][0]["code"] == "DRY_RUN_REQUIRED"


def test_commit_moves_candidate_into_canonical_store_and_projection(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)

    dry_run = runner.invoke(
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
            "--dry-run",
            "--json",
        ],
    )
    candidate_id = json.loads(dry_run.stdout)["data"]["candidate"]["candidate_id"]

    commit = runner.invoke(app, ["commit", candidate_id, "--root", str(tmp_path), "--json"])
    payload = json.loads(commit.stdout)
    memory_id = payload["data"]["memory"]["memory_id"]

    assert commit.exit_code == 0
    assert payload["ok"] is True
    assert "User prefers concise answers" in (tmp_path / ".memoryplane" / "store" / "memories.jsonl").read_text()
    assert not (tmp_path / ".memoryplane" / "candidates" / f"{candidate_id}.json").exists()
    assert (tmp_path / ".memoryplane" / "projections" / "preference" / f"{memory_id}.json").exists()


def test_reject_marks_candidate_as_rejected(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)

    dry_run = runner.invoke(
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
            "tentative",
            "--dry-run",
            "--json",
        ],
    )
    candidate_id = json.loads(dry_run.stdout)["data"]["candidate"]["candidate_id"]

    reject = runner.invoke(app, ["reject", candidate_id, "--root", str(tmp_path), "--json"])
    payload = json.loads(reject.stdout)
    candidate_file = tmp_path / ".memoryplane" / "candidates" / f"{candidate_id}.json"

    assert reject.exit_code == 0
    assert payload["ok"] is True
    assert json.loads(candidate_file.read_text())["status"] == "rejected"
