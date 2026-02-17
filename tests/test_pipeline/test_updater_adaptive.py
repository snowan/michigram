from michigram.afs.namespace import Namespace
from michigram.afs.mount import FilesystemMount
from michigram.storage.filesystem import FilesystemBackend
from michigram.repository.history import HistoryRepository
from michigram.repository.memory import MemoryRepository, MemoryType
from michigram.pipeline.constructor import ContextConstructor, ContextManifest
from michigram.pipeline.updater import ContextUpdater, UpdateMode
from michigram.afs.node import ContextNode, NodeType, NodeMetadata


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


def test_adaptive_mode(tmp_path):
    updater, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "k1", "v1")
    prev = updater.update("proj", mode=UpdateMode.SNAPSHOT)
    memory.store("proj", MemoryType.FACT, "k2", "v2")
    result = updater.update("proj", mode=UpdateMode.ADAPTIVE, previous=prev)
    paths = {n.path for n in result.items}
    assert any("k1" in p for p in paths)
    assert any("k2" in p for p in paths)


def test_adaptive_replaces_stale(tmp_path):
    updater, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "key", "old_value")
    prev = updater.update("proj", mode=UpdateMode.SNAPSHOT)

    memory.store("proj", MemoryType.FACT, "key", "new_value")
    result = updater.update("proj", mode=UpdateMode.ADAPTIVE, previous=prev)

    key_nodes = [n for n in result.items if "key" in n.path]
    assert len(key_nodes) == 1
    assert key_nodes[0].content == "new_value"
    assert key_nodes[0].metadata.version == 2


def test_adaptive_falls_back_without_previous(tmp_path):
    updater, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "k", "v")
    manifest = updater.update("proj", mode=UpdateMode.ADAPTIVE, previous=None)
    assert len(manifest.items) == 1
