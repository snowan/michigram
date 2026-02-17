from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

from michi_context_v2.afs.namespace import Namespace
from michi_context_v2.afs.node import ContextNode, NodeType, NodeMetadata, node_to_dict, node_from_dict
from michi_context_v2.core.primitives import now_iso


def export_bundle(namespace: Namespace, base_path: str, output_path: Path) -> int:
    """Export all nodes under base_path to a tar.gz bundle. Returns count of exported nodes."""
    try:
        items = _collect_all(namespace, base_path)
    except KeyError:
        items = []

    manifest = {
        "version": "1.0",
        "exported_at": now_iso(),
        "base_path": base_path,
        "node_count": len(items),
    }

    with tarfile.open(output_path, "w:gz") as tar:
        manifest_data = json.dumps(manifest, indent=2).encode()
        info = tarfile.TarInfo(name="manifest.json")
        info.size = len(manifest_data)
        tar.addfile(info, io.BytesIO(manifest_data))

        for node in items:
            node_dict = node_to_dict(node)
            node_data = json.dumps(node_dict, indent=2).encode()
            safe_name = node.path.strip("/").replace("/", "__")
            info = tarfile.TarInfo(name=f"nodes/{safe_name}.json")
            info.size = len(node_data)
            tar.addfile(info, io.BytesIO(node_data))

    return len(items)


def import_bundle(namespace: Namespace, bundle_path: Path, target_prefix: str | None = None) -> int:
    """Import nodes from a tar.gz bundle into the namespace. Returns count of imported nodes."""
    imported = 0
    with tarfile.open(bundle_path, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.name.startswith("nodes/") or not member.name.endswith(".json"):
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            node_dict = json.loads(f.read())
            node = node_from_dict(node_dict)

            if target_prefix:
                original_base = node_dict.get("_base_path", "")
                if original_base and node.path.startswith(original_base):
                    rel = node.path[len(original_base):]
                    node = ContextNode(
                        path=target_prefix.rstrip("/") + "/" + rel.lstrip("/"),
                        node_type=node.node_type,
                        metadata=node.metadata,
                        content=node.content,
                    )

            node.metadata.updated_at = now_iso()
            namespace.write(node.path, node)
            imported += 1

    return imported


def _collect_all(namespace: Namespace, base_path: str) -> list[ContextNode]:
    results = []
    try:
        children = namespace.list(base_path)
    except KeyError:
        return results

    for child in children:
        child_path = f"{base_path.rstrip('/')}/{child}"
        node = namespace.read(child_path)
        if node is not None:
            if node.node_type == NodeType.FILE:
                results.append(node)
            else:
                results.extend(_collect_all(namespace, child_path))
        else:
            results.extend(_collect_all(namespace, child_path))

    return results
