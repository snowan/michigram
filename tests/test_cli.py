import json
import subprocess
import sys
from pathlib import Path


def test_cli_status(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from michi_context_v2.core.config import Config
    from michi_context_v2.cli import cmd_status
    import argparse
    config_dir = tmp_path / ".michi-context-v2"
    config_dir.mkdir(parents=True)

    args = argparse.Namespace()
    cmd_status(args)


def test_cli_memory_store_recall(tmp_path, monkeypatch, capsys):
    config_dir = tmp_path / ".michi-context-v2"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"base_dir": str(config_dir)}))

    import michi_context_v2.core.config as cfg_mod
    original_load = cfg_mod.load_config

    def mock_load(path=None):
        return cfg_mod.Config(base_dir=config_dir)

    monkeypatch.setattr(cfg_mod, "load_config", mock_load)

    import argparse
    from michi_context_v2.cli import cmd_memory

    args = argparse.Namespace(
        action="store", project=str(tmp_path), type="facts", key="db", value="postgres"
    )
    cmd_memory(args)

    args2 = argparse.Namespace(
        action="recall", project=str(tmp_path), type="facts", key="db", value=""
    )
    cmd_memory(args2)
    captured = capsys.readouterr()
    assert "postgres" in captured.out


def test_cli_inject(tmp_path, monkeypatch, capsys):
    config_dir = tmp_path / ".michi-context-v2"
    config_dir.mkdir(parents=True)

    import michi_context_v2.core.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "load_config", lambda p=None: cfg_mod.Config(base_dir=config_dir))

    import argparse
    from michi_context_v2.cli import cmd_inject

    args = argparse.Namespace(
        project=str(tmp_path), adapter="claude-code", strategy="recency"
    )
    cmd_inject(args)
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "hookSpecificOutput" in parsed
