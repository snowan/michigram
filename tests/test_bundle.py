from pathlib import Path

from michi_context_v2.afs.mount import FilesystemMount
from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata
from michi_context_v2.bundle import export_bundle, import_bundle
from michi_context_v2.core.primitives import now_iso
from michi_context_v2.storage.filesystem import FilesystemBackend


def _make_ns(tmp_path, name="store"):
    backend = FilesystemBackend(tmp_path / name)
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    return ns


def _add_nodes(ns, project, count=3):
    ts = now_iso()
    for i in range(count):
        node = ContextNode(
            path=f"/context/memory/{project}/facts/key{i}",
            node_type=NodeType.FILE,
            metadata=NodeMetadata(created_at=ts, updated_at=ts, source="test", tags=["test"]),
            content=f"value {i}",
        )
        ns.write(node.path, node)


def test_export_bundle(tmp_path):
    ns = _make_ns(tmp_path)
    _add_nodes(ns, "proj", 3)
    out = tmp_path / "export.tar.gz"
    count = export_bundle(ns, "/context/memory/proj", out)
    assert count == 3
    assert out.exists()


def test_import_bundle(tmp_path):
    ns1 = _make_ns(tmp_path, "store1")
    _add_nodes(ns1, "proj", 2)
    bundle = tmp_path / "bundle.tar.gz"
    export_bundle(ns1, "/context/memory/proj", bundle)

    ns2 = _make_ns(tmp_path, "store2")
    imported = import_bundle(ns2, bundle)
    assert imported == 2

    node = ns2.read("/context/memory/proj/facts/key0")
    assert node is not None
    assert node.content == "value 0"


def test_export_empty(tmp_path):
    ns = _make_ns(tmp_path)
    out = tmp_path / "empty.tar.gz"
    count = export_bundle(ns, "/context/nonexistent", out)
    assert count == 0


def test_roundtrip(tmp_path):
    ns = _make_ns(tmp_path, "original")
    _add_nodes(ns, "myproj", 5)
    bundle = tmp_path / "roundtrip.tar.gz"
    exported = export_bundle(ns, "/context/memory/myproj", bundle)

    ns2 = _make_ns(tmp_path, "restored")
    imported = import_bundle(ns2, bundle)
    assert exported == imported

    for i in range(5):
        node = ns2.read(f"/context/memory/myproj/facts/key{i}")
        assert node is not None
        assert node.content == f"value {i}"
