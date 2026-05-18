"""Node-level operations: find, history, and checkout for individual AST nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from sgit.core.storage import Repository
from sgit.models import Commit, FileSnapshot, SemanticNode


@dataclass
class NodeChange:
    """A record of a node changing in a specific commit."""

    commit: Commit
    file_path: str
    node: SemanticNode
    change_type: str  # "created", "modified", "deleted"
    old_node: Optional[SemanticNode] = None


def find_node_in_snapshot(
    snapshot: FileSnapshot,
    node_name: str,
) -> Optional[SemanticNode]:
    """Find a SemanticNode by qualified name within a single FileSnapshot.

    Supports both simple names ("add") and qualified names ("Calculator.solve").
    """

    def _search(nodes: list[SemanticNode], prefix: str = "") -> Optional[SemanticNode]:
        for node in nodes:
            qname = f"{prefix}.{node.name}" if prefix else node.name
            if qname == node_name:
                return node
            if node.children:
                found = _search(node.children, qname)
                if found is not None:
                    return found
        return None

    return _search(snapshot.nodes)


def find_node_across_snapshots(
    snapshots: dict[str, FileSnapshot],
    node_name: str,
) -> Optional[tuple[str, SemanticNode]]:
    """Find a node by qualified name across all file snapshots.

    Returns (file_path, node) or None.
    """
    for file_path, snapshot in snapshots.items():
        node = find_node_in_snapshot(snapshot, node_name)
        if node is not None:
            return (file_path, node)
    return None


def extract_node_text(source: str, node: SemanticNode) -> str:
    """Extract the raw source text for a node using its line range."""
    lines = source.splitlines(keepends=True)
    start = node.line_start - 1  # 0-indexed
    end = node.line_end  # exclusive
    if start < 0 or end > len(lines):
        return ""
    return "".join(lines[start:end])


def replace_node_text(
    source: str,
    old_node: SemanticNode,
    new_text: str,
) -> str:
    """Replace a node's text in the source with new_text."""
    lines = source.splitlines(keepends=True)
    start = old_node.line_start - 1
    end = old_node.line_end

    # Detect indentation of the old node
    if start < len(lines):
        old_first_line = lines[start]
        old_indent = len(old_first_line) - len(old_first_line.lstrip())
    else:
        old_indent = 0

    # Detect indentation of the new text
    new_lines = new_text.splitlines(keepends=True)
    if new_lines:
        new_first_line = new_lines[0]
        new_indent = len(new_first_line) - len(new_first_line.lstrip())
    else:
        new_indent = 0

    # Re-indent new text to match old indentation
    indent_diff = old_indent - new_indent
    if indent_diff != 0:
        adjusted: list[str] = []
        for line in new_lines:
            if line.strip() == "":
                adjusted.append(line)
            elif indent_diff > 0:
                adjusted.append(" " * indent_diff + line)
            else:
                # Remove leading spaces (but don't go negative)
                remove = min(-indent_diff, len(line) - len(line.lstrip()))
                adjusted.append(line[remove:])
        new_lines = adjusted

    # Ensure new text ends with newline
    new_text_final = "".join(new_lines)
    if new_text_final and not new_text_final.endswith("\n"):
        new_text_final += "\n"

    before = "".join(lines[:start])
    after = "".join(lines[end:])
    return before + new_text_final + after


def node_history(
    repo: Repository,
    node_name: str,
    max_count: int = 50,
) -> list[NodeChange]:
    """Walk commit history and return changes affecting a specific node.

    Returns a list of NodeChange records, newest first.
    """
    commits = repo.log(max_count=max_count + 50)  # fetch extra to filter
    changes: list[NodeChange] = []

    prev_node: Optional[SemanticNode] = None
    prev_file: Optional[str] = None

    # Walk from oldest to newest, then reverse
    for commit in reversed(commits):
        snapshots = repo.get_commit_snapshots(commit)
        result = find_node_across_snapshots(snapshots, node_name)

        if result is not None:
            file_path, current_node = result
            if prev_node is None:
                # Node created
                changes.append(
                    NodeChange(
                        commit=commit,
                        file_path=file_path,
                        node=current_node,
                        change_type="created",
                    )
                )
            elif current_node.body_hash != prev_node.body_hash:
                # Node modified (body changed)
                changes.append(
                    NodeChange(
                        commit=commit,
                        file_path=file_path,
                        node=current_node,
                        change_type="modified",
                        old_node=prev_node,
                    )
                )
            elif current_node.signature != prev_node.signature:
                # Signature changed
                changes.append(
                    NodeChange(
                        commit=commit,
                        file_path=file_path,
                        node=current_node,
                        change_type="modified",
                        old_node=prev_node,
                    )
                )
            prev_node = current_node
            prev_file = file_path
        else:
            if prev_node is not None:
                # Node deleted
                changes.append(
                    NodeChange(
                        commit=commit,
                        file_path=prev_file or "",
                        node=prev_node,
                        change_type="deleted",
                        old_node=prev_node,
                    )
                )
                prev_node = None
                prev_file = None

    # Reverse to newest-first
    changes.reverse()

    return changes[:max_count]


