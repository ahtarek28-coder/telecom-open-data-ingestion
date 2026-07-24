from odingest.checkpoint import load_checkpoint, save_checkpoint


def test_load_checkpoint_missing_file_returns_none(tmp_path):
    assert load_checkpoint(tmp_path / "does_not_exist.json") is None


def test_checkpoint_round_trip(tmp_path):
    path = tmp_path / "checkpoints" / "test.json"

    save_checkpoint(path, "2026-01-01T00:00:00.000Z")
    assert load_checkpoint(path) == "2026-01-01T00:00:00.000Z"

    save_checkpoint(path, "2026-02-01T00:00:00.000Z")
    assert load_checkpoint(path) == "2026-02-01T00:00:00.000Z"
