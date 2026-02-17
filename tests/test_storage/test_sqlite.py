from michi_context_v2.storage.sqlite import SqliteBackend
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata
from michi_context_v2.core.primitives import now_iso


def _backend(tmp_path):
    return SqliteBackend(tmp_path / "test.db")


def test_write_and_read(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="test/file1", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts),
        content="sqlite content",
    )
    be.write("test/file1", node)
    result = be.read("test/file1")
    assert result is not None
    assert result.content == "sqlite content"
    be.close()


def test_read_missing(tmp_path):
    be = _backend(tmp_path)
    assert be.read("nonexistent") is None
    be.close()


def test_list(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    for name in ["x", "y", "z"]:
        node = ContextNode(
            path=f"dir/{name}", node_type=NodeType.FILE,
            metadata=NodeMetadata(created_at=ts, updated_at=ts),
            content=name,
        )
        be.write(f"dir/{name}", node)
    items = be.list("dir")
    assert items == ["x", "y", "z"]
    be.close()


def test_delete(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="del/item", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts),
        content="delete me",
    )
    be.write("del/item", node)
    assert be.delete("del/item") is True
    assert be.read("del/item") is None
    assert be.delete("del/item") is False
    be.close()


def test_search_by_tags(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="s/tagged", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts, tags=["bug"]),
        content="tagged",
    )
    be.write("s/tagged", node)
    assert len(be.search("s", tags=["bug"])) == 1
    assert len(be.search("s", tags=["feature"])) == 0
    be.close()


def test_search_by_source(tmp_path):
    be = _backend(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="s/src", node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts, source="user"),
        content="user data",
    )
    be.write("s/src", node)
    assert len(be.search("s", source="user")) == 1
    assert len(be.search("s", source="system")) == 0
    be.close()
