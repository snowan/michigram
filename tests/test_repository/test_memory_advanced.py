from michigram.afs.namespace import Namespace
from michigram.afs.mount import FilesystemMount
from michigram.storage.filesystem import FilesystemBackend
from michigram.repository.memory import MemoryRepository, MemoryType


def _make_repo(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    return MemoryRepository(ns)


def test_store_procedural(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store_procedural("proj", "grep", "Search files", usage_example="grep -r pattern .")
    node = repo.recall("proj", MemoryType.PROCEDURAL, "grep")
    assert node is not None
    assert '"tool": "grep"' in node.content
    assert node.metadata.source == "procedural"
    assert "tool" in node.metadata.tags


def test_recall_procedural(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store_procedural("proj", "ripgrep", "Fast search", usage_example="rg pattern")
    result = repo.recall_procedural("proj", "ripgrep")
    assert result is not None
    assert result["tool"] == "ripgrep"
    assert result["description"] == "Fast search"
    assert result["usage"] == "rg pattern"


def test_recall_procedural_missing(tmp_path):
    repo = _make_repo(tmp_path)
    assert repo.recall_procedural("proj", "nonexistent") is None


def test_store_user_preference(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store_user_preference("proj", "theme", "dark")
    node = repo.recall("proj", MemoryType.USER, "theme")
    assert node is not None
    assert node.content == "dark"
    assert node.metadata.source == "user"
    assert "preference" in node.metadata.tags


def test_recall_user_preferences(tmp_path):
    repo = _make_repo(tmp_path)
    repo.store_user_preference("proj", "theme", "dark")
    repo.store_user_preference("proj", "language", "python")
    prefs = repo.recall_user_preferences("proj")
    assert prefs == {"theme": "dark", "language": "python"}
