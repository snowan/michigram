from __future__ import annotations

import json
from pathlib import Path

from michigram.adapters.base import AgentAdapter
from michigram.pipeline.constructor import ContextManifest
from michigram.repository.history import HistoryRepository


class ClaudeCodeAdapter(AgentAdapter):
    def __init__(self, history: HistoryRepository) -> None:
        self._history = history

    def ingest(self, raw_data: Path, project: str) -> list[str]:
        session_ids = []
        if raw_data.is_file() and raw_data.suffix == ".jsonl":
            sid = self._history.ingest_session(raw_data, project)
            session_ids.append(sid)
        elif raw_data.is_dir():
            for f in sorted(raw_data.glob("*.jsonl")):
                sid = self._history.ingest_session(f, project)
                session_ids.append(sid)
        return session_ids

    def format_context(self, manifest: ContextManifest) -> str:
        sections = []
        for node in manifest.items:
            sections.append(node.content or "")

        context_text = "\n\n---\n\n".join(sections) if sections else ""

        output = {
            "hookSpecificOutput": {
                "additionalContext": context_text
            }
        }
        return json.dumps(output, indent=2)

    def detect_sessions(self, project_path: str) -> list[Path]:
        claude_dir = Path.home() / ".claude" / "projects"
        if not claude_dir.exists():
            return []

        safe_key = Path(project_path).resolve().as_posix().replace("/", "-").replace(".", "-").lstrip("-")
        project_dir = claude_dir / safe_key

        if not project_dir.exists():
            return []

        return sorted(project_dir.glob("*.jsonl"))
