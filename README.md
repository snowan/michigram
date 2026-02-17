# michi-context-v2

A context engineering system for AI coding agents. It captures session history, extracts knowledge across memory tiers, and injects relevant context back into the agent — all within token budget constraints.

Built for [Claude Code](https://docs.anthropic.com/en/docs/claude-code), with a pluggable adapter layer for other agents.

## The Problem

AI coding agents lose context between sessions. Each new conversation starts from zero — the agent forgets what files it worked on, what errors it hit, what the project's tech stack is, and what patterns it learned. As sessions grow long, older context falls out of the window entirely.

**michi-context-v2** solves this by implementing a persistent, multi-tiered memory system that:

- **Captures** raw session logs automatically
- **Evaluates** sessions to extract facts, patterns, and errors
- **Stores** knowledge in appropriate memory tiers (facts, episodic, experiential, procedural, user preferences)
- **Injects** the most relevant context at session start, within token budget

The result: agents that remember across sessions and get smarter over time.

## Conceptual Foundation

The memory architecture draws from cognitive psychology's multi-store model, adapted for AI agent workflows:

| Memory Tier | Analogy | What It Stores | Example |
|-------------|---------|---------------|---------|
| **Fact** | Semantic memory | Stable project knowledge | "Uses PostgreSQL", "Python 3.10" |
| **Episodic** | Episodic memory | Specific events and errors | "ImportError: no module named foo" |
| **Experiential** | Procedural memory | Learned workflows | "Modified files: src/auth.py, tests/test_auth.py" |
| **Procedural** | Skill memory | Tool usage patterns | "Bash: pytest tests/ -v" |
| **User** | Preferences | User-set configuration | "Always use async", "Prefer pytest over unittest" |

Context selection uses **scoring strategies** (recency, relevance) and respects a configurable **token budget** to fit within the agent's context window.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  CLI / HTTP Server                │
├──────────────────────────────────────────────────┤
│              Pipeline Layer                       │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐    │
│  │Constructor│  │ Evaluator │  │  Updater   │    │
│  │(build ctx)│  │(learn)    │  │(refresh)   │    │
│  └──────────┘  └───────────┘  └────────────┘    │
├──────────────────────────────────────────────────┤
│              Repository Layer                     │
│  ┌────────┐  ┌────────┐  ┌────────────┐         │
│  │History │  │Memory  │  │Scratchpad  │         │
│  └────────┘  └────────┘  └────────────┘         │
├──────────────────────────────────────────────────┤
│        Abstract File System (AFS)                 │
│  ┌───────────┐  ┌──────────────┐                 │
│  │ Namespace  │  │ Mount Points │                 │
│  └───────────┘  └──────────────┘                 │
├──────────────────────────────────────────────────┤
│              Storage Backends                     │
│  ┌────────────┐  ┌────────┐                      │
│  │ Filesystem │  │ SQLite │                      │
│  └────────────┘  └────────┘                      │
└──────────────────────────────────────────────────┘
```

All context is stored in a unified **Abstract File System (AFS)** — a virtual namespace with pluggable backends. This means you can switch between filesystem and SQLite storage without changing any application code.

## Installation

```bash
# Clone and install
git clone https://github.com/snowan/michigram.git
cd michigram
pip install -e .

# Verify
michi-context-v2 --help
```

**Requirements:** Python >= 3.10, no external dependencies.

## Setup with Claude Code

### 1. Install the SessionStart hook

```bash
./scripts/install.sh
```

This adds a hook to `~/.claude/settings.json` that automatically injects context when a Claude Code session starts:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "michi-context-v2 inject --project $CWD --adapter claude-code"
      }
    ]
  }
}
```

### 2. (Optional) Install the background daemon

```bash
./scripts/install-launchd.sh
```

This creates a macOS LaunchAgent that runs every 30 minutes to capture new sessions and learn from them automatically. Logs go to `~/.michi-context-v2/logs/daemon.log`.

## Usage

### Capture sessions

```bash
# Auto-detect Claude Code sessions for a project
michi-context-v2 capture --project /path/to/myproject --adapter claude-code

# Ingest a specific JSONL file
michi-context-v2 capture --project /path/to/myproject --adapter claude-code \
  --input ~/.claude/projects/Users-me-code-myproject/session.jsonl
```

### Learn from sessions

```bash
# Extract facts, patterns, and errors from captured sessions
michi-context-v2 learn --project /path/to/myproject
```

### Inject context

```bash
# Build and output context (used by the hook automatically)
michi-context-v2 inject --project /path/to/myproject --strategy recency
```

Strategies:
- `recency` — most recent items first (default)
- `relevance` — prioritize facts > experiential > episodic

### Manage memory

```bash
# Store a fact
michi-context-v2 memory store --project /path/to/proj \
  --type facts --key db --value "PostgreSQL 15"

# Recall all facts
michi-context-v2 memory recall --project /path/to/proj --type facts

# Forget a memory
michi-context-v2 memory forget --project /path/to/proj --type facts --key db
```

### Run the daemon

```bash
# Continuous capture + learn loop (every 30 minutes by default)
michi-context-v2 daemon --interval 1800
```

### Explore the AFS

```bash
# List the context tree
michi-context-v2 afs ls /context

# Read a specific session
michi-context-v2 afs read /context/history/myproject/abc123

# Search by tags
michi-context-v2 afs search /context/memory --tags infra
```

### Prune old sessions

```bash
# Remove sessions older than 30 days
michi-context-v2 prune --project /path/to/proj --max-age-days 30
```

### Export / Import

```bash
# Backup
michi-context-v2 export --path /context --output context-backup.tar.gz

# Restore
michi-context-v2 import --bundle context-backup.tar.gz --target /context
```

### HTTP server

```bash
michi-context-v2 serve --host 127.0.0.1 --port 8420
```

Endpoints:
- `GET /status` — health check
- `GET /context/inject?project=X&strategy=recency` — context injection
- `GET/POST/DELETE /context/memory/{project}/{type}/{key}` — memory CRUD
- `GET /context/afs/{path}` — AFS navigation

## Configuration

Config lives at `~/.michi-context-v2/config.json`:

```json
{
  "base_dir": "~/.michi-context-v2",
  "default_backend": "filesystem",
  "token_budget": 8000,
  "default_adapter": "claude-code",
  "prune_max_age_days": 30,
  "daemon_interval_seconds": 1800
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `base_dir` | `~/.michi-context-v2` | Root directory for all data |
| `default_backend` | `filesystem` | Storage backend (`filesystem` or `sqlite`) |
| `token_budget` | `8000` | Max tokens for context injection |
| `default_adapter` | `claude-code` | Agent adapter to use |
| `prune_max_age_days` | `30` | Auto-prune sessions older than this |
| `daemon_interval_seconds` | `1800` | Daemon loop interval |

State is tracked separately in `~/.michi-context-v2/.state.json` (managed automatically).

## Data Flow

```
Claude Code session
  │
  ▼
~/.claude/projects/{key}/*.jsonl     ← raw session logs
  │
  ▼  [capture]
/context/history/{project}/{sid}     ← parsed sessions (prompts, file ops, errors)
  │
  ▼  [learn]
/context/memory/{project}/{type}/{key}  ← extracted knowledge
  │
  ▼  [inject]
ContextManifest → JSON output       ← token-budgeted context for the agent
```

## Project Structure

```
michigram/
├── pyproject.toml
├── scripts/
│   ├── install.sh              # Claude Code hook installer
│   └── install-launchd.sh      # macOS daemon installer
├── src/michi_context_v2/
│   ├── cli.py                  # CLI entrypoint (11 subcommands)
│   ├── server.py               # HTTP API server
│   ├── bundle.py               # Export/import tar.gz bundles
│   ├── core/
│   │   ├── config.py           # Configuration loading
│   │   ├── state.py            # Session/project state tracking
│   │   └── primitives.py       # Atomic writes, hashing, token estimation
│   ├── adapters/
│   │   ├── base.py             # Abstract adapter interface
│   │   ├── claude_code.py      # Claude Code JSONL adapter
│   │   └── generic.py          # Generic markdown/text adapter
│   ├── pipeline/
│   │   ├── constructor.py      # Context manifest builder
│   │   ├── evaluator.py        # Session → knowledge extraction
│   │   └── updater.py          # Incremental/adaptive context updates
│   ├── repository/
│   │   ├── history.py          # Session log storage
│   │   ├── memory.py           # Multi-tier memory (5 types)
│   │   └── scratchpad.py       # Temporary notes with TTL
│   ├── afs/
│   │   ├── node.py             # ContextNode model + metadata
│   │   ├── namespace.py        # Virtual filesystem with mount routing
│   │   └── mount.py            # Mount point abstraction
│   └── storage/
│       ├── base.py             # Storage backend interface
│       ├── filesystem.py       # File-based storage with versioning
│       └── sqlite.py           # SQLite-based storage
└── tests/                      # 119 tests covering all modules
```

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/ -v
```

## License

MIT
