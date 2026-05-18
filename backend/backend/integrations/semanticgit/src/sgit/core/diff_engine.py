"""Semantic diff engine: compares two FileSnapshots and produces SemanticDelta."""

from __future__ import annotations

from difflib import SequenceMatcher

from sgit.models import FileSnapshot, SemanticDelta, SemanticNode
from sgit.parsers.ast_parser import flatten_nodes

RENAME_SIMILARITY_THRESHOLD = 0.6


def _body_similarity(a: SemanticNode, b: SemanticNode) -> float:
    """Compute similarity ratio between two nodes' body hashes and structure."""
    if a.body_hash == b.body_hash:
        return 1.0
    sig_sim = SequenceMatcher(None, a.signature, b.signature).ratio()
    kind_match = 1.0 if a.kind == b.kind else 0.0
    children_a = {c.name for c in a.children}
    children_b = {c.name for c in b.children}
    if children_a or children_b:
        child_sim = len(children_a & children_b) / max(len(children_a | children_b), 1)
    else:
        child_sim = 0.5
    return sig_sim * 0.4 + kind_match * 0.3 + child_sim * 0.3


def compute_delta(old: FileSnapshot, new: FileSnapshot) -> SemanticDelta:
    """Compute semantic delta between two file snapshots."""
    delta = SemanticDelta(file_path=new.path)

    old_nodes = flatten_nodes(old)
    new_nodes = flatten_nodes(new)

    old_names = set(old_nodes.keys())
    new_names = set(new_nodes.keys())

    matched = old_names & new_names
    only_old = old_names - new_names
    only_new = new_names - old_names

    for name in matched:
        old_node = old_nodes[name]
        new_node = new_nodes[name]
        if old_node.body_hash != new_node.body_hash or old_node.signature != new_node.signature:
            delta.modified.append((old_node, new_node))

    used_old: set[str] = set()
    used_new: set[str] = set()

    for old_name in only_old:
        old_node = old_nodes[old_name]
        best_score = 0.0
        best_new_name = ""

        for new_name in only_new:
            if new_name in used_new:
                continue
            new_node = new_nodes[new_name]
            if old_node.kind != new_node.kind:
                continue

            sim = _body_similarity(old_node, new_node)
            if sim > best_score:
                best_score = sim
                best_new_name = new_name

        if best_score >= RENAME_SIMILARITY_THRESHOLD and best_new_name:
            new_node = new_nodes[best_new_name]
            old_parent = old_node.parent_name
            new_parent = new_node.parent_name

            if old_node.name != new_node.name:
                delta.renamed.append((old_name, best_new_name, new_node))
            if old_parent != new_parent:
                delta.moved.append((new_node, old_parent or "(module)", new_parent or "(module)"))
            if old_node.body_hash != new_node.body_hash:
                delta.modified.append((old_node, new_node))

            used_old.add(old_name)
            used_new.add(best_new_name)

    for old_name in only_old:
        if old_name not in used_old:
            delta.removed.append(old_nodes[old_name])

    for new_name in only_new:
        if new_name not in used_new:
            delta.added.append(new_nodes[new_name])

    return delta


def format_delta(delta: SemanticDelta) -> str:
    """Format a SemanticDelta into a human-readable string."""
    if not delta.has_changes:
        return f"  {delta.file_path}: no semantic changes"

    lines: list[str] = [f"  {delta.file_path}:"]

    for node in delta.added:
        lines.append(f"    + Added {node.kind} '{node.qualified_name}'")
        if node.signature:
            lines.append(f"      signature: {node.signature}")

    for node in delta.removed:
        lines.append(f"    - Removed {node.kind} '{node.qualified_name}'")

    for old_node, new_node in delta.modified:
        lines.append(f"    ~ Modified {new_node.kind} '{new_node.qualified_name}'")
        if old_node.signature != new_node.signature:
            lines.append(f"      signature changed: {old_node.signature} -> {new_node.signature}")

    for old_name, new_name, node in delta.renamed:
        lines.append(f"    > Renamed '{old_name}' -> '{new_name}'")

    for node, old_parent, new_parent in delta.moved:
        lines.append(f"    >> Moved '{node.name}' from {old_parent} to {new_parent}")

    return "\n".join(lines)


def format_deltas(deltas: list[SemanticDelta]) -> str:
    """Format a list of SemanticDeltas into a human-readable report."""
    if not deltas:
        return "No semantic changes detected."

    parts = ["Semantic diff:"]
    for d in deltas:
        parts.append(format_delta(d))
    return "\n".join(parts)
