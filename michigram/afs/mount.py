from __future__ import annotations
from abc import ABC, abstractmethod
from michigram.afs.node import ContextNode
from michigram.storage.base import StorageBackend

class MountPoint(ABC):
    @abstractmethod
    def read(self, rel_path: str) -> ContextNode | None: ...

    @abstractmethod
    def write(self, rel_path: str, node: ContextNode) -> None: ...

    @abstractmethod
    def list(self, rel_path: str) -> list[str]: ...

    @abstractmethod
    def delete(self, rel_path: str) -> bool: ...

    @abstractmethod
    def search(self, rel_path: str, tags: list[str] | None = None,
               source: str | None = None, since: str | None = None) -> list[ContextNode]: ...

class FilesystemMount(MountPoint):
    def __init__(self, backend: StorageBackend) -> None:
        self._backend = backend

    def read(self, rel_path: str) -> ContextNode | None:
        return self._backend.read(rel_path)

    def write(self, rel_path: str, node: ContextNode) -> None:
        self._backend.write(rel_path, node)

    def list(self, rel_path: str) -> list[str]:
        return self._backend.list(rel_path)

    def delete(self, rel_path: str) -> bool:
        return self._backend.delete(rel_path)

    def search(self, rel_path: str, tags: list[str] | None = None,
               source: str | None = None, since: str | None = None) -> list[ContextNode]:
        return self._backend.search(rel_path, tags=tags, source=source, since=since)
