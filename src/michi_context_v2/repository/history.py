from __future__ import annotations

import json
from pathlib import Path

from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata
from michi_context_v2.core.primitives import now_iso, estimate_tokens, sha256_short


class HistoryRepository:
    def __init__(self, namespace: Namespace, prefix: str = "/context/history") -> None:
        self._ns = namespace
        self._prefix = prefix

    def _session_path(self, project: str, session_id: str) -> str:
        return f"{self._prefix}/{project}/{session_id}"

    def ingest_session(self, jsonl_path: Path, project: str, session_id: str | None = None) -> str:
        text = jsonl_path.read_text()
        lines = [line for line in text.strip().split("\n") if line.strip()]

        prompts: list[str] = []
        file_ops: list[str] = []
        errors: list[str] = []
        summary = ""

        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") == "summary":
                summary = entry.get("summary", "")
                if session_id is None:
                    session_id = entry.get("session_id", "")

            if entry.get("type") in ("human", "user"):
                msg = entry.get("message", {})
                content = msg.get("content", [])
                if isinstance(content, str):
                    prompts.append(content)
                else:
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            prompts.append(block["text"])

            if entry.get("type") == "assistant":
                msg = entry.get("message", {})
                for block in msg.get("content", []):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        if name in ("Read", "Write", "Edit"):
                            fp = inp.get("file_path", "")
                            file_ops.append(f"{name}: {fp}")
                        elif name in ("Bash", "Glob", "Grep"):
                            detail = inp.get("command", "") or inp.get("pattern", "")
                            file_ops.append(f"{name}: {detail}")
                    elif block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:
                            summary_lines = text[:300]
                            if not summary:
                                summary = summary_lines

            if entry.get("type") == "result" and entry.get("is_error"):
                errors.append(entry.get("content", "")[:200])

        if session_id is None:
            session_id = sha256_short(text)

        content_parts = []
        if summary:
            content_parts.append(f"## Summary\n{summary}")
        if prompts:
            content_parts.append("## Prompts\n" + "\n".join(f"- {p[:200]}" for p in prompts))
        if file_ops:
            content_parts.append("## File Operations\n" + "\n".join(f"- {op}" for op in file_ops))
        if errors:
            content_parts.append("## Errors\n" + "\n".join(f"- {e}" for e in errors))

        content = "\n\n".join(content_parts) if content_parts else text[:2000]

        ts = now_iso()
        node = ContextNode(
            path=self._session_path(project, session_id),
            node_type=NodeType.FILE,
            metadata=NodeMetadata(
                created_at=ts,
                updated_at=ts,
                source="capture",
                token_estimate=estimate_tokens(content),
                tags=["session", "history"],
            ),
            content=content,
        )
        self._ns.write(node.path, node)
        return session_id

    def get_session(self, project: str, session_id: str) -> ContextNode | None:
        return self._ns.read(self._session_path(project, session_id))

    def list_sessions(self, project: str) -> list[str]:
        try:
            return self._ns.list(f"{self._prefix}/{project}")
        except KeyError:
            return []

    def prune(self, project: str, before: str) -> int:
        sessions = self.list_sessions(project)
        pruned = 0
        for sid in sessions:
            node = self.get_session(project, sid)
            if node and node.metadata.created_at < before:
                self._ns.delete(self._session_path(project, sid))
                pruned += 1
        return pruned
