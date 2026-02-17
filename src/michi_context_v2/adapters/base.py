from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from michi_context_v2.pipeline.constructor import ContextManifest


class AgentAdapter(ABC):
    @abstractmethod
    def ingest(self, raw_data: Path, project: str) -> list[str]:
        """Ingest raw session data. Returns list of session IDs created."""
        ...

    @abstractmethod
    def format_context(self, manifest: ContextManifest) -> str:
        """Format a ContextManifest into the agent's expected format."""
        ...

    @abstractmethod
    def detect_sessions(self, project_path: str) -> list[Path]:
        """Find unprocessed session files for the given project."""
        ...
