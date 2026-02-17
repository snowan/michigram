import json
from pathlib import Path
from michigram.core.config import Config, load_config, DEFAULT_BASE_DIR


def test_default_config():
    cfg = Config()
    assert cfg.base_dir == DEFAULT_BASE_DIR
    assert cfg.default_backend == "filesystem"
    assert cfg.token_budget == 8000


def test_load_config_missing_file(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.json")
    assert cfg.token_budget == 8000


def test_load_config_from_file(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "token_budget": 16000,
        "default_backend": "sqlite",
    }))
    cfg = load_config(config_file)
    assert cfg.token_budget == 16000
    assert cfg.default_backend == "sqlite"
    assert cfg.default_adapter == "claude-code"


def test_load_config_with_base_dir(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"base_dir": "/custom/path"}))
    cfg = load_config(config_file)
    assert cfg.base_dir == Path("/custom/path")
