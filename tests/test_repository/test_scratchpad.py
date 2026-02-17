import time
from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.afs.mount import FilesystemMount
from michi_context_v2.storage.filesystem import FilesystemBackend
from michi_context_v2.repository.scratchpad import ScratchpadRepository
from michi_context_v2.repository.memory import MemoryRepository, MemoryType


def _make_repos(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    scratch = ScratchpadRepository(ns)
    memory = MemoryRepository(ns)
    return scratch, memory, ns


def test_create_and_read(tmp_path):
    scratch, _, _ = _make_repos(tmp_path)
    scratch.create("task1", "note1", "some notes")
    node = scratch.read("task1", "note1")
    assert node is not None
    assert node.content == "some notes"


def test_list_notes(tmp_path):
    scratch, _, _ = _make_repos(tmp_path)
    scratch.create("task1", "n1", "a")
    scratch.create("task1", "n2", "b")
    notes = scratch.list_notes("task1")
    assert len(notes) == 2


def test_promote(tmp_path):
    scratch, memory, _ = _make_repos(tmp_path)
    scratch.create("task1", "note1", "important finding", tags=["discovery"])
    result = scratch.promote("task1", "note1", memory, "proj", MemoryType.FACT, "finding1")
    assert result is True
    assert scratch.read("task1", "note1") is None
    node = memory.recall("proj", MemoryType.FACT, "finding1")
    assert node is not None
    assert node.content == "important finding"


def test_promote_missing(tmp_path):
    scratch, memory, _ = _make_repos(tmp_path)
    assert scratch.promote("task1", "nope", memory, "proj", MemoryType.FACT, "k") is False


def test_archive(tmp_path):
    scratch, _, ns = _make_repos(tmp_path)
    scratch.create("task1", "note1", "archived data")
    result = scratch.archive("task1", "note1", "/context/history/proj/archived_note")
    assert result is True
    assert scratch.read("task1", "note1") is None
    archived = ns.read("/context/history/proj/archived_note")
    assert archived is not None
    assert archived.content == "archived data"
    assert "archived" in archived.metadata.tags


def test_gc_expired(tmp_path):
    scratch, _, _ = _make_repos(tmp_path)
    scratch.create("task1", "old_note", "expired", ttl_seconds=0)
    time.sleep(0.1)
    removed = scratch.gc()
    assert removed == 1
    assert scratch.read("task1", "old_note") is None


def test_gc_not_expired(tmp_path):
    scratch, _, _ = _make_repos(tmp_path)
    scratch.create("task1", "fresh", "still good", ttl_seconds=9999)
    removed = scratch.gc()
    assert removed == 0
    assert scratch.read("task1", "fresh") is not None
