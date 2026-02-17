import json
import pytest
from pathlib import Path

from michigram.afs.node import ContextNode, NodeType, NodeMetadata
from michigram.core.primitives import now_iso, estimate_tokens


@pytest.fixture
def tmp_base(tmp_path):
    return tmp_path / "michi-test"


@pytest.fixture
def sample_node():
    ts = now_iso()
    return ContextNode(
        path="/context/history/testproj/session1",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(
            created_at=ts,
            updated_at=ts,
            source="test",
            token_estimate=estimate_tokens("hello world"),
            tags=["test"],
        ),
        content="hello world",
    )


@pytest.fixture
def sample_jsonl(tmp_path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    lines = [
        {"type": "summary", "summary": "Test session", "session_id": "abc123"},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll help you with that."},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/tmp/test.py"},
                    },
                ],
            },
        },
        {
            "type": "human",
            "message": {
                "role": "human",
                "content": [{"type": "text", "text": "Fix the bug in main.py"}],
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Write",
                        "input": {
                            "file_path": "/tmp/main.py",
                            "content": "print('fixed')",
                        },
                    }
                ],
            },
        },
    ]
    jsonl_file = session_dir / "test_session.jsonl"
    jsonl_file.write_text("\n".join(json.dumps(line) for line in lines))
    return jsonl_file


@pytest.fixture
def real_schema_jsonl(tmp_path):
    """JSONL fixture using real Claude Code schema (type: user, string content)."""
    session_dir = tmp_path / "real_sessions"
    session_dir.mkdir()
    lines = [
        {"type": "summary", "summary": "Real session", "session_id": "real456"},
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "Fix the TypeError in auth.py",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll fix the TypeError in auth.py."},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/src/auth.py"},
                    },
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Now run the tests"}],
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "pytest tests/"},
                    },
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "/src/auth.py"},
                    },
                ],
            },
        },
        {"type": "result", "is_error": True, "content": "ImportError: no module named foo"},
    ]
    jsonl_file = session_dir / "real_session.jsonl"
    jsonl_file.write_text("\n".join(json.dumps(line) for line in lines))
    return jsonl_file
