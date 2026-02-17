from michi_context_v2.afs.mount import FilesystemMount
from michi_context_v2.storage.filesystem import FilesystemBackend
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata
from michi_context_v2.core.primitives import now_iso


def test_mount_delegates_to_backend(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ts = now_iso()
    node = ContextNode(
        path="test/item",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts, tags=["x"]),
        content="via mount",
    )
    mount.write("test/item", node)
    result = mount.read("test/item")
    assert result is not None
    assert result.content == "via mount"


def test_mount_search(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ts = now_iso()
    node = ContextNode(
        path="search/item",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts, source="claude-code", tags=["error"]),
        content="error log",
    )
    mount.write("search/item", node)
    results = mount.search("search", tags=["error"])
    assert len(results) == 1
    assert results[0].metadata.source == "claude-code"
