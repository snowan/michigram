from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import json

class NodeType(Enum):
    FILE = "file"
    DIRECTORY = "directory"

@dataclass
class NodeMetadata:
    created_at: str               # ISO 8601
    updated_at: str
    source: str = ""              # "claude-code", "user", "evaluator"
    content_type: str = "text/plain"
    token_estimate: int = 0
    tags: list[str] = field(default_factory=list)
    ttl_seconds: int | None = None
    version: int = 1
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass
class ContextNode:
    path: str                     # e.g. /context/history/myproject/abc123
    node_type: NodeType
    metadata: NodeMetadata
    content: str | None = None

def node_to_dict(node: ContextNode) -> dict[str, Any]:
    """Serialize a ContextNode to a plain dict."""
    return {
        "path": node.path,
        "node_type": node.node_type.value,
        "metadata": {
            "created_at": node.metadata.created_at,
            "updated_at": node.metadata.updated_at,
            "source": node.metadata.source,
            "content_type": node.metadata.content_type,
            "token_estimate": node.metadata.token_estimate,
            "tags": node.metadata.tags,
            "ttl_seconds": node.metadata.ttl_seconds,
            "version": node.metadata.version,
            "extra": node.metadata.extra,
        },
        "content": node.content,
    }

def node_from_dict(data: dict[str, Any]) -> ContextNode:
    """Deserialize a ContextNode from a plain dict."""
    meta = data["metadata"]
    return ContextNode(
        path=data["path"],
        node_type=NodeType(data["node_type"]),
        metadata=NodeMetadata(
            created_at=meta["created_at"],
            updated_at=meta["updated_at"],
            source=meta.get("source", ""),
            content_type=meta.get("content_type", "text/plain"),
            token_estimate=meta.get("token_estimate", 0),
            tags=meta.get("tags", []),
            ttl_seconds=meta.get("ttl_seconds"),
            version=meta.get("version", 1),
            extra=meta.get("extra", {}),
        ),
        content=data.get("content"),
    )
