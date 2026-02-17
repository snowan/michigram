from michigram.afs.namespace import Namespace
from michigram.afs.mount import FilesystemMount
from michigram.storage.filesystem import FilesystemBackend
from michigram.adapters.generic import GenericAdapter
from michigram.pipeline.constructor import ContextManifest
from michigram.afs.node import ContextNode, NodeType, NodeMetadata


def _setup(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    return GenericAdapter(ns), ns


def test_ingest_markdown(tmp_path):
    adapter, _ = _setup(tmp_path)
    md_file = tmp_path / "session.md"
    md_file.write_text("# Session Notes\nDid some work")
    sids = adapter.ingest(md_file, "proj")
    assert len(sids) == 1


def test_ingest_directory(tmp_path):
    adapter, _ = _setup(tmp_path)
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "a.md").write_text("note a")
    (d / "b.txt").write_text("note b")
    sids = adapter.ingest(d, "proj")
    assert len(sids) == 2


def test_format_context(tmp_path):
    adapter, _ = _setup(tmp_path)
    ts = "2026-01-01T00:00:00Z"
    items = [
        ContextNode(
            path="/context/test/item1",
            node_type=NodeType.FILE,
            metadata=NodeMetadata(created_at=ts, updated_at=ts),
            content="content 1",
        ),
        ContextNode(
            path="/context/test/item2",
            node_type=NodeType.FILE,
            metadata=NodeMetadata(created_at=ts, updated_at=ts),
            content="content 2",
        ),
    ]
    manifest = ContextManifest(items=items, total_tokens=10, strategy="recency")
    output = adapter.format_context(manifest)
    assert "content 1" in output
    assert "content 2" in output
    assert "---" in output


def test_detect_sessions(tmp_path):
    adapter, _ = _setup(tmp_path)
    d = tmp_path / "proj_dir"
    d.mkdir()
    (d / "notes.md").write_text("notes")
    (d / "log.txt").write_text("log")
    (d / "code.py").write_text("code")
    files = adapter.detect_sessions(str(d))
    names = [f.name for f in files]
    assert "notes.md" in names
    assert "log.txt" in names
    assert "code.py" not in names
