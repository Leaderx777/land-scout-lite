from pathlib import Path

from land_scout.core.flip_storage import clear_saved_flips, load_saved_flips, save_saved_flips


def test_save_and_load_saved_flips(tmp_path: Path):
    path = tmp_path / "saved_flips.json"
    deals = [
        {
            "address": "123 Main St",
            "decision": "BUY",
            "projected_profit": 42000.0,
            "roi_percent": 61.8,
        }
    ]

    save_saved_flips(deals, path)

    assert load_saved_flips(path) == deals


def test_load_missing_file_returns_empty_list(tmp_path: Path):
    assert load_saved_flips(tmp_path / "missing.json") == []


def test_clear_saved_flips(tmp_path: Path):
    path = tmp_path / "saved_flips.json"
    save_saved_flips([{"address": "123 Main St"}], path)

    clear_saved_flips(path)

    assert load_saved_flips(path) == []
