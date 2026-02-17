from __future__ import annotations

from enum import Enum

from michigram.pipeline.constructor import ContextConstructor, ContextManifest


class UpdateMode(Enum):
    SNAPSHOT = "snapshot"
    INCREMENTAL = "incremental"
    ADAPTIVE = "adaptive"


class ContextUpdater:
    def __init__(self, constructor: ContextConstructor) -> None:
        self._constructor = constructor

    def update(self, project: str, token_budget: int = 8000,
               strategy: str = "recency", mode: UpdateMode = UpdateMode.SNAPSHOT,
               previous: ContextManifest | None = None) -> ContextManifest:
        if mode == UpdateMode.SNAPSHOT or previous is None:
            return self._constructor.construct(project, token_budget, strategy)

        if mode == UpdateMode.ADAPTIVE:
            return self._adaptive_update(project, token_budget, strategy, previous)

        return self._incremental_update(project, token_budget, strategy, previous)

    def _incremental_update(self, project: str, token_budget: int,
                            strategy: str, previous: ContextManifest) -> ContextManifest:
        fresh = self._constructor.construct(project, token_budget, strategy)

        prev_paths = {n.path for n in previous.items}
        new_items = [n for n in fresh.items if n.path not in prev_paths]
        retained = [n for n in previous.items if n.path in {n.path for n in fresh.items}]

        combined = retained + new_items
        total = sum(n.metadata.token_estimate for n in combined)

        while total > token_budget and combined:
            removed = combined.pop()
            total -= removed.metadata.token_estimate

        return ContextManifest(
            items=combined,
            total_tokens=total,
            strategy=strategy,
            excluded_count=fresh.excluded_count,
        )

    def _adaptive_update(self, project: str, token_budget: int,
                         strategy: str, previous: ContextManifest) -> ContextManifest:
        fresh = self._constructor.construct(project, token_budget, strategy)

        prev_by_path = {n.path: n for n in previous.items}
        fresh_by_path = {n.path: n for n in fresh.items}

        combined = []
        for path, fresh_node in fresh_by_path.items():
            prev_node = prev_by_path.get(path)
            if prev_node is None:
                combined.append(fresh_node)
            elif fresh_node.metadata.updated_at > prev_node.metadata.updated_at:
                combined.append(fresh_node)
            else:
                combined.append(prev_node)

        total = sum(n.metadata.token_estimate for n in combined)

        while total > token_budget and combined:
            removed = combined.pop()
            total -= removed.metadata.token_estimate

        return ContextManifest(
            items=combined,
            total_tokens=total,
            strategy=strategy,
            excluded_count=fresh.excluded_count,
        )

    def should_refresh(self, previous: ContextManifest, staleness_threshold: float = 0.5) -> bool:
        if not previous.items:
            return True
        max_updated = max(n.metadata.updated_at for n in previous.items)
        min_updated = min(n.metadata.updated_at for n in previous.items)
        if max_updated == min_updated:
            return False
        stale_count = sum(1 for n in previous.items if n.metadata.updated_at == min_updated)
        return (stale_count / len(previous.items)) >= staleness_threshold
