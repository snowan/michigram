from __future__ import annotations
from abc import ABC, abstractmethod
from michi_context_v2.afs.node import ContextNode

class StorageBackend(ABC):
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
