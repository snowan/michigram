from michigram.afs.namespace import Namespace
from michigram.afs.mount import FilesystemMount
from michigram.storage.filesystem import FilesystemBackend
from michigram.repository.history import HistoryRepository
from michigram.repository.memory import MemoryRepository, MemoryType
from michigram.pipeline.constructor import ContextConstructor


def _setup(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    history = HistoryRepository(ns)
    memory = MemoryRepository(ns)
    return ContextConstructor(history, memory), history, memory


def test_empty_construct(tmp_path):
    constructor, _, _ = _setup(tmp_path)
    manifest = constructor.construct("proj")
    assert manifest.items == []
    assert manifest.total_tokens == 0


def test_construct_with_memory(tmp_path):
    constructor, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "db", "PostgreSQL")
    memory.store("proj", MemoryType.FACT, "lang", "Python")
    manifest = constructor.construct("proj", token_budget=8000)
    assert len(manifest.items) == 2
    assert manifest.total_tokens > 0


def test_construct_respects_budget(tmp_path):
    constructor, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "big", "x" * 1000)
    memory.store("proj", MemoryType.FACT, "small", "y")
    manifest = constructor.construct("proj", token_budget=100)
    assert manifest.total_tokens <= 100
    assert manifest.excluded_count >= 1


def test_construct_with_history(tmp_path, sample_jsonl):
    constructor, history, _ = _setup(tmp_path)
    history.ingest_session(sample_jsonl, "proj")
    manifest = constructor.construct("proj")
    assert len(manifest.items) >= 1


def test_construct_relevance_strategy(tmp_path):
    constructor, _, memory = _setup(tmp_path)
    memory.store("proj", MemoryType.FACT, "f1", "fact value")
    memory.store("proj", MemoryType.EXPERIENTIAL, "p1", "pattern value")
    manifest = constructor.construct("proj", strategy="relevance")
    assert manifest.strategy == "relevance"
    assert len(manifest.items) == 2
    assert "/facts/" in manifest.items[0].path
