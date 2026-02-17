# michigram

An implementation of the [Agentic File System (AFS)](https://arxiv.org/abs/2512.05470) paper — a context engineering system that gives AI coding agents persistent, structured memory across sessions.

> **"Everything is Context: Agentic File System Abstraction for Context Engineering"**
> Xiwei Xu, Robert Mao, Quan Bai, Xuewu Gu, Yechao Li, Liming Zhu
> [arXiv:2512.05470](https://arxiv.org/abs/2512.05470)

## The Problem

AI coding agents lose context between sessions. Every new conversation starts from zero — the agent forgets what files it modified, what errors it encountered, what the project's tech stack is, and what patterns it learned. As sessions grow long, older context falls out of the window entirely.

This isn't a model problem. It's a **context engineering** problem — how systems capture, structure, and govern external knowledge, memory, tools, and human input to enable trustworthy reasoning.

## What This Project Does

michigram implements the AFS paper's core idea: treat **everything as context** and manage it through a Unix-inspired file system abstraction. Just as Unix treats devices, pipes, and files through a uniform interface, AFS treats prompts, memories, session logs, and tool outputs as nodes in a virtual file system.

The system:

1. **Captures** raw session logs from Claude Code
2. **Evaluates** sessions to extract facts, patterns, and errors
3. **Stores** knowledge across five memory tiers
4. **Constructs** token-budgeted context manifests using scoring strategies
5. **Injects** relevant context back into the agent at session start

## Paper Implementation

The paper defines three pipeline components. Here's how michigram maps to them:

| Paper Concept | Implementation | File |
|--------------|----------------|------|
| **Context Constructor** | Assembles context manifests with recency/relevance scoring, respects token budget | `pipeline/constructor.py` |
| **Context Evaluator** | Extracts facts, patterns, errors from sessions; detects drift | `pipeline/evaluator.py` |
| **Context Loader** | Ingests JSONL sessions, formats output for agent hooks | `adapters/claude_code.py` |
| **AFS Namespace** | Virtual file system with mount points and longest-prefix routing | `afs/namespace.py` |
| **AFS Nodes** | Immutable context units with metadata, tags, TTL, versioning | `afs/node.py` |
| **Mount Points** | Pluggable storage backends behind a uniform interface | `afs/mount.py` |
| **Persistent Memory** | Five-tier memory system (fact, episodic, experiential, procedural, user) | `repository/memory.py` |

### Memory Tiers

The paper advocates for structured memory categories inspired by cognitive psychology:

| Tier | What It Stores | Example |
|------|---------------|---------|
| **Fact** | Stable project knowledge | "Uses PostgreSQL", "Python 3.10" |
| **Episodic** | Specific events and errors | "ImportError: no module named foo" |
| **Experiential** | Learned workflows and patterns | "Modified files: src/auth.py, tests/test_auth.py" |
| **Procedural** | Tool usage and how-to knowledge | "Bash: pytest tests/ -v" |
| **User** | Explicit preferences | "Always use async", "Prefer pytest" |

### AFS Architecture

The paper's key insight is that a file-system abstraction provides uniform mounting, metadata, and access control for heterogeneous context artifacts:

```
┌──────────────────────────────────────────────┐
│              CLI / HTTP Server                │
├──────────────────────────────────────────────┤
│  Constructor  │  Evaluator  │    Updater     │
├──────────────────────────────────────────────┤
│    History    │   Memory    │  Scratchpad    │
├──────────────────────────────────────────────┤
│        AFS (Namespace + Mount Points)        │
├──────────────────────────────────────────────┤
│       Filesystem    │       SQLite           │
└──────────────────────────────────────────────┘
```

All context — sessions, memories, scratchpad notes — lives under a unified namespace (`/context/history/...`, `/context/memory/...`, `/context/scratchpad/...`). Storage backends are swappable without changing application code.

## Installation

```bash
git clone https://github.com/snowan/michigram.git
cd michigram
pip install -e .
```

Requirements: Python >= 3.10, no external dependencies.

## Setup with Claude Code

### 1. Install the SessionStart hook

```bash
./scripts/install.sh
```

This registers a hook in `~/.claude/settings.json` that injects context automatically:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "michigram inject --project $CWD --adapter claude-code"
      }
    ]
  }
}
```

### 2. (Optional) Install the background daemon

```bash
./scripts/install-launchd.sh
```

Creates a macOS LaunchAgent that captures and learns from sessions every 30 minutes.

## Usage

### Capture sessions

```bash
michigram capture --project /path/to/myproject --adapter claude-code
```

### Learn from sessions

```bash
michigram learn --project /path/to/myproject
```

### Inject context

```bash
michigram inject --project /path/to/myproject --strategy recency
```

Strategies: `recency` (most recent first, default), `relevance` (facts > experiential > episodic).

### Manage memory

```bash
# Store
michigram memory store --project /path/to/proj --type facts --key db --value "PostgreSQL 15"