def checkout_node(
    repo: Repository,
    node_name: str,
    commit_id: str,
) -> tuple[str, str]:
    """Restore a specific node from a past commit into the current working tree.

    Returns (file_path, message) describing what was done.
    Raises ValueError if node not found.
    """
    # 1. Load target commit and find the node
    target_commit = repo.get_commit(commit_id)
    if target_commit is None:
        raise ValueError(f"Commit {commit_id} not found")

    target_snapshots = repo.get_commit_snapshots(target_commit)
    target_result = find_node_across_snapshots(target_snapshots, node_name)
    if target_result is None:
        raise ValueError(f"Node '{node_name}' not found in commit {commit_id[:8]}")

    target_file, target_node = target_result

    # 2. Get source from target commit
    target_source = repo.load_source(commit_id, target_file)
    if target_source is None:
        raise ValueError(
            f"Source for '{target_file}' not stored in commit {commit_id[:8]}. "
            "Only commits made with s-git Phase 3+ store raw sources."
        )

    old_text = extract_node_text(target_source, target_node)
    if not old_text.strip():
        raise ValueError(
            f"Could not extract source for node '{node_name}' from commit {commit_id[:8]}"
        )

    # 3. Find the node in the current working tree
    current_file_path = repo.root / target_file
    if not current_file_path.exists():
        raise ValueError(f"File '{target_file}' does not exist in working tree")

    current_source = current_file_path.read_text(encoding="utf-8")

    # Parse current file to find the node
    from sgit.parsers.registry import parse_any_file

    current_snapshot = parse_any_file(str(current_file_path))
    current_node = find_node_in_snapshot(current_snapshot, node_name)

    if current_node is None:
        raise ValueError(f"Node '{node_name}' not found in current '{target_file}'")

    # 4. Replace the node text in the current file
    new_source = replace_node_text(current_source, current_node, old_text)

    # 5. Write back
    current_file_path.write_text(new_source, encoding="utf-8")

    return (
        target_file,
        f"Restored '{node_name}' from commit {commit_id[:8]} in {target_file}",
    )


def search_nodes_in_snapshot(
    snapshot: FileSnapshot,
    pattern: Optional[str] = None,
    kind: Optional[str] = None,
    name_pattern: Optional[str] = None,
    is_async: Optional[bool] = None,
    min_params: Optional[int] = None,
    max_params: Optional[int] = None,
    has_decorator: Optional[str] = None,
    return_type: Optional[str] = None,
) -> list[SemanticNode]:
    """Search nodes in a snapshot matching structural criteria."""
    results: list[SemanticNode] = []

    def _match(node: SemanticNode) -> bool:
        # Kind filter
        if kind is not None:
            if kind == "async":
                if not node.kind.startswith("async_"):
                    return False
            elif kind not in node.kind:
                return False

        # Name pattern (regex)
        if name_pattern is not None:
            if not re.search(name_pattern, node.name, re.IGNORECASE):
                return False

        # Async filter
        if is_async is not None:
            node_is_async = node.kind.startswith("async_")
            if node_is_async != is_async:
                return False

        # Parameter count
        if min_params is not None or max_params is not None:
            param_count = _count_params(node.signature)
            if min_params is not None and param_count < min_params:
                return False
            if max_params is not None and param_count > max_params:
                return False

        # Decorator filter
        if has_decorator is not None:
            if not any(has_decorator in d for d in node.decorators):
                return False

        # Return type filter
        if return_type is not None:
            if f"-> {return_type}" not in node.signature and return_type not in node.signature:
                # Check for return type in signature
                sig = node.signature
                arrow_idx = sig.find("->")
                if arrow_idx < 0:
                    return False
                ret_part = sig[arrow_idx + 2 :].strip()
                if return_type.lower() not in ret_part.lower():
                    return False

        # General pattern (matches name, signature, or kind)
        if pattern is not None:
            combined = f"{node.kind} {node.name} {node.signature}"
            if not re.search(pattern, combined, re.IGNORECASE):
                return False

        return True

    def _walk(nodes: list[SemanticNode]) -> None:
        for node in nodes:
            if _match(node):
                results.append(node)
            if node.children:
                _walk(node.children)

    _walk(snapshot.nodes)
    return results


def _count_params(signature: str) -> int:
    """Count parameters in a function signature string like '(self, x, y=...)'."""
    if not signature or signature == "()":
        return 0
    # Remove outer parens
    sig = signature.strip()
    if sig.startswith("("):
        # Find matching closing paren
        depth = 0
        end = -1
        for i, ch in enumerate(sig):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end > 0:
            sig = sig[1:end]
        else:
            sig = sig[1:]
            if sig.endswith(")"):
                sig = sig[:-1]

    if not sig.strip():
        return 0

    # Split by commas, respecting nested brackets
    params: list[str] = []
    depth = 0
    current = ""
    for ch in sig:
        if ch in "([{":
            depth += 1
            current += ch
        elif ch in ")]}":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            params.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        params.append(current.strip())

    # Filter out *, /, and empty entries
    return len([p for p in params if p and p not in ("*", "/")])
