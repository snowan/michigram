import pytest
from michigram.afs.namespace import Namespace
from michigram.afs.mount import FilesystemMount
from michigram.storage.filesystem import FilesystemBackend
from michigram.afs.node import ContextNode, NodeType, NodeMetadata
from michigram.core.primitives import now_iso


def _make_ns(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    return ns


def test_write_and_read(tmp_path):
    ns = _make_ns(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="/context/test/item",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts),
        content="test content",
    )
    ns.write("/context/test/item", node)
    result = ns.read("/context/test/item")
    assert result is not None
    assert result.content == "test content"


def test_list(tmp_path):
    ns = _make_ns(tmp_path)
    ts = now_iso()
    for name in ["a", "b", "c"]:
        node = ContextNode(
            path=f"/context/items/{name}",
            node_type=NodeType.FILE,
            metadata=NodeMetadata(created_at=ts, updated_at=ts),
            content=name,
        )
        ns.write(f"/context/items/{name}", node)
    items = ns.list("/context/items")
    assert items == ["a", "b", "c"]


def test_delete(tmp_path):
    ns = _make_ns(tmp_path)
    ts = now_iso()
    node = ContextNode(
        path="/context/del",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts),
        content="gone",
    )
    ns.write("/context/del", node)
    assert ns.delete("/context/del") is True
    assert ns.read("/context/del") is None


def test_no_mount_raises(tmp_path):
    ns = Namespace()
    with pytest.raises(KeyError):
        ns.read("/unknown/path")


def test_longest_prefix_match(tmp_path):
    backend1 = FilesystemBackend(tmp_path / "store1")
    backend2 = FilesystemBackend(tmp_path / "store2")
    mount1 = FilesystemMount(backend1)
    mount2 = FilesystemMount(backend2)
    ns = Namespace()
    ns.mount("/context", mount1)
    ns.mount("/context/special", mount2)

    ts = now_iso()
    node = ContextNode(
        path="/context/special/item",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts),
        content="special",
    )
    ns.write("/context/special/item", node)
    assert backend2.read("item") is not None
    assert backend1.read("special/item") is None
