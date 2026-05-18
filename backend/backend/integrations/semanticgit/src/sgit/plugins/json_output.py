"""JSON structured output for AI agents: compact semantic diffs."""

from __future__ import annotations

import json
from typing import Any

from sgit.models import Commit, SemanticDelta, SemanticNode


def delta_to_dict(delta: SemanticDelta) -> dict[str, Any]:
    """Convert a SemanticDelta to a compact JSON-friendly dict."""
    result: dict[str, Any] = {"file": delta.file_path}

    if delta.added:
        result["added"] = [_node_summary(n) for n in delta.added]

    if delta.removed:
        result["removed"] = [_node_summary(n) for n in delta.removed]

    if delta.modified:
        result["modified"] = [_modification_summary(old, new) for old, new in delta.modified]

    if delta.renamed:
        result["renamed"] = [
            {"old": old_name, "new": new_name, "kind": node.kind}
            for old_name, new_name, node in delta.renamed
        ]

    if delta.moved:
        result["moved"] = [
            {"name": node.name, "from": old_parent, "to": new_parent}
            for node, old_parent, new_parent in delta.moved
        ]

    return result


def _node_summary(node: SemanticNode) -> dict[str, str]:
    d: dict[str, str] = {"kind": node.kind, "name": node.qualified_name}
    if node.signature:
        d["signature"] = node.signature
    return d


def _modification_summary(old: SemanticNode, new: SemanticNode) -> dict[str, Any]:
    d: dict[str, Any] = {"kind": new.kind, "name": new.qualified_name}
    if old.signature != new.signature:
        d["signature_changed"] = True
        d["old_signature"] = old.signature
        d["new_signature"] = new.signature
    else:
        d["signature_changed"] = False
    return d


def deltas_to_json(deltas: list[SemanticDelta], indent: int | None = 2) -> str:
    """Serialize a list of SemanticDeltas to JSON."""
    items = [delta_to_dict(d) for d in deltas if d.has_changes]
    return json.dumps(items, indent=indent, ensure_ascii=False)


def commit_to_dict(commit: Commit) -> dict[str, Any]:
    """Convert a Commit to a JSON-friendly dict."""
    return {
        "id": commit.commit_id,
        "parent": commit.parent_id,
        "branch": commit.branch,
        "timestamp": commit.timestamp,
        "message": commit.message.split("\n")[0],
        "files": sorted(commit.snapshots.keys()),
        "file_count": len(commit.snapshots),
    }


def commits_to_json(commits: list[Commit], indent: int | None = 2) -> str:
    """Serialize a list of Commits to JSON."""
    return json.dumps(
        [commit_to_dict(c) for c in commits],
        indent=indent,
        ensure_ascii=False,
    )


def status_to_json(
    branch: str,
    head: str | None,
    staged: dict[str, str],
    untracked: list[str],
    indent: int | None = 2,
) -> str:
    """Serialize repository status to JSON."""
    return json.dumps(
        {
            "branch": branch,
            "head": head,
            "staged": sorted(staged.keys()),
            "staged_count": len(staged),
            "untracked": untracked,
            "untracked_count": len(untracked),
        },
        indent=indent,
        ensure_ascii=False,
    )
