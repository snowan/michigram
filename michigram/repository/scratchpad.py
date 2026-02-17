from __future__ import annotations

from datetime import datetime, timezone

from michigram.afs.namespace import Namespace
from michigram.afs.node import ContextNode, NodeType, NodeMetadata
from michigram.core.primitives import now_iso, estimate_tokens
from michigram.repository.memory import MemoryRepository, MemoryType


class ScratchpadRepository:
    def __init__(self, namespace: Namespace, prefix: str = "/context/scratchpad") -> None:
        self._ns = namespace
        self._prefix = prefix

    def _path(self, task_id: str, note_id: str) -> str:
        return f"{self._prefix}/{task_id}/{note_id}"

    def create(self, task_id: str, note_id: str, content: str,
               ttl_seconds: int = 3600, tags: list[str] | None = None) -> None:
        path = self._path(task_id, note_id)
        ts = now_iso()
        node = ContextNode(
            path=path,
            node_type=NodeType.FILE,
            metadata=NodeMetadata(
                created_at=ts,
                updated_at=ts,
                source="scratchpad",
                token_estimate=estimate_tokens(content),
                tags=tags or ["scratchpad"],
                ttl_seconds=ttl_seconds,
            ),
            content=content,
        )
        self._ns.write(path, node)

    def read(self, task_id: str, note_id: str) -> ContextNode | None:
        return self._ns.read(self._path(task_id, note_id))

    def list_notes(self, task_id: str) -> list[str]:
        try:
            return self._ns.list(f"{self._prefix}/{task_id}")
        except KeyError:
            return []

    def promote(self, task_id: str, note_id: str, memory_repo: MemoryRepository,
                project: str, memory_type: MemoryType, key: str) -> bool:
        node = self.read(task_id, note_id)
        if node is None:
            return False
        memory_repo.store(project, memory_type, key, node.content or "",
                         source="promotion", tags=node.metadata.tags)
        self._ns.delete(self._path(task_id, note_id))
        return True

    def archive(self, task_id: str, note_id: str, history_ns_path: str) -> bool:
        node = self.read(task_id, note_id)
        if node is None:
            return False
        ts = now_iso()
        archived = ContextNode(
            path=history_ns_path,
            node_type=NodeType.FILE,
            metadata=NodeMetadata(
                created_at=node.metadata.created_at,
                updated_at=ts,
                source="archive",
                token_estimate=node.metadata.token_estimate,
                tags=node.metadata.tags + ["archived"],
            ),
            content=node.content,
        )
        self._ns.write(history_ns_path, archived)
        self._ns.delete(self._path(task_id, note_id))
        return True

    def gc(self) -> int:
        now = datetime.now(timezone.utc)
        removed = 0
        try:
            task_ids = self._ns.list(self._prefix)
        except KeyError:
            return 0
        for tid in task_ids:
            notes = self.list_notes(tid)
            for nid in notes:
                node = self.read(tid, nid)
                if node is None:
                    continue
                ttl = node.metadata.ttl_seconds
                if ttl is None:
                    continue
                created = datetime.fromisoformat(node.metadata.created_at)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                elapsed = (now - created).total_seconds()
                if elapsed > ttl:
                    self._ns.delete(self._path(tid, nid))
                    removed += 1
        return removed
