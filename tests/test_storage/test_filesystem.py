from michi_context_v2.storage.filesystem import FilesystemBackend
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata
from michi_context_v2.core.primitives import now_iso


def _backend(tmp_path):
    return FilesystemBackend(tmp_path / "store")


def test_write_and_read(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="test/file1",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts),
        content="content here",
    )
    be.write("test/file1", node)
    result = be.read("test/file1")
    assert result is not None
    assert result.content == "content here"
    assert result.metadata.created_at == ts


def test_read_missing(tmp_path):
    be = _backend(tmp_path)
    assert be.read("nonexistent") is None


def test_list(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    for name in ["alpha", "beta"]:
        node = ContextNode(
            path=f"dir/{name}",
            node_type=NodeType.FILE,
            metadata=NodeMetadata(created_at=ts, updated_at=ts),
            content=name,
        )
        be.write(f"dir/{name}", node)
    items = be.list("dir")
    assert "alpha" in items
    assert "beta" in items


def test_delete(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="del/target",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts),
        content="bye",
    )
    be.write("del/target", node)
    assert be.delete("del/target") is True
    assert be.read("del/target") is None
    assert be.delete("del/target") is False


def test_search_by_tags(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    node1 = ContextNode(
        path="s/a", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts, tags=["error", "python"]),
        content="a",
    )
    node2 = ContextNode(
        path="s/b", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts, tags=["info"]),
        content="b",
    )
    be.write("s/a", node1)
    be.write("s/b", node2)
    results = be.search("s", tags=["error"])
    assert len(results) == 1
    assert results[0].path == "s/a"


def test_search_by_source(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="s/c", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts, source="evaluator"),
        content="c",
    )
    be.write("s/c", node)
    assert len(be.search("s", source="evaluator")) == 1
    assert len(be.search("s", source="user")) == 0


def test_search_by_since(tmp_path):
    be = _backend(tmp_path)
    node_old = ContextNode(
        path="s/old", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z"),
        content="old",
    )
    node_new = ContextNode(
        path="s/new", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at="2026-02-01T00:00:00Z", updated_at="2026-02-01T00:00:00Z"),
        content="new",
    )
    be.write("s/old", node_old)
    be.write("s/new", node_new)
    results = be.search("s", since="2026-01-01T00:00:00Z")
    assert len(results) == 1
    assert results[0].path == "s/new"
