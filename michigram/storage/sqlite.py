from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from michigram.afs.node import ContextNode, NodeType, NodeMetadata
from michigram.storage.base import StorageBackend

class SqliteBackend(StorageBackend):
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS nodes ("
            "  path TEXT PRIMARY KEY,"
            "  node_type TEXT NOT NULL,"
            "  content TEXT,"
            "  metadata TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def read(self, rel_path: str) -> ContextNode | None:
        row = self._conn.execute(
            "SELECT path, node_type, content, metadata FROM nodes WHERE path = ?",
            (rel_path,)
        ).fetchone()
        if row is None:
            return None
        path, node_type, content, meta_json = row
        meta = json.loads(meta_json)
        return ContextNode(
            path=path,
            node_type=NodeType(node_type),
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
            content=content,
        )

    def write(self, rel_path: str, node: ContextNode) -> None:
        meta_dict = {
            "created_at": node.metadata.created_at,
            "updated_at": node.metadata.updated_at,
            "source": node.metadata.source,
            "content_type": node.metadata.content_type,
            "token_estimate": node.metadata.token_estimate,
            "tags": node.metadata.tags,
            "ttl_seconds": node.metadata.ttl_seconds,
            "version": node.metadata.version,
            "extra": node.metadata.extra,
        }
        self._conn.execute(
            "INSERT OR REPLACE INTO nodes (path, node_type, content, metadata) VALUES (?, ?, ?, ?)",
            (rel_path, node.node_type.value, node.content, json.dumps(meta_dict))
        )
        self._conn.commit()

    def list(self, rel_path: str) -> list[str]:
        prefix = f"{rel_path}/" if rel_path else ""
        rows = self._conn.execute(
            "SELECT path FROM nodes WHERE path LIKE ? ORDER BY path",
            (f"{prefix}%",)
        ).fetchall()
        names = set()
        for (path,) in rows:
            rest = path[len(prefix):]
            parts = rest.split("/")
            names.add(parts[0])
        return sorted(names)

    def delete(self, rel_path: str) -> bool:
        cursor = self._conn.execute("DELETE FROM nodes WHERE path = ?", (rel_path,))
        self._conn.commit()
        return cursor.rowcount > 0

    def search(self, rel_path: str, tags: list[str] | None = None,
               source: str | None = None, since: str | None = None) -> list[ContextNode]:
        prefix = f"{rel_path}/" if rel_path else ""
        rows = self._conn.execute(
            "SELECT path, node_type, content, metadata FROM nodes WHERE path LIKE ? ORDER BY path",
            (f"{prefix}%",)
        ).fetchall()
        results = []
        for path, node_type, content, meta_json in rows:
            meta = json.loads(meta_json)
            node = ContextNode(
                path=path,
                node_type=NodeType(node_type),
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
                content=content,
            )
            if tags and not set(tags).issubset(set(node.metadata.tags)):
                continue
            if source and node.metadata.source != source:
                continue
            if since and node.metadata.updated_at < since:
                continue
            results.append(node)
        return results

    def close(self) -> None:
        self._conn.close()
