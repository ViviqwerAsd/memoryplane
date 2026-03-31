import json
from pathlib import Path

from typer.testing import CliRunner

from memoryplane.cli import app


def init_workspace(runner, root: Path):
    result = runner.invoke(app, ["init", "--root", str(root), "--json"])
    assert result.exit_code == 0


def write_memory(
    runner,
    root: Path,
    *,
    type_: str = "preference",
    space: str = "preference",
    entity: str = "user",
    content: str,
    confidence: float = 1.0,
    timestamp_patch=None,
):
    if timestamp_patch is not None:
        command = timestamp_patch
    result = runner.invoke(
        app,
        [
            "write",
            "--root",
            str(root),
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
            "--confidence",
            str(confidence),
            "--commit",
            "--json",
        ],
    )
    assert result.exit_code == 0
    return json.loads(result.stdout)["data"]["memory"]


def test_config_defaults_apply_and_precedence_is_cli_over_env_over_config(tmp_path, monkeypatch):
    runner = CliRunner()
    config_root = tmp_path / "config-root"
    env_root = tmp_path / "env-root"
    cli_root = tmp_path / "cli-root"
    init_workspace(runner, config_root)
    init_workspace(runner, env_root)
    init_workspace(runner, cli_root)

    write_memory(runner, config_root, content="from config root")
    write_memory(runner, env_root, content="from env root")
    write_memory(runner, cli_root, content="from cli root")

    (tmp_path / ".memoryplane.conf").write_text(json.dumps({"root": str(config_root), "json": True}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MEMORYPLANE_ROOT", str(env_root))

    env_result = runner.invoke(app, ["list"])
    env_payload = json.loads(env_result.stdout)
    assert env_result.exit_code == 0
    assert env_payload["data"]["results"][0]["content_preview"] == "from env root"

    cli_result = runner.invoke(app, ["list", "--root", str(cli_root)])
    cli_payload = json.loads(cli_result.stdout)
    assert cli_result.exit_code == 0
    assert cli_payload["data"]["results"][0]["content_preview"] == "from cli root"


def test_list_defaults_to_compact_json_and_supports_full_mode(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    memory = write_memory(runner, tmp_path, content="User prefers concise answers and direct summaries")

    compact = runner.invoke(app, ["list", "--root", str(tmp_path), "--json"])
    compact_payload = json.loads(compact.stdout)
    compact_item = compact_payload["data"]["results"][0]

    assert compact.exit_code == 0
    assert compact_item["memory_id"] == memory["memory_id"]
    assert compact_item["type"] == "preference"
    assert compact_item["content_preview"] == "User prefers concise answers and direct summaries"
    assert "memory" not in compact_item

    full = runner.invoke(app, ["list", "--root", str(tmp_path), "--full", "--json"])
    full_payload = json.loads(full.stdout)

    assert full.exit_code == 0
    assert full_payload["data"]["results"][0]["memory"]["memory_id"] == memory["memory_id"]


def test_list_recent_filters_to_recent_window(tmp_path, monkeypatch):
    runner = CliRunner()
    init_workspace(runner, tmp_path)

    monkeypatch.setattr("memoryplane.services.write_service.utc_now", lambda: "2026-03-31T07:00:00Z")
    write_memory(runner, tmp_path, content="older memory")
    monkeypatch.setattr("memoryplane.services.write_service.utc_now", lambda: "2026-03-31T09:00:00Z")
    monkeypatch.setattr("memoryplane.utils.text.utc_now_datetime", lambda: __import__("datetime").datetime(2026, 3, 31, 9, 0, 0, tzinfo=__import__("datetime").UTC))
    write_memory(runner, tmp_path, content="recent memory")

    result = runner.invoke(app, ["list", "--root", str(tmp_path), "--recent", "1h", "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert [item["content_preview"] for item in payload["data"]["results"]] == ["recent memory"]


def test_search_supports_confidence_sort(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    low = write_memory(runner, tmp_path, content="concise answer style", confidence=0.3)
    high = write_memory(runner, tmp_path, content="concise answer preference", confidence=0.9)

    result = runner.invoke(
        app,
        ["search", "--root", str(tmp_path), "--query", "concise answer", "--sort-by", "confidence", "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert [item["memory"]["memory_id"] for item in payload["data"]["results"]] == [
        high["memory_id"],
        low["memory_id"],
    ]


def test_write_batch_template_prints_example_payload(tmp_path):
    runner = CliRunner()

    result = runner.invoke(app, ["write-batch", "--template"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert payload[0]["type"] == "preference"
    assert "durability" in payload[0]


def test_write_batch_supports_csv_import(tmp_path):
    runner = CliRunner()
    init_workspace(runner, tmp_path)
    csv_file = tmp_path / "memories.csv"
    csv_file.write_text(
        "type,space,entity,content,source,durability,commit,confidence\n"
        "preference,preference,user,User prefers bullet points,chat:sess_001,durable,true,0.8\n"
    )

    result = runner.invoke(
        app,
        ["write-batch", "--root", str(tmp_path), "--csv", str(csv_file), "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["data"]["results"][0]["ok"] is True

    listed = runner.invoke(app, ["list", "--root", str(tmp_path), "--json"])
    listed_payload = json.loads(listed.stdout)
    assert listed_payload["data"]["results"][0]["content_preview"] == "User prefers bullet points"


def test_errors_include_fix_suggestions(tmp_path):
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

    batch_result = runner.invoke(app, ["write-batch", "--root", str(tmp_path), "--file", str(batch_file), "--json"])
    batch_payload = json.loads(batch_result.stdout)
    assert "Fix:" in batch_payload["data"]["results"][0]["error"]["message"]

    invalid_type = runner.invoke(
        app,
        [
            "write",
            "--root",
            str(tmp_path),
            "--type",
            "invalid",
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
    invalid_payload = json.loads(invalid_type.stdout)
    assert "Fix:" in invalid_payload["errors"][0]["message"]
