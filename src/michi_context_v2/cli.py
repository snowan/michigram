from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from michi_context_v2.afs.mount import FilesystemMount
from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.core.config import Config, load_config, get_adapter_class
from michi_context_v2.core.state import get_state, save_state
from michi_context_v2.pipeline.constructor import ContextConstructor
from michi_context_v2.pipeline.evaluator import ContextEvaluator
from michi_context_v2.pipeline.updater import ContextUpdater, UpdateMode
from michi_context_v2.repository.history import HistoryRepository
from michi_context_v2.repository.memory import MemoryRepository, MemoryType
from michi_context_v2.storage.filesystem import FilesystemBackend


def _build_stack(config: Config) -> tuple[Namespace, HistoryRepository, MemoryRepository]:
    store_root = config.base_dir / "store"
    backend = FilesystemBackend(store_root)
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    history = HistoryRepository(ns)
    memory = MemoryRepository(ns)
    return ns, history, memory


def _project_name(project_path: str) -> str:
    return Path(project_path).resolve().name


def cmd_capture(args: argparse.Namespace) -> None:
    config = load_config()
    ns, history, _ = _build_stack(config)
    project = _project_name(args.project)

    adapter_cls = get_adapter_class(args.adapter)
    if args.adapter == "claude-code":
        adapter = adapter_cls(history)
    else:
        adapter = adapter_cls(ns)

    sessions = adapter.detect_sessions(args.project)
    state = get_state(config.base_dir)
    ingested = 0

    for session_path in sessions:
        key = f"{project}:{session_path.name}"
        mtime = session_path.stat().st_mtime
        prev = state.get("captured_sessions", {}).get(key)
        if prev and prev.get("mtime") == mtime:
            continue
        sids = adapter.ingest(session_path, project)
        for sid in sids:
            state.setdefault("captured_sessions", {})[key] = {
                "mtime": mtime,
                "session_id": sid,
            }
            ingested += 1

    save_state(config.base_dir, state)
    print(f"Captured {ingested} new sessions for {project}")


def cmd_inject(args: argparse.Namespace) -> None:
    config = load_config()
    ns, history, memory = _build_stack(config)
    project = _project_name(args.project)

    constructor = ContextConstructor(history, memory)
    manifest = constructor.construct(project, config.token_budget, args.strategy)

    adapter_cls = get_adapter_class(args.adapter)
    if args.adapter == "claude-code":
        adapter = adapter_cls(history)
    else:
        adapter = adapter_cls(ns)

    output = adapter.format_context(manifest)
    print(output)


def cmd_learn(args: argparse.Namespace) -> None:
    config = load_config()
    _, history, memory = _build_stack(config)
    project = _project_name(args.project)

    state = get_state(config.base_dir)
    evaluated = set(state.get("evaluated_sessions", {}).get(project, []))

    evaluator = ContextEvaluator(history, memory)
    result = evaluator.continuous_learn(project, evaluated)

    state.setdefault("evaluated_sessions", {})[project] = list(evaluated)
    save_state(config.base_dir, state)

    print(f"Learned from sessions: {result}")


def cmd_prune(args: argparse.Namespace) -> None:
    config = load_config()
    _, history, _ = _build_stack(config)

    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.max_age)
    cutoff_str = cutoff.isoformat()

    state = get_state(config.base_dir)
    total_pruned = 0

    for key_info in state.get("project_map", {}).values():
        proj_name = key_info.get("name", "")
        if proj_name:
            pruned = history.prune(proj_name, before=cutoff_str)
            total_pruned += pruned

    if args.project:
        project = _project_name(args.project)
        pruned = history.prune(project, before=cutoff_str)
        total_pruned += pruned

    print(f"Pruned {total_pruned} old sessions")


def cmd_daemon(args: argparse.Namespace) -> None:
    print(f"Starting daemon (interval={args.interval}s)")
    while True:
        _daemon_tick()
        time.sleep(args.interval)


def _daemon_tick() -> None:
    config = load_config()
    ns, history, memory = _build_stack(config)
    state = get_state(config.base_dir)

    for key_info in state.get("project_map", {}).values():
        proj_name = key_info.get("name", "")
        proj_path = key_info.get("path", "")
        if not proj_name or not proj_path:
            continue

        adapter_cls = get_adapter_class(config.default_adapter)
        if config.default_adapter == "claude-code":
            adapter = adapter_cls(history)
        else:
            adapter = adapter_cls(ns)

        sessions = adapter.detect_sessions(proj_path)
        for sp in sessions:
            mtime = sp.stat().st_mtime
            if time.time() - mtime < 300:
                continue
            key = f"{proj_name}:{sp.name}"
            prev = state.get("captured_sessions", {}).get(key)
            if prev and prev.get("mtime") == mtime:
                continue
            sids = adapter.ingest(sp, proj_name)
            for sid in sids:
                state.setdefault("captured_sessions", {})[key] = {
                    "mtime": mtime, "session_id": sid,
                }

        evaluated = set(state.get("evaluated_sessions", {}).get(proj_name, []))
        evaluator = ContextEvaluator(history, memory)
        evaluator.continuous_learn(proj_name, evaluated)
        state.setdefault("evaluated_sessions", {})[proj_name] = list(evaluated)

    save_state(config.base_dir, state)


