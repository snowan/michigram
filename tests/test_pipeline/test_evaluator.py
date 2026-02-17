from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.afs.mount import FilesystemMount
from michi_context_v2.storage.filesystem import FilesystemBackend
from michi_context_v2.repository.history import HistoryRepository
from michi_context_v2.repository.memory import MemoryRepository, MemoryType
from michi_context_v2.pipeline.evaluator import ContextEvaluator


def _setup(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    history = HistoryRepository(ns)
    memory = MemoryRepository(ns)
    evaluator = ContextEvaluator(history, memory)
    return evaluator, history, memory


def test_evaluate_session(tmp_path, sample_jsonl):
    evaluator, history, memory = _setup(tmp_path)
    sid = history.ingest_session(sample_jsonl, "proj")
    result = evaluator.evaluate_session("proj", sid)
    assert isinstance(result, dict)
    assert "facts" in result
    assert "patterns" in result
    assert "errors" in result


def test_evaluate_missing_session(tmp_path):
    evaluator, _, _ = _setup(tmp_path)
    result = evaluator.evaluate_session("proj", "nonexistent")
    assert result == {"facts": 0, "patterns": 0, "errors": 0}


def test_evaluate_extracts_patterns(tmp_path, sample_jsonl):
    evaluator, history, memory = _setup(tmp_path)
    sid = history.ingest_session(sample_jsonl, "proj")
    evaluator.evaluate_session("proj", sid)
    patterns = memory.recall_all("proj", MemoryType.EXPERIENTIAL)
    assert len(patterns) >= 1


def test_continuous_learn(tmp_path, sample_jsonl):
    evaluator, history, _ = _setup(tmp_path)
    history.ingest_session(sample_jsonl, "proj")
    evaluated = set()
    result = evaluator.continuous_learn("proj", evaluated)
    assert len(evaluated) == 1
    result2 = evaluator.continuous_learn("proj", evaluated)
    assert result2["facts"] == 0
    assert result2["patterns"] == 0


def test_detect_drift(tmp_path, sample_jsonl):
    evaluator, history, _ = _setup(tmp_path)
    history.ingest_session(sample_jsonl, "proj")
    evaluator.evaluate_session("proj", "abc123")
    signals = evaluator.detect_drift("proj")
    assert isinstance(signals, list)


def test_evaluate_extracts_prompts_as_facts(tmp_path, sample_jsonl):
    evaluator, history, memory = _setup(tmp_path)
    sid = history.ingest_session(sample_jsonl, "proj")
    result = evaluator.evaluate_session("proj", sid)
    assert result["facts"] >= 1
    facts = memory.recall_all("proj", MemoryType.FACT)
    fact_values = [f.content for f in facts]
    assert any("Goal:" in v for v in fact_values)


def test_evaluate_extracts_error_types(tmp_path, real_schema_jsonl):
    evaluator, history, memory = _setup(tmp_path)
    sid = history.ingest_session(real_schema_jsonl, "proj")
    result = evaluator.evaluate_session("proj", sid)
    assert result["facts"] >= 1
    facts = memory.recall_all("proj", MemoryType.FACT)
    fact_values = [f.content for f in facts]
    assert any("ImportError" in v for v in fact_values)


def test_evaluate_extracts_file_paths(tmp_path, real_schema_jsonl):
    evaluator, history, memory = _setup(tmp_path)
    sid = history.ingest_session(real_schema_jsonl, "proj")
    result = evaluator.evaluate_session("proj", sid)
    facts = memory.recall_all("proj", MemoryType.FACT)
    fact_values = [f.content for f in facts]
    assert any("Project dir:" in v or "File type:" in v for v in fact_values)


def test_dedup_file_patterns(tmp_path):
    """Different orderings of same files should produce same hash."""
    evaluator, history, memory = _setup(tmp_path)
    from michi_context_v2.pipeline.evaluator import ContextEvaluator

    content_a = "## File Operations\n- Read: /a.py\n- Write: /b.py\n- Read: /a.py\n"
    content_b = "## File Operations\n- Write: /b.py\n- Read: /a.py\n"

    patterns_a = evaluator._extract_patterns(content_a)
    patterns_b = evaluator._extract_patterns(content_b)

    assert patterns_a.keys() == patterns_b.keys()
