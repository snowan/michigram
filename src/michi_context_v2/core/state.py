from __future__ import annotations

import json
from pathlib import Path

from .primitives import atomic_write

_DEFAULT_STATE = {
    "captured_sessions": {},
    "project_map": {},
    "evaluated_sessions": {},
}


def _state_path(base_dir: Path) -> Path:
    return base_dir / ".state.json"


def get_state(base_dir: Path) -> dict:
    path = _state_path(base_dir)
    if not path.exists():
        return {k: dict(v) for k, v in _DEFAULT_STATE.items()}
    data = json.loads(path.read_text())
    for key, default in _DEFAULT_STATE.items():
        data.setdefault(key, dict(default))
    return data


def save_state(base_dir: Path, state: dict) -> None:
    path = _state_path(base_dir)
    atomic_write(path, json.dumps(state, indent=2) + "\n")
