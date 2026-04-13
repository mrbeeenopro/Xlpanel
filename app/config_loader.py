from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load runtime configuration from JSON file."""
    path = Path(config_path).expanduser().resolve()
    with path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)