def cmd_status(args: argparse.Namespace) -> None:
    config = load_config()
    state = get_state(config.base_dir)
    sessions = state.get("captured_sessions", {})
    projects = state.get("project_map", {})
    evaluated = state.get("evaluated_sessions", {})

    print(f"Base dir: {config.base_dir}")
    print(f"Backend: {config.default_backend}")
    print(f"Token budget: {config.token_budget}")
    print(f"Projects tracked: {len(projects)}")
    print(f"Sessions captured: {len(sessions)}")
    total_eval = sum(len(v) for v in evaluated.values())
    print(f"Sessions evaluated: {total_eval}")


def cmd_memory(args: argparse.Namespace) -> None:
    config = load_config()
    _, _, memory = _build_stack(config)
    project = _project_name(args.project)

    if args.action == "store":
        mt = MemoryType(args.type)
        memory.store(project, mt, args.key, args.value)
        print(f"Stored {args.type}/{args.key}")

    elif args.action == "recall":
        mt = MemoryType(args.type)
        if args.key:
            node = memory.recall(project, mt, args.key)
            if node:
                print(node.content)
            else:
                print("Not found")
        else:
            nodes = memory.recall_all(project, mt)
            for n in nodes:
                key = n.path.split("/")[-1]
                print(f"  {key}: {(n.content or '')[:80]}")

    elif args.action == "forget":
        mt = MemoryType(args.type)
        if memory.forget(project, mt, args.key):
            print(f"Forgotten {args.type}/{args.key}")
        else:
            print("Not found")


def cmd_serve(args: argparse.Namespace) -> None:
    from michi_context_v2.server import run_server
    config = load_config()
    run_server(host=args.host, port=args.port, config=config)


def cmd_export(args: argparse.Namespace) -> None:
    from michi_context_v2.bundle import export_bundle
    config = load_config()
    ns, _, _ = _build_stack(config)
    output = Path(args.output)
    count = export_bundle(ns, args.path, output)
    print(f"Exported {count} nodes to {output}")


def cmd_import(args: argparse.Namespace) -> None:
    from michi_context_v2.bundle import import_bundle
    config = load_config()
    ns, _, _ = _build_stack(config)
    bundle = Path(args.bundle)
    count = import_bundle(ns, bundle, target_prefix=args.target or None)
    print(f"Imported {count} nodes from {bundle}")


def cmd_afs(args: argparse.Namespace) -> None:
    config = load_config()
    ns, _, _ = _build_stack(config)

    if args.action == "ls":
        try:
            items = ns.list(args.path)
            for item in items:
                print(item)
        except KeyError:
            print(f"Path not found: {args.path}")

    elif args.action == "read":
        try:
            node = ns.read(args.path)
            if node:
                print(node.content or "")
            else:
                print("Not found")
        except KeyError:
            print(f"Path not found: {args.path}")

    elif args.action == "search":
        try:
            tags = args.tags.split(",") if args.tags else None
            nodes = ns.search(args.path, tags=tags, source=args.source, since=args.since)
            for n in nodes:
                print(f"  {n.path} (tokens={n.metadata.token_estimate}, tags={n.metadata.tags})")
        except KeyError:
            print(f"Path not found: {args.path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="michi-context-v2",
                                     description="Context engineering system v2")
    sub = parser.add_subparsers(dest="command")

    p_capture = sub.add_parser("capture")
    p_capture.add_argument("--project", default=".")
    p_capture.add_argument("--adapter", default="claude-code")

    p_inject = sub.add_parser("inject")
    p_inject.add_argument("--project", default=".")
    p_inject.add_argument("--adapter", default="claude-code")
    p_inject.add_argument("--strategy", default="recency")

    p_learn = sub.add_parser("learn")
    p_learn.add_argument("--project", default=".")

    p_prune = sub.add_parser("prune")
    p_prune.add_argument("--max-age", type=int, default=30)
    p_prune.add_argument("--project", default="")

    p_daemon = sub.add_parser("daemon")
    p_daemon.add_argument("--interval", type=int, default=1800)

    p_status = sub.add_parser("status")

    p_memory = sub.add_parser("memory")
    p_memory.add_argument("action", choices=["store", "recall", "forget"])
    p_memory.add_argument("--project", default=".")
    p_memory.add_argument("--type", default="facts")
    p_memory.add_argument("--key", default="")
    p_memory.add_argument("--value", default="")

    p_afs = sub.add_parser("afs")
    p_afs.add_argument("action", choices=["ls", "read", "search"])
    p_afs.add_argument("path", nargs="?", default="/context")
    p_afs.add_argument("--tags", default="")
    p_afs.add_argument("--source", default="")
    p_afs.add_argument("--since", default="")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8420)

    p_export = sub.add_parser("export")
    p_export.add_argument("--path", default="/context")
    p_export.add_argument("--output", required=True)

    p_import = sub.add_parser("import")
    p_import.add_argument("--bundle", required=True)
    p_import.add_argument("--target", default="")

    args = parser.parse_args()

    commands = {
        "capture": cmd_capture,
        "inject": cmd_inject,
        "learn": cmd_learn,
        "prune": cmd_prune,
        "daemon": cmd_daemon,
        "status": cmd_status,
        "memory": cmd_memory,
        "afs": cmd_afs,
        "serve": cmd_serve,
        "export": cmd_export,
        "import": cmd_import,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
