from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_DIR = Path.home() / ".michigram"


@dataclass
class Config:
    base_dir: Path = field(default_factory=lambda: DEFAULT_BASE_DIR)
    default_backend: str = "filesystem"
    token_budget: int = 8000
    default_adapter: str = "claude-code"
    prune_max_age_days: int = 30
    daemon_interval_seconds: int = 1800


def load_config(config_path: Path | None = None) -> Config:
    if config_path is None:
        config_path = DEFAULT_BASE_DIR / "config.json"
    if not config_path.exists():
        return Config()
    data = json.loads(config_path.read_text())
    kwargs: dict = {}
    if "base_dir" in data:
        kwargs["base_dir"] = Path(data["base_dir"])
    for key in ("default_backend", "token_budget", "default_adapter", "prune_max_age_days", "daemon_interval_seconds"):
        if key in data:
            kwargs[key] = data[key]
    return Config(**kwargs)


_ADAPTER_REGISTRY: dict[str, str] = {
    "claude-code": "michigram.adapters.claude_code:ClaudeCodeAdapter",
    "generic": "michigram.adapters.generic:GenericAdapter",
}


def register_adapter(name: str, import_path: str) -> None:
    _ADAPTER_REGISTRY[name] = import_path


def get_adapter_class(name: str) -> type:
    import importlib
    if name not in _ADAPTER_REGISTRY:
        raise KeyError(f"Unknown adapter: {name}. Available: {list(_ADAPTER_REGISTRY.keys())}")
    module_path, class_name = _ADAPTER_REGISTRY[name].rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
