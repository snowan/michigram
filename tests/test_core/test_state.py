from michi_context_v2.core.state import get_state, save_state


def test_get_state_default(tmp_path):
    state = get_state(tmp_path)
    assert "captured_sessions" in state
    assert "project_map" in state
    assert "evaluated_sessions" in state


def test_save_and_load(tmp_path):
    state = get_state(tmp_path)
    state["captured_sessions"]["proj:abc"] = {"mtime": 123, "file": "test.md"}
    save_state(tmp_path, state)
    loaded = get_state(tmp_path)
    assert loaded["captured_sessions"]["proj:abc"]["mtime"] == 123


def test_state_roundtrip(tmp_path):
    state = {
        "captured_sessions": {"a": 1},
        "project_map": {"b": 2},
        "evaluated_sessions": {"c": 3},
    }
    save_state(tmp_path, state)
    loaded = get_state(tmp_path)
    assert loaded == state
