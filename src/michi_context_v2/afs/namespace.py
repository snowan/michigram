from __future__ import annotations
from michi_context_v2.afs.mount import MountPoint
from michi_context_v2.afs.node import ContextNode

class Namespace:
    """Hierarchical namespace with mount points. Resolves paths via longest-prefix match."""

    def __init__(self) -> None:
        self._mounts: dict[str, MountPoint] = {}

    def mount(self, prefix: str, mount_point: MountPoint) -> None:
        # Normalize: ensure prefix starts with / and doesn't end with /
        prefix = "/" + prefix.strip("/")
        self._mounts[prefix] = mount_point

    def unmount(self, prefix: str) -> None:
        prefix = "/" + prefix.strip("/")
        self._mounts.pop(prefix, None)

    def _resolve(self, path: str) -> tuple[MountPoint, str]:
        """Find the mount with the longest matching prefix and return (mount, relative_path)."""
        path = "/" + path.strip("/")
        best_prefix = ""
        best_mount = None
        for prefix, mp in self._mounts.items():
            if path == prefix or path.startswith(prefix + "/"):
                if len(prefix) > len(best_prefix):
                    best_prefix = prefix
                    best_mount = mp
        if best_mount is None:
            raise KeyError(f"No mount found for path: {path}")
        rel_path = path[len(best_prefix):].lstrip("/")
        return best_mount, rel_path

    def read(self, path: str) -> ContextNode | None:
        mount, rel = self._resolve(path)
        return mount.read(rel)

    def write(self, path: str, node: ContextNode) -> None:
        mount, rel = self._resolve(path)
        mount.write(rel, node)

    def list(self, path: str) -> list[str]:
        mount, rel = self._resolve(path)
        return mount.list(rel)

    def delete(self, path: str) -> bool:
        mount, rel = self._resolve(path)
        return mount.delete(rel)

    def search(self, path: str, tags: list[str] | None = None,
               source: str | None = None, since: str | None = None) -> list[ContextNode]:
        mount, rel = self._resolve(path)
        return mount.search(rel, tags=tags, source=source, since=since)

    @property
    def mounts(self) -> dict[str, MountPoint]:
        return dict(self._mounts)
