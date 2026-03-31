import json

from typer.testing import CliRunner

from memoryplane.cli import app


def test_init_creates_expected_files(tmp_path):
    runner = CliRunner()

    result = runner.invoke(app, ["init", "--root", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    memoryplane_root = tmp_path / ".memoryplane"

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert (memoryplane_root / "config.json").exists()
    assert (memoryplane_root / "store" / "memories.jsonl").exists()
    assert (memoryplane_root / "store" / "revisions.jsonl").exists()
    assert (memoryplane_root / "store" / "tombstones.jsonl").exists()
    assert (memoryplane_root / "candidates").is_dir()
    assert (memoryplane_root / "indexes" / "search_cache.json").exists()
    assert (memoryplane_root / "projections" / "profile").is_dir()
    assert (memoryplane_root / "projections" / "preference").is_dir()
    assert (memoryplane_root / "projections" / "event").is_dir()
