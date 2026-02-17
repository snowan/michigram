from __future__ import annotations

from dataclasses import dataclass, field

from michi_context_v2.afs.node import ContextNode
from michi_context_v2.repository.history import HistoryRepository
from michi_context_v2.repository.memory import MemoryRepository, MemoryType


@dataclass
class ContextManifest:
    items: list[ContextNode] = field(default_factory=list)
    total_tokens: int = 0
    strategy: str = "recency"
    excluded_count: int = 0


MEMORY_TYPE_PRIORITY = {
    MemoryType.FACT: 1,
    MemoryType.EXPERIENTIAL: 2,
    MemoryType.EPISODIC: 3,
    MemoryType.PROCEDURAL: 4,
    MemoryType.USER: 5,
}


class ContextConstructor:
    def __init__(self, history: HistoryRepository, memory: MemoryRepository) -> None:
        self._history = history
        self._memory = memory

    def construct(self, project: str, token_budget: int = 8000,
                  strategy: str = "recency") -> ContextManifest:
        candidates: list[ContextNode] = []

        for mt in MemoryType:
            candidates.extend(self._memory.recall_all(project, mt))

        session_ids = self._history.list_sessions(project)
        for sid in session_ids:
            node = self._history.get_session(project, sid)
            if node:
                candidates.append(node)

        scored = self._score(candidates, strategy)

        items: list[ContextNode] = []
        total = 0
        excluded = 0
        for node in scored:
            cost = node.metadata.token_estimate
            if total + cost <= token_budget:
                items.append(node)
                total += cost
            else:
                excluded += 1

        return ContextManifest(
            items=items,
            total_tokens=total,
            strategy=strategy,
            excluded_count=excluded,
        )

    def _score(self, candidates: list[ContextNode], strategy: str) -> list[ContextNode]:
        if strategy == "recency":
            return sorted(candidates, key=lambda n: n.metadata.updated_at, reverse=True)

        if strategy == "relevance":
            def relevance_key(n: ContextNode) -> tuple[int, str]:
                for mt in MemoryType:
                    if f"/{mt.value}/" in n.path:
                        return (MEMORY_TYPE_PRIORITY.get(mt, 99), n.metadata.updated_at)
                return (100, n.metadata.updated_at)
            return sorted(candidates, key=relevance_key)

        return sorted(candidates, key=lambda n: n.metadata.updated_at, reverse=True)
