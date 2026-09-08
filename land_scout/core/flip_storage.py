import json
from pathlib import Path
from typing import Any

DEFAULT_STORAGE_PATH = Path("data/saved_flip_deals.json")


def load_saved_flips(path: Path | str = DEFAULT_STORAGE_PATH) -> list[dict[str, Any]]:
    storage_path = Path(path)
    if not storage_path.exists():
        return []

    try:
        data = json.loads(storage_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    return data if isinstance(data, list) else []


def save_saved_flips(
    deals: list[dict[str, Any]],
    path: Path | str = DEFAULT_STORAGE_PATH,
) -> None:
    storage_path = Path(path)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(
        json.dumps(deals, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_saved_flips(path: Path | str = DEFAULT_STORAGE_PATH) -> None:
    storage_path = Path(path)
    if storage_path.exists():
        storage_path.unlink()
