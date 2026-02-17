import json
from pathlib import Path

from michi_context_v2.afs.mount import FilesystemMount
from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.adapters.claude_code import ClaudeCodeAdapter
from michi_context_v2.pipeline.constructor import ContextConstructor
from michi_context_v2.pipeline.evaluator import ContextEvaluator
from michi_context_v2.repository.history import HistoryRepository
from michi_context_v2.repository.memory import MemoryRepository, MemoryType
from michi_context_v2.storage.filesystem import FilesystemBackend


def test_full_pipeline(tmp_path, sample_jsonl):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    history = HistoryRepository(ns)
    memory = MemoryRepository(ns)

    adapter = ClaudeCodeAdapter(history)
    sids = adapter.ingest(sample_jsonl, "testproj")
    assert len(sids) == 1
    sid = sids[0]

    node = history.get_session("testproj", sid)
    assert node is not None
    assert "Fix the bug" in node.content

    evaluator = ContextEvaluator(history, memory)
    result = evaluator.evaluate_session("testproj", sid)
    assert isinstance(result, dict)

    patterns = memory.recall_all("testproj", MemoryType.EXPERIENTIAL)
    assert len(patterns) >= 1

    constructor = ContextConstructor(history, memory)
    manifest = constructor.construct("testproj", token_budget=8000)
    assert len(manifest.items) > 0

    output = adapter.format_context(manifest)
    parsed = json.loads(output)
    assert "hookSpecificOutput" in parsed
    context = parsed["hookSpecificOutput"]["additionalContext"]
    assert len(context) > 0


def test_memory_lifecycle(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    memory = MemoryRepository(ns)

    memory.store("proj", MemoryType.FACT, "db", "PostgreSQL", tags=["infra"])
    memory.store("proj", MemoryType.FACT, "lang", "Python", tags=["tech"])
    memory.store("proj", MemoryType.EXPERIENTIAL, "pattern1", "Always run tests", tags=["workflow"])

    facts = memory.recall_all("proj", MemoryType.FACT)
    assert len(facts) == 2

    memory.update("proj", MemoryType.FACT, "db", "MySQL")
    node = memory.recall("proj", MemoryType.FACT, "db")
    assert node.content == "MySQL"
    assert node.metadata.version == 2

    memory.forget("proj", MemoryType.FACT, "lang")
    assert memory.recall("proj", MemoryType.FACT, "lang") is None

    infra = memory.search("proj", tags=["infra"])
    assert len(infra) == 1


def test_scratchpad_to_memory(tmp_path):
    backend = FilesystemBackend(tmp_path / "store")
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    memory = MemoryRepository(ns)

    from michi_context_v2.repository.scratchpad import ScratchpadRepository
    scratch = ScratchpadRepository(ns)

    scratch.create("task1", "finding", "Important: always use UTC timestamps")
    scratch.promote("task1", "finding", memory, "proj", MemoryType.FACT, "timestamp_rule")

    node = memory.recall("proj", MemoryType.FACT, "timestamp_rule")
    assert node is not None
    assert "UTC" in node.content
    assert scratch.read("task1", "finding") is None
