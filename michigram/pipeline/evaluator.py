from __future__ import annotations

import re

from michigram.afs.node import ContextNode
from michigram.core.primitives import sha256_short
from michigram.repository.history import HistoryRepository
from michigram.repository.memory import MemoryRepository, MemoryType


class ContextEvaluator:
    def __init__(self, history: HistoryRepository, memory: MemoryRepository) -> None:
        self._history = history
        self._memory = memory

    def evaluate_session(self, project: str, session_id: str) -> dict[str, int]:
        node = self._history.get_session(project, session_id)
        if node is None:
            return {"facts": 0, "patterns": 0, "errors": 0}

        content = node.content or ""
        facts = self._extract_facts(content)
        patterns = self._extract_patterns(content)
        errors = self._extract_errors(content)

        for key, value in facts.items():
            self._memory.store(project, MemoryType.FACT, key, value,
                             source="evaluator", tags=["auto-extracted"])

        for key, value in patterns.items():
            self._memory.store(project, MemoryType.EXPERIENTIAL, key, value,
                             source="evaluator", tags=["pattern"])

        for key, value in errors.items():
            self._memory.store(project, MemoryType.EPISODIC, key, value,
                             source="evaluator", tags=["error"])

        return {
            "facts": len(facts),
            "patterns": len(patterns),
            "errors": len(errors),
        }

    def _extract_facts(self, content: str) -> dict[str, str]:
        facts = {}
        lines = content.split("\n")

        prompts_section = False
        for line in lines:
            stripped = line.strip()
            if stripped == "## Prompts":
                prompts_section = True
                continue
            if stripped.startswith("## ") and prompts_section:
                prompts_section = False
                continue
            if prompts_section and stripped.startswith("- "):
                prompt_text = stripped[2:].strip()
                if prompt_text:
                    key = sha256_short("prompt_" + prompt_text, 8)
                    facts[key] = f"Goal: {prompt_text}"
                continue

            if not stripped or stripped.startswith("#"):
                continue

            tool_patterns = [
                r"uses?\s+(\w[\w\s]*\w)",
                r"running\s+(\w[\w\s]*)",
                r"(?:install|pip install|npm install|yarn add)\s+([\w@/.-]+)",
                r"(?:import|from)\s+([\w.]+)",
                r"(?:require)\s*\(\s*['\"]([^'\"]+)",
                r"(?:docker|git|npm|pip|cargo|brew)\s+\w+",
            ]
            for pattern in tool_patterns:
                m = re.search(pattern, stripped, re.IGNORECASE)
                if m:
                    value = m.group(1).strip() if m.lastindex else m.group(0).strip()
                    key = sha256_short(value, 8)
                    facts[key] = value
                    break

            file_path_match = re.search(r"(?:Read|Write|Edit|Bash|Glob|Grep):\s*(\S+)", stripped)
            if file_path_match:
                path = file_path_match.group(1)
                parts = path.rsplit("/", 1)
                if len(parts) > 1:
                    directory = parts[0]
                    key = sha256_short("dir_" + directory, 8)
                    facts[key] = f"Project dir: {directory}"
                ext_match = re.search(r"\.\w+$", path)
                if ext_match:
                    ext = ext_match.group(0)
                    key = sha256_short("ext_" + ext, 8)
                    facts[key] = f"File type: {ext}"

            error_match = re.search(r"(TypeError|ImportError|ValueError|KeyError|AttributeError|RuntimeError|SyntaxError|NameError|FileNotFoundError|ModuleNotFoundError)", stripped)
            if error_match:
                err_type = error_match.group(1)
                key = sha256_short("errtype_" + err_type, 8)
                facts[key] = f"Error encountered: {err_type}"

        return facts

    def _extract_patterns(self, content: str) -> dict[str, str]:
        patterns = {}
        if "## File Operations" in content:
            section = content.split("## File Operations")[1].split("##")[0]
            file_refs = re.findall(r"(?:Read|Write|Edit|Bash|Glob|Grep):\s*(.+)", section)
            if file_refs:
                unique_files = sorted(set(f.strip() for f in file_refs))
                key = sha256_short("files_" + ",".join(unique_files), 8)
                patterns[key] = "Modified files: " + ", ".join(unique_files)
        return patterns

    def _extract_errors(self, content: str) -> dict[str, str]:
        errors = {}
        if "## Errors" in content:
            section = content.split("## Errors")[1].split("##")[0]
            for line in section.strip().split("\n"):
                line = line.strip().lstrip("- ")
                if line:
                    key = sha256_short(line, 8)
                    errors[key] = line
        return errors

    def detect_drift(self, project: str, recent_count: int = 5) -> list[str]:
        sessions = self._history.list_sessions(project)
        recent = sessions[-recent_count:] if len(sessions) > recent_count else sessions
        drift_signals: list[str] = []

        recent_files: set[str] = set()
        for sid in recent:
            node = self._history.get_session(project, sid)
            if node and node.content:
                files = re.findall(r"(?:Read|Write|Edit|Bash|Glob|Grep):\s*(.+)", node.content)
                recent_files.update(f.strip() for f in files)

        stored_patterns = self._memory.recall_all(project, MemoryType.EXPERIENTIAL)
        for pattern in stored_patterns:
            if pattern.content and "Modified files:" in pattern.content:
                stored_files = set(f.strip() for f in pattern.content.split("Modified files:")[1].split(","))
                overlap = recent_files & stored_files
                if stored_files and not overlap:
                    drift_signals.append(f"Focus shifted away from: {', '.join(sorted(stored_files))}")

        return drift_signals

    def continuous_learn(self, project: str, evaluated_ids: set[str] | None = None) -> dict[str, int]:
        if evaluated_ids is None:
            evaluated_ids = set()

        totals = {"facts": 0, "patterns": 0, "errors": 0}
        sessions = self._history.list_sessions(project)
        for sid in sessions:
            if sid in evaluated_ids:
                continue
            result = self.evaluate_session(project, sid)
            for k in totals:
                totals[k] += result[k]
            evaluated_ids.add(sid)

        return totals