# Recall
michigram memory recall --project /path/to/proj --type facts

# Forget
michigram memory forget --project /path/to/proj --type facts --key db
```

### Run the daemon

```bash
michigram daemon --interval 1800
```

### Explore the AFS

```bash
michigram afs ls /context
michigram afs read /context/history/myproject/abc123
michigram afs search /context/memory --tags infra
```

### Other commands

```bash
michigram prune --project /path/to/proj --max-age-days 30
michigram serve --host 127.0.0.1 --port 8420
michigram export --path /context --output backup.tar.gz
michigram import --bundle backup.tar.gz --target /context
michigram status
```

## Configuration

Config file: `~/.michigram/config.json`

```json
{
  "base_dir": "~/.michigram",
  "default_backend": "filesystem",
  "token_budget": 8000,
  "default_adapter": "claude-code",
  "prune_max_age_days": 30,
  "daemon_interval_seconds": 1800
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `base_dir` | `~/.michigram` | Root directory for all data |
| `default_backend` | `filesystem` | Storage backend (`filesystem` or `sqlite`) |
| `token_budget` | `8000` | Max tokens for context injection |
| `default_adapter` | `claude-code` | Agent adapter |
| `prune_max_age_days` | `30` | Auto-prune age threshold |
| `daemon_interval_seconds` | `1800` | Background learning interval |

## Data Flow

```
Claude Code session
  │
  ▼
~/.claude/projects/{key}/*.jsonl       ← raw JSONL session logs
  │
  ▼  [capture]
/context/history/{project}/{sid}       ← parsed: prompts, file ops, errors
  │
  ▼  [learn]
/context/memory/{project}/{type}/{key} ← extracted: facts, patterns, errors
  │
  ▼  [inject]
ContextManifest → JSON hook output     ← token-budgeted context for the agent
```

## Project Structure

```
michigram/
├── pyproject.toml
├── scripts/
│   ├── install.sh                # Claude Code hook installer
│   └── install-launchd.sh        # macOS daemon installer
├── michigram/
│   ├── cli.py                    # CLI entrypoint (11 subcommands)
│   ├── server.py                 # HTTP API server
│   ├── bundle.py                 # Export/import tar.gz bundles
│   ├── core/
│   │   ├── config.py             # Configuration loading
│   │   ├── state.py              # Session/project state tracking
│   │   └── primitives.py         # Atomic writes, hashing, token estimation
│   ├── adapters/
│   │   ├── base.py               # Abstract adapter interface
│   │   ├── claude_code.py        # Claude Code JSONL adapter
│   │   └── generic.py            # Generic markdown/text adapter
│   ├── pipeline/
│   │   ├── constructor.py        # Context manifest builder (paper: Context Constructor)
│   │   ├── evaluator.py          # Session analysis (paper: Context Evaluator)
│   │   └── updater.py            # Incremental/adaptive context updates
│   ├── repository/
│   │   ├── history.py            # Session log storage
│   │   ├── memory.py             # Five-tier memory system
│   │   └── scratchpad.py         # Temporary notes with TTL + promotion
│   ├── afs/
│   │   ├── node.py               # ContextNode model + metadata
│   │   ├── namespace.py          # Virtual filesystem with mount routing
│   │   └── mount.py              # Mount point abstraction
│   └── storage/
│       ├── base.py               # Storage backend interface
│       ├── filesystem.py         # File-based storage with versioning
│       └── sqlite.py             # SQLite-based storage
└── tests/                        # 119 tests
```

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## References

- Xu, X., Mao, R., Bai, Q., Gu, X., Li, Y., & Zhu, L. (2025). *Everything is Context: Agentic File System Abstraction for Context Engineering*. [arXiv:2512.05470](https://arxiv.org/abs/2512.05470)

## License

MIT
