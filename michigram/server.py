from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from michigram.afs.mount import FilesystemMount
from michigram.afs.namespace import Namespace
from michigram.core.config import Config, load_config
from michigram.pipeline.constructor import ContextConstructor
from michigram.repository.history import HistoryRepository
from michigram.repository.memory import MemoryRepository, MemoryType
from michigram.storage.filesystem import FilesystemBackend


def _build_stack(config: Config):
    store_root = config.base_dir / "store"
    backend = FilesystemBackend(store_root)
    mount = FilesystemMount(backend)
    ns = Namespace()
    ns.mount("/context", mount)
    history = HistoryRepository(ns)
    memory = MemoryRepository(ns)
    return ns, history, memory


class ContextHandler(BaseHTTPRequestHandler):
    config: Config
    ns: Namespace
    history: HistoryRepository
    memory: MemoryRepository

    def _json_response(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/status":
            self._json_response({"status": "ok", "base_dir": str(self.config.base_dir)})

        elif path == "/context/inject":
            project = params.get("project", ["default"])[0]
            strategy = params.get("strategy", ["recency"])[0]
            budget = int(params.get("budget", [str(self.config.token_budget)])[0])
            constructor = ContextConstructor(self.history, self.memory)
            manifest = constructor.construct(project, budget, strategy)
            items = []
            for node in manifest.items:
                items.append({"path": node.path, "content": node.content or "",
                              "tokens": node.metadata.token_estimate})
            self._json_response({"items": items, "total_tokens": manifest.total_tokens,
                                 "strategy": manifest.strategy, "excluded": manifest.excluded_count})

        elif path.startswith("/context/memory/"):
            rest = path[len("/context/memory/"):]
            parts = rest.split("/", 2)
            if len(parts) >= 2:
                project, mem_type = parts[0], parts[1]
                try:
                    mt = MemoryType(mem_type)
                except ValueError:
                    self._json_response({"error": f"Unknown memory type: {mem_type}"}, 400)
                    return
                if len(parts) == 3:
                    node = self.memory.recall(project, mt, parts[2])
                    if node:
                        self._json_response({"key": parts[2], "value": node.content,
                                             "version": node.metadata.version})
                    else:
                        self._json_response({"error": "Not found"}, 404)
                else:
                    nodes = self.memory.recall_all(project, mt)
                    items = [{"key": n.path.split("/")[-1], "value": n.content or "",
                              "version": n.metadata.version} for n in nodes]
                    self._json_response({"type": mem_type, "items": items})
            else:
                self._json_response({"error": "Invalid path"}, 400)

        elif path.startswith("/context/afs/"):
            afs_path = "/" + path[len("/context/afs/"):].lstrip("/")
            try:
                node = self.ns.read(afs_path)
                if node:
                    self._json_response({"path": node.path, "content": node.content or "",
                                         "type": node.node_type.value,
                                         "tokens": node.metadata.token_estimate,
                                         "tags": node.metadata.tags})
                else:
                    items = self.ns.list(afs_path)
                    self._json_response({"path": afs_path, "children": items})
            except KeyError:
                self._json_response({"error": f"Not found: {afs_path}"}, 404)
        else:
            self._json_response({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}

        if path.startswith("/context/memory/"):
            rest = path[len("/context/memory/"):]
            parts = rest.split("/", 2)
            if len(parts) == 3:
                project, mem_type, key = parts
                try:
                    mt = MemoryType(mem_type)
                except ValueError:
                    self._json_response({"error": f"Unknown memory type: {mem_type}"}, 400)
                    return
                value = body.get("value", "")
                tags = body.get("tags", [])
                self.memory.store(project, mt, key, value, tags=tags)
                self._json_response({"stored": f"{mem_type}/{key}"}, 201)
            else:
                self._json_response({"error": "Invalid path"}, 400)
        else:
            self._json_response({"error": "Not found"}, 404)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/context/memory/"):
            rest = path[len("/context/memory/"):]
            parts = rest.split("/", 2)
            if len(parts) == 3:
                project, mem_type, key = parts
                try:
                    mt = MemoryType(mem_type)
                except ValueError:
                    self._json_response({"error": f"Unknown memory type: {mem_type}"}, 400)
                    return
                if self.memory.forget(project, mt, key):
                    self._json_response({"deleted": f"{mem_type}/{key}"})
                else:
                    self._json_response({"error": "Not found"}, 404)
            else:
                self._json_response({"error": "Invalid path"}, 400)
        else:
            self._json_response({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        pass


def create_server(host: str = "127.0.0.1", port: int = 8420,
                  config: Config | None = None) -> HTTPServer:
    if config is None:
        config = load_config()
    ns, history, memory = _build_stack(config)

    handler = type("Handler", (ContextHandler,), {
        "config": config, "ns": ns, "history": history, "memory": memory,
    })
    return HTTPServer((host, port), handler)


def run_server(host: str = "127.0.0.1", port: int = 8420,
               config: Config | None = None) -> None:
    server = create_server(host, port, config)
    print(f"Serving on {host}:{port}")
    server.serve_forever()
