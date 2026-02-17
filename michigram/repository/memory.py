from __future__ import annotations

from enum import Enum

from michigram.afs.namespace import Namespace
from michigram.afs.node import ContextNode, NodeType, NodeMetadata
from michigram.core.primitives import now_iso, estimate_tokens


class MemoryType(Enum):
    FACT = "facts"
    EPISODIC = "episodic"
    EXPERIENTIAL = "experiential"
    PROCEDURAL = "procedural"
    USER = "user"


class MemoryRepository:
    def __init__(self, namespace: Namespace, prefix: str = "/context/memory") -> None:
        self._ns = namespace
        self._prefix = prefix

    def _path(self, project: str, memory_type: MemoryType, key: str) -> str:
        return f"{self._prefix}/{project}/{memory_type.value}/{key}"

    def store(self, project: str, memory_type: MemoryType, key: str, value: str,
              source: str = "user", tags: list[str] | None = None) -> None:
        path = self._path(project, memory_type, key)
        existing = self._ns.read(path)
        ts = now_iso()
        version = 1
        if existing:
            version = existing.metadata.version + 1

        node = ContextNode(
            path=path,
            node_type=NodeType.FILE,
            metadata=NodeMetadata(
                created_at=existing.metadata.created_at if existing else ts,
                updated_at=ts,
                source=source,
                token_estimate=estimate_tokens(value),
                tags=tags or [],
                version=version,
            ),
            content=value,
        )
        self._ns.write(path, node)

    def recall(self, project: str, memory_type: MemoryType, key: str) -> ContextNode | None:
        return self._ns.read(self._path(project, memory_type, key))

    def recall_all(self, project: str, memory_type: MemoryType) -> list[ContextNode]:
        try:
            keys = self._ns.list(f"{self._prefix}/{project}/{memory_type.value}")
        except KeyError:
            return []
        results = []
        for k in keys:
            node = self.recall(project, memory_type, k)
            if node:
                results.append(node)
        return results

    def update(self, project: str, memory_type: MemoryType, key: str, value: str,
               source: str = "evaluator") -> bool:
        existing = self.recall(project, memory_type, key)
        if existing is None:
            return False
        self.store(project, memory_type, key, value, source=source, tags=existing.metadata.tags)
        return True

    def forget(self, project: str, memory_type: MemoryType, key: str) -> bool:
        path = self._path(project, memory_type, key)
        return self._ns.delete(path)

    def store_procedural(self, project: str, tool_name: str, description: str,
                         usage_example: str = "", tags: list[str] | None = None) -> None:
        import json
        value = json.dumps({"tool": tool_name, "description": description, "usage": usage_example})
        self.store(project, MemoryType.PROCEDURAL, tool_name, value,
                   source="procedural", tags=tags or ["tool"])

    def recall_procedural(self, project: str, tool_name: str) -> dict | None:
        import json
        node = self.recall(project, MemoryType.PROCEDURAL, tool_name)
        if node and node.content:
            return json.loads(node.content)
        return None

    def store_user_preference(self, project: str, pref_key: str, pref_value: str,
                              tags: list[str] | None = None) -> None:
        self.store(project, MemoryType.USER, pref_key, pref_value,
                   source="user", tags=tags or ["preference"])

    def recall_user_preferences(self, project: str) -> dict[str, str]:
        nodes = self.recall_all(project, MemoryType.USER)
        return {n.path.split("/")[-1]: (n.content or "") for n in nodes}

    def search(self, project: str, tags: list[str] | None = None,
               source: str | None = None, since: str | None = None) -> list[ContextNode]:
        try:
            return self._ns.search(f"{self._prefix}/{project}", tags=tags, source=source, since=since)
        except KeyError:
            return []
