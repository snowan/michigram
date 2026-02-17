import json
import threading
from http.client import HTTPConnection

from michigram.core.config import Config
from michigram.server import create_server


def _start_server(tmp_path):
    config = Config(base_dir=tmp_path / ".michigram")
    config.base_dir.mkdir(parents=True)
    server = create_server("127.0.0.1", 0, config)  # port 0 = random available
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def _get(port, path):
    conn = HTTPConnection("127.0.0.1", port)
    conn.request("GET", path)
    resp = conn.getresponse()
    return resp.status, json.loads(resp.read())


def _post(port, path, body):
    conn = HTTPConnection("127.0.0.1", port)
    data = json.dumps(body).encode()
    conn.request("POST", path, body=data, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    return resp.status, json.loads(resp.read())


def _delete(port, path):
    conn = HTTPConnection("127.0.0.1", port)
    conn.request("DELETE", path)
    resp = conn.getresponse()
    return resp.status, json.loads(resp.read())


def test_status(tmp_path):
    server, port = _start_server(tmp_path)
    status, data = _get(port, "/status")
    assert status == 200
    assert data["status"] == "ok"
    server.shutdown()


def test_memory_crud(tmp_path):
    server, port = _start_server(tmp_path)

    status, data = _post(port, "/context/memory/proj/facts/db", {"value": "PostgreSQL", "tags": ["infra"]})
    assert status == 201

    status, data = _get(port, "/context/memory/proj/facts/db")
    assert status == 200
    assert data["value"] == "PostgreSQL"

    status, data = _get(port, "/context/memory/proj/facts")
    assert status == 200
    assert len(data["items"]) == 1

    status, data = _delete(port, "/context/memory/proj/facts/db")
    assert status == 200

    status, data = _get(port, "/context/memory/proj/facts/db")
    assert status == 404

    server.shutdown()


def test_inject(tmp_path):
    server, port = _start_server(tmp_path)
    status, data = _get(port, "/context/inject?project=testproj")
    assert status == 200
    assert "items" in data
    assert "total_tokens" in data
    server.shutdown()


def test_not_found(tmp_path):
    server, port = _start_server(tmp_path)
    status, data = _get(port, "/nonexistent")
    assert status == 404
    server.shutdown()
