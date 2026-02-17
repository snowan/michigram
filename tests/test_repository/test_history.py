from michigram.afs.namespace import Namespace
from michigram.afs.mount import FilesystemMount
from michigram.storage.filesystem import FilesystemBackend
from michigram.repository.history import HistoryRepository


def _make_repo(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    return HistoryRepository(ns)


def test_ingest_session(tmp_path, sample_jsonl):
    repo = _make_repo(tmp_path)
    sid = repo.ingest_session(sample_jsonl, "testproj")
    assert sid == "abc123"


def test_get_session(tmp_path, sample_jsonl):
    repo = _make_repo(tmp_path)
    sid = repo.ingest_session(sample_jsonl, "testproj")
    node = repo.get_session("testproj", sid)
    assert node is not None
    assert "Fix the bug" in node.content
    assert "session" in node.metadata.tags


def test_list_sessions(tmp_path, sample_jsonl):
    repo = _make_repo(tmp_path)
    repo.ingest_session(sample_jsonl, "testproj")
    sessions = repo.list_sessions("testproj")
    assert len(sessions) == 1


def test_prune(tmp_path, sample_jsonl):
    repo = _make_repo(tmp_path)
    repo.ingest_session(sample_jsonl, "testproj")
    pruned = repo.prune("testproj", before="2099-01-01T00:00:00Z")
    assert pruned == 1
    assert repo.list_sessions("testproj") == []


def test_prune_none_old_enough(tmp_path, sample_jsonl):
    repo = _make_repo(tmp_path)
    repo.ingest_session(sample_jsonl, "testproj")
    pruned = repo.prune("testproj", before="2020-01-01T00:00:00Z")
    assert pruned == 0


def test_list_sessions_empty(tmp_path):
    repo = _make_repo(tmp_path)
    assert repo.list_sessions("nonexistent") == []


def test_ingest_user_type_string_content(tmp_path, real_schema_jsonl):
    repo = _make_repo(tmp_path)
    sid = repo.ingest_session(real_schema_jsonl, "testproj")
    assert sid == "real456"
    node = repo.get_session("testproj", sid)
    assert node is not None
    assert "Fix the TypeError" in node.content


def test_ingest_extracts_bash_glob_grep(tmp_path, real_schema_jsonl):
    repo = _make_repo(tmp_path)
    sid = repo.ingest_session(real_schema_jsonl, "testproj")
    node = repo.get_session("testproj", sid)
    assert "Bash:" in node.content
    assert "Edit:" in node.content


def test_ingest_extracts_errors(tmp_path, real_schema_jsonl):
    repo = _make_repo(tmp_path)
    sid = repo.ingest_session(real_schema_jsonl, "testproj")
    node = repo.get_session("testproj", sid)
    assert "ImportError" in node.content
