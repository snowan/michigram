from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.afs.mount import FilesystemMount
from michi_context_v2.storage.filesystem import FilesystemBackend
from michi_context_v2.repository.memory import MemoryRepository, MemoryType


def _make_repo(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    return MemoryRepository(ns)


def test_store_and_recall(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store("proj", MemoryType.FACT, "db_engine", "PostgreSQL")
    node = repo.recall("proj", MemoryType.FACT, "db_engine")
    assert node is not None
    assert node.content == "PostgreSQL"


def test_recall_missing(tmp_path):
    repo = _make_repo(tmp_path)
    assert repo.recall("proj", MemoryType.FACT, "missing") is None


def test_recall_all(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store("proj", MemoryType.FACT, "a", "val_a")
    repo.store("proj", MemoryType.FACT, "b", "val_b")
    nodes = repo.recall_all("proj", MemoryType.FACT)
    assert len(nodes) == 2


def test_update(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store("proj", MemoryType.FACT, "key1", "v1")
    assert repo.update("proj", MemoryType.FACT, "key1", "v2")
    node = repo.recall("proj", MemoryType.FACT, "key1")
    assert node.content == "v2"
    assert node.metadata.version == 2


def test_update_missing(tmp_path):
    repo = _make_repo(tmp_path)
    assert repo.update("proj", MemoryType.FACT, "nope", "val") is False


def test_forget(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store("proj", MemoryType.EPISODIC, "ep1", "episode data")
    assert repo.forget("proj", MemoryType.EPISODIC, "ep1") is True
    assert repo.recall("proj", MemoryType.EPISODIC, "ep1") is None


def test_forget_missing(tmp_path):
    repo = _make_repo(tmp_path)
    assert repo.forget("proj", MemoryType.FACT, "nope") is False


def test_search_by_tags(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store("proj", MemoryType.EXPERIENTIAL, "p1", "pattern", tags=["error"])
    repo.store("proj", MemoryType.EXPERIENTIAL, "p2", "other", tags=["info"])
    results = repo.search("proj", tags=["error"])
    assert len(results) == 1
    assert results[0].content == "pattern"


def test_version_increments(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store("proj", MemoryType.FACT, "x", "v1")
    repo.store("proj", MemoryType.FACT, "x", "v2")
    repo.store("proj", MemoryType.FACT, "x", "v3")
    node = repo.recall("proj", MemoryType.FACT, "x")
    assert node.metadata.version == 3
