from __future__ import annotations

from pathlib import Path

from michi_context_v2.adapters.base import AgentAdapter
from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata
from michi_context_v2.core.primitives import now_iso, estimate_tokens, sha256_short
from michi_context_v2.pipeline.constructor import ContextManifest


class GenericAdapter(AgentAdapter):
    def __init__(self, namespace: Namespace, history_prefix: str = "/context/history") -> None:
        self._ns = namespace
        self._history_prefix = history_prefix

    def ingest(self, raw_data: Path, project: str) -> list[str]:
        session_ids = []
        files = []
        if raw_data.is_file():
            files.append(raw_data)
        elif raw_data.is_dir():
            files.extend(sorted(raw_data.glob("*.md")))
            files.extend(sorted(raw_data.glob("*.txt")))

        for f in files:
            content = f.read_text()
            sid = sha256_short(f.name + content, 12)
            ts = now_iso()
            path = f"{self._history_prefix}/{project}/{sid}"
            node = ContextNode(
                path=path,
                node_type=NodeType.FILE,
                metadata=NodeMetadata(
                    created_at=ts,
                    updated_at=ts,
                    source="generic",
                    token_estimate=estimate_tokens(content),
                    tags=["session", "generic"],
                ),
                content=content,
            )
            self._ns.write(path, node)
            session_ids.append(sid)
        return session_ids

    def format_context(self, manifest: ContextManifest) -> str:
        sections = []
        for node in manifest.items:
            header = f"# {node.path.split('/')[-1]}"
            sections.append(f"{header}\n{node.content or ''}")
        return "\n\n---\n\n".join(sections) if sections else ""

    def detect_sessions(self, project_path: str) -> list[Path]:
        p = Path(project_path)
        if not p.exists():
            return []
        results = []
        results.extend(sorted(p.glob("*.md")))
        results.extend(sorted(p.glob("*.txt")))
        return results
