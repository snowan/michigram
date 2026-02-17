from __future__ import annotations
import json
from pathlib import Path
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata, node_to_dict, node_from_dict
from michi_context_v2.core.primitives import atomic_write
from michi_context_v2.storage.base import StorageBackend

class FilesystemBackend(StorageBackend):
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _content_path(self, rel_path: str) -> Path:
        return self._root / rel_path

    def _meta_path(self, rel_path: str) -> Path:
        return self._root / f"{rel_path}.meta.json"

    def read(self, rel_path: str) -> ContextNode | None:
        cp = self._content_path(rel_path)
        mp = self._meta_path(rel_path)
        if not mp.exists():
            return None
        meta_data = json.loads(mp.read_text())
        content = cp.read_text() if cp.exists() else None
        meta = NodeMetadata(
            created_at=meta_data["created_at"],
            updated_at=meta_data["updated_at"],
            source=meta_data.get("source", ""),
            content_type=meta_data.get("content_type", "text/plain"),
            token_estimate=meta_data.get("token_estimate", 0),
            tags=meta_data.get("tags", []),
            ttl_seconds=meta_data.get("ttl_seconds"),
            version=meta_data.get("version", 1),
            extra=meta_data.get("extra", {}),
        )
        node_type = NodeType(meta_data.get("node_type", "file"))
        path_str = meta_data.get("path", rel_path)
        return ContextNode(path=path_str, node_type=node_type, metadata=meta, content=content)

    def _version_dir(self, rel_path: str) -> Path:
        return self._root / ".versions" / rel_path

    def write(self, rel_path: str, node: ContextNode) -> None:
        cp = self._content_path(rel_path)
        mp = self._meta_path(rel_path)

        existing = self.read(rel_path)
        if existing is not None:
            vdir = self._version_dir(rel_path)
            vdir.mkdir(parents=True, exist_ok=True)
            old_ver = existing.metadata.version
            if existing.content is not None:
                atomic_write(vdir / f"v{old_ver}", existing.content)
            atomic_write(vdir / f"v{old_ver}.meta.json", json.dumps({
                "path": existing.path,
                "node_type": existing.node_type.value,
                "created_at": existing.metadata.created_at,
                "updated_at": existing.metadata.updated_at,
                "source": existing.metadata.source,
                "content_type": existing.metadata.content_type,
                "token_estimate": existing.metadata.token_estimate,
                "tags": existing.metadata.tags,
                "ttl_seconds": existing.metadata.ttl_seconds,
                "version": existing.metadata.version,
                "extra": existing.metadata.extra,
            }, indent=2))

        cp.parent.mkdir(parents=True, exist_ok=True)

        if node.content is not None:
            atomic_write(cp, node.content)

        meta_dict = {
            "path": node.path,
            "node_type": node.node_type.value,
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
        atomic_write(mp, json.dumps(meta_dict, indent=2))

    def get_versions(self, rel_path: str) -> list[int]:
        vdir = self._version_dir(rel_path)
        if not vdir.exists():
            return []
        versions = []
        for f in vdir.iterdir():
            if f.suffix == ".json":
                continue
            if f.name.startswith("v") and not f.name.endswith(".tmp"):
                try:
                    versions.append(int(f.name[1:]))
                except ValueError:
                    continue
        return sorted(versions)

    def read_version(self, rel_path: str, version: int) -> ContextNode | None:
        vdir = self._version_dir(rel_path)
        content_file = vdir / f"v{version}"
        meta_file = vdir / f"v{version}.meta.json"
        if not meta_file.exists():
            return None
        meta_data = json.loads(meta_file.read_text())
        content = content_file.read_text() if content_file.exists() else None
        meta = NodeMetadata(
            created_at=meta_data["created_at"],
            updated_at=meta_data["updated_at"],
            source=meta_data.get("source", ""),
            content_type=meta_data.get("content_type", "text/plain"),
            token_estimate=meta_data.get("token_estimate", 0),
            tags=meta_data.get("tags", []),
            ttl_seconds=meta_data.get("ttl_seconds"),
            version=meta_data.get("version", 1),
            extra=meta_data.get("extra", {}),
        )
        node_type = NodeType(meta_data.get("node_type", "file"))
        path_str = meta_data.get("path", rel_path)
        return ContextNode(path=path_str, node_type=node_type, metadata=meta, content=content)

    def list(self, rel_path: str) -> list[str]:
        target = self._root / rel_path if rel_path else self._root
        if not target.exists() or not target.is_dir():
            return []
        results = []
        for item in sorted(target.iterdir()):
            if item.name.endswith(".meta.json"):
                continue
            results.append(item.name)
        return results

    def delete(self, rel_path: str) -> bool:
        cp = self._content_path(rel_path)
        mp = self._meta_path(rel_path)
        deleted = False
        if cp.exists():
            cp.unlink()
            deleted = True
        if mp.exists():
            mp.unlink()
            deleted = True
        return deleted

    def search(self, rel_path: str, tags: list[str] | None = None,
               source: str | None = None, since: str | None = None) -> list[ContextNode]:
        target = self._root / rel_path if rel_path else self._root
        if not target.exists():
            return []
        results = []
        meta_files = sorted(target.rglob("*.meta.json"))
        for mf in meta_files:
            rel = str(mf.relative_to(self._root))
            content_rel = rel[:-len(".meta.json")]
            node = self.read(content_rel)
            if node is None:
                continue
            if tags and not set(tags).issubset(set(node.metadata.tags)):
                continue
            if source and node.metadata.source != source:
                continue
            if since and node.metadata.updated_at < since:
                continue
            results.append(node)
        return results
