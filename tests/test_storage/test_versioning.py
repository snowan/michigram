from michi_context_v2.storage.filesystem import FilesystemBackend
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata
from michi_context_v2.core.primitives import now_iso


def _backend(tmp_path):
    return FilesystemBackend(tmp_path / "store")


def _node(content: str, version: int = 1) -> ContextNode:
    ts = now_iso()
    return ContextNode(
        path="test/file1",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(created_at=ts, updated_at=ts, version=version),
        content=content,
    )


def test_write_creates_version_on_update(tmp_path):
    be = _backend(tmp_path)
    be.write("test/file1", _node("v1 content", version=1))
    be.write("test/file1", _node("v2 content", version=2))
    vdir = tmp_path / "store" / ".versions" / "test" / "file1"
    assert (vdir / "v1").exists()
    assert (vdir / "v1.meta.json").exists()
    assert (vdir / "v1").read_text() == "v1 content"


def test_get_versions(tmp_path):
    be = _backend(tmp_path)
    be.write("test/file1", _node("first", version=1))
    be.write("test/file1", _node("second", version=2))
    be.write("test/file1", _node("third", version=3))
    assert be.get_versions("test/file1") == [1, 2]


def test_read_version(tmp_path):
    be = _backend(tmp_path)
    be.write("test/file1", _node("original", version=1))
    be.write("test/file1", _node("updated", version=2))
    old = be.read_version("test/file1", 1)
    assert old is not None
    assert old.content == "original"
    assert old.metadata.version == 1


def test_no_version_on_first_write(tmp_path):
    be = _backend(tmp_path)
    be.write("test/file1", _node("first", version=1))
    assert be.get_versions("test/file1") == []


def test_read_version_missing(tmp_path):
    be = _backend(tmp_path)
    assert be.read_version("test/file1", 99) is None
