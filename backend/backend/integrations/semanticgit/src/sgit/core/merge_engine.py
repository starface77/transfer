"""Semantic merge engine: merges two branches using AST-level analysis."""

from __future__ import annotations

from dataclasses import dataclass, field

from sgit.models import FileSnapshot, SemanticNode
from sgit.parsers.ast_parser import flatten_nodes


@dataclass
class MergeResult:
    """Result of a semantic merge operation."""

    file_path: str
    merged_nodes: list[SemanticNode] = field(default_factory=list)
    auto_resolved: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def is_clean(self) -> bool:
        return not self.has_conflicts


def _nodes_overlap(a: SemanticNode, b: SemanticNode) -> bool:
    """Check if two modifications touch the same semantic region."""
    if a.kind != b.kind:
        return False
    return a.body_hash != b.body_hash


def merge_snapshots(
    base: FileSnapshot,
    ours: FileSnapshot,
    theirs: FileSnapshot,
) -> MergeResult:
    """Three-way semantic merge of file snapshots.

    Compares 'ours' and 'theirs' against 'base' to detect changes,
    then attempts to combine them without conflicts.
    """
    result = MergeResult(file_path=ours.path)

    base_nodes = flatten_nodes(base)
    our_nodes = flatten_nodes(ours)
    their_nodes = flatten_nodes(theirs)

    all_names = set(base_nodes) | set(our_nodes) | set(their_nodes)

    for name in sorted(all_names):
        in_base = name in base_nodes
        in_ours = name in our_nodes
        in_theirs = name in their_nodes

        if in_base and in_ours and in_theirs:
            base_hash = base_nodes[name].body_hash
            our_hash = our_nodes[name].body_hash
            their_hash = their_nodes[name].body_hash

            we_changed = our_hash != base_hash
            they_changed = their_hash != base_hash

            if not we_changed and not they_changed:
                result.merged_nodes.append(our_nodes[name])
            elif we_changed and not they_changed:
                result.merged_nodes.append(our_nodes[name])
                result.auto_resolved.append(f"Accepted our change to '{name}'")
            elif not we_changed and they_changed:
                result.merged_nodes.append(their_nodes[name])
                result.auto_resolved.append(f"Accepted their change to '{name}'")
            elif our_hash == their_hash:
                result.merged_nodes.append(our_nodes[name])
                result.auto_resolved.append(f"Both sides made identical change to '{name}'")
            else:
                our_node = our_nodes[name]
                their_node = their_nodes[name]
                if not _nodes_overlap(our_node, their_node):
                    result.merged_nodes.append(our_nodes[name])
                    result.auto_resolved.append(
                        f"Non-overlapping changes to '{name}': "
                        f"merged automatically (different semantic regions)"
                    )
                else:
                    result.merged_nodes.append(our_nodes[name])
                    result.conflicts.append(
                        f"Conflict in '{name}': both sides modified the same "
                        f"{our_node.kind} with incompatible changes"
                    )

        elif in_base and in_ours and not in_theirs:
            our_hash = our_nodes[name].body_hash
            base_hash = base_nodes[name].body_hash
            if our_hash == base_hash:
                result.auto_resolved.append(
                    f"'{name}' removed by theirs (unchanged by us): accepted removal"
                )
            else:
                result.merged_nodes.append(our_nodes[name])
                result.conflicts.append(f"Conflict: we modified '{name}' but they deleted it")

        elif in_base and not in_ours and in_theirs:
            their_hash = their_nodes[name].body_hash
            base_hash = base_nodes[name].body_hash
            if their_hash == base_hash:
                result.auto_resolved.append(
                    f"'{name}' removed by us (unchanged by them): accepted removal"
                )
            else:
                result.merged_nodes.append(their_nodes[name])
                result.conflicts.append(f"Conflict: they modified '{name}' but we deleted it")

        elif in_base and not in_ours and not in_theirs:
            result.auto_resolved.append(f"'{name}' removed by both sides")

        elif not in_base and in_ours and not in_theirs:
            result.merged_nodes.append(our_nodes[name])
            result.auto_resolved.append(f"Added '{name}' from our side")

        elif not in_base and not in_ours and in_theirs:
            result.merged_nodes.append(their_nodes[name])
            result.auto_resolved.append(f"Added '{name}' from their side")

        elif not in_base and in_ours and in_theirs:
            if our_nodes[name].body_hash == their_nodes[name].body_hash:
                result.merged_nodes.append(our_nodes[name])
                result.auto_resolved.append(f"Both sides added identical '{name}'")
            else:
                result.merged_nodes.append(our_nodes[name])
                result.conflicts.append(
                    f"Conflict: both sides added different versions of '{name}'"
                )

    return result


def format_merge_result(result: MergeResult) -> str:
    """Format a MergeResult into a human-readable report."""
    lines: list[str] = [f"Merge result for {result.file_path}:"]

    if result.auto_resolved:
        lines.append("  Auto-resolved:")
        for msg in result.auto_resolved:
            lines.append(f"    {msg}")

    if result.conflicts:
        lines.append("  CONFLICTS:")
        for msg in result.conflicts:
            lines.append(f"    {msg}")
    elif result.auto_resolved:
        lines.append("  Clean merge! All changes resolved automatically.")
    else:
        lines.append("  No changes to merge.")

    return "\n".join(lines)
