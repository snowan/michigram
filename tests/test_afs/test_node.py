from michi_context_v2.afs.node import (
    ContextNode, NodeType, NodeMetadata, node_to_dict, node_from_dict,
)


def test_node_roundtrip():
    node = ContextNode(
        path="/context/test/item",
        node_type=NodeType.FILE,
        metadata=NodeMetadata(
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            source="test",
            tags=["a", "b"],
        ),
        content="hello",
    )
    d = node_to_dict(node)
    restored = node_from_dict(d)
    assert restored.path == node.path
    assert restored.node_type == node.node_type
    assert restored.content == node.content
    assert restored.metadata.tags == ["a", "b"]
    assert restored.metadata.source == "test"


def test_node_from_dict_defaults():
    d = {
        "path": "/test",
        "node_type": "file",
        "metadata": {
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }
    node = node_from_dict(d)
    assert node.metadata.source == ""
    assert node.metadata.tags == []
    assert node.metadata.version == 1
    assert node.content is None


def test_node_type_values():
    assert NodeType.FILE.value == "file"
    assert NodeType.DIRECTORY.value == "directory"
