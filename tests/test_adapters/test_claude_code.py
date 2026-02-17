import json
from pathlib import Path
from unittest.mock import patch

from michigram.afs.namespace import Namespace
from michigram.afs.mount import FilesystemMount
from michigram.storage.filesystem import FilesystemBackend
from michigram.repository.history import HistoryRepository
from michigram.repository.memory import MemoryRepository, MemoryType
from michigram.adapters.claude_code import ClaudeCodeAdapter
from michigram.pipeline.constructor import ContextConstructor


def _setup(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    history = HistoryRepository(ns)
    memory = MemoryRepository(ns)
    return ClaudeCodeAdapter(history), history, memory, ns


def test_ingest_single_file(tmp_path, sample_jsonl):
    adapter, _, _, _ = _setup(tmp_path)
    sids = adapter.ingest(sample_jsonl, "testproj")
    assert len(sids) == 1
    assert sids[0] == "abc123"


def test_ingest_directory(tmp_path, sample_jsonl):
    adapter, _, _, _ = _setup(tmp_path)
    sids = adapter.ingest(sample_jsonl.parent, "testproj")
    assert len(sids) >= 1


def test_format_context(tmp_path, sample_jsonl):
    adapter, history, memory, _ = _setup(tmp_path)
    adapter.ingest(sample_jsonl, "testproj")

    constructor = ContextConstructor(history, memory)
    manifest = constructor.construct("testproj")
    output = adapter.format_context(manifest)

    parsed = json.loads(output)
    assert "hookSpecificOutput" in parsed
    assert "additionalContext" in parsed["hookSpecificOutput"]


def test_format_empty_manifest(tmp_path):
    adapter, _, _, _ = _setup(tmp_path)
    from michigram.pipeline.constructor import ContextManifest
    manifest = ContextManifest()
    output = adapter.format_context(manifest)
    parsed = json.loads(output)
    assert parsed["hookSpecificOutput"]["additionalContext"] == ""


def test_detect_sessions_dotted_path(tmp_path):
    adapter, _, _, _ = _setup(tmp_path)
    claude_dir = tmp_path / ".claude" / "projects"
    project_dir = claude_dir / "Users-xiaowei-wan-code-myproject"
    project_dir.mkdir(parents=True)
    (project_dir / "session1.jsonl").write_text('{"type":"summary"}\n')

    with patch.object(Path, "home", return_value=tmp_path):
        sessions = adapter.detect_sessions("/Users/xiaowei.wan/code/myproject")

    assert len(sessions) == 1
    assert sessions[0].name == "session1.jsonl"
