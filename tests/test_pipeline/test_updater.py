from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.afs.mount import FilesystemMount
from michi_context_v2.storage.filesystem import FilesystemBackend
from michi_context_v2.repository.history import HistoryRepository
from michi_context_v2.repository.memory import MemoryRepository, MemoryType
from michi_context_v2.pipeline.constructor import ContextConstructor, ContextManifest
from michi_context_v2.pipeline.updater import ContextUpdater, UpdateMode
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata


def _setup(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    history = HistoryRepository(ns)
    memory = MemoryRepository(ns)
    constructor = ContextConstructor(history, memory)
    updater = ContextUpdater(constructor)
    return updater, history, memory


def test_snapshot_mode(tmp_path):
    updater, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "k", "v")
    manifest = updater.update("proj", mode=UpdateMode.SNAPSHOT)
    assert len(manifest.items) == 1


def test_incremental_mode(tmp_path):
    updater, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "k1", "v1")
    prev = updater.update("proj", mode=UpdateMode.SNAPSHOT)
    memory.store("proj", MemoryType.FACT, "k2", "v2")
    updated = updater.update("proj", mode=UpdateMode.INCREMENTAL, previous=prev)
    assert len(updated.items) >= 1


def test_incremental_falls_back_without_previous(tmp_path):
    updater, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "k", "v")
    manifest = updater.update("proj", mode=UpdateMode.INCREMENTAL, previous=None)
    assert len(manifest.items) == 1


def test_should_refresh_empty():
    manifest = ContextManifest(items=[], total_tokens=0)
    updater = ContextUpdater(None)
    assert updater.should_refresh(manifest) is True


def test_should_refresh_all_same_time():
    ts = "2026-01-01T00:00:00Z"
    items = [
        ContextNode(
            path=f"/test/{i}", node_type=NodeType.FILE,
            metadata=NodeMetadata(created_at=ts, updated_at=ts),
            content="x",
        )
        for i in range(3)
    ]
    manifest = ContextManifest(items=items, total_tokens=3)
    updater = ContextUpdater(None)
    assert updater.should_refresh(manifest) is False
