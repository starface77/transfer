"""Structural code search: find code by AST structure patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from sgit.core.node_ops import _count_params
from sgit.models import FileSnapshot, SemanticNode


@dataclass
class SearchPattern:
    """A structural search query."""

    kind: Optional[str] = None
    name: Optional[str] = None
    signature: Optional[str] = None
    is_async: Optional[bool] = None
    min_params: Optional[int] = None
    max_params: Optional[int] = None
    exact_params: Optional[int] = None
    has_decorator: Optional[str] = None
    return_type: Optional[str] = None
    parent: Optional[str] = None
    has_docstring: Optional[bool] = None
    pattern: Optional[str] = None


@dataclass
class SearchResult:
    """A single search match."""

    file_path: str
    node: SemanticNode
    qualified_name: str
    match_score: float = 1.0


@dataclass
class SearchResults:
    """Collection of search results."""

    matches: list[SearchResult] = field(default_factory=list)
    total_files_searched: int = 0
    total_nodes_searched: int = 0

    def to_dict(self) -> dict:
        return {
            "matches": [
                {
                    "file": m.file_path,
                    "kind": m.node.kind,
                    "name": m.qualified_name,
                    "signature": m.node.signature,
                    "line_start": m.node.line_start,
                    "line_end": m.node.line_end,
                    "decorators": m.node.decorators,
                    "docstring": m.node.docstring[:100] if m.node.docstring else "",
                }
                for m in self.matches
            ],
            "total_files_searched": self.total_files_searched,
            "total_nodes_searched": self.total_nodes_searched,
            "total_matches": len(self.matches),
        }


def _node_matches(node: SemanticNode, query: SearchPattern) -> bool:
    """Check if a single node matches the search pattern."""
    # Kind filter
    if query.kind is not None:
        qk = query.kind.lower()
        nk = node.kind.lower()
        if qk == "async":
            if not nk.startswith("async_"):
                return False
        elif qk == "function":
            if nk not in ("function", "async_function"):
                return False
        elif qk == "method":
            if nk not in ("method", "async_method"):
                return False
        elif qk not in nk:
            return False

    # Name pattern (regex)
    if query.name is not None:
        if not re.search(query.name, node.name, re.IGNORECASE):
            return False

    # Signature pattern (regex)
    if query.signature is not None:
        if not re.search(query.signature, node.signature, re.IGNORECASE):
            return False

    # Async filter
    if query.is_async is not None:
        node_is_async = node.kind.startswith("async_")
        if node_is_async != query.is_async:
            return False

    # Parameter count
    if query.exact_params is not None:
        param_count = _count_params(node.signature)
        if param_count != query.exact_params:
            return False

    if query.min_params is not None:
        if _count_params(node.signature) < query.min_params:
            return False

    if query.max_params is not None:
        if _count_params(node.signature) > query.max_params:
            return False

    # Decorator filter
    if query.has_decorator is not None:
        if not any(query.has_decorator in d for d in node.decorators):
            return False

    # Return type filter
    if query.return_type is not None:
        sig = node.signature
        arrow_idx = sig.find("->")
        if arrow_idx < 0:
            return False
        ret_part = sig[arrow_idx + 2 :].strip()
        if query.return_type.lower() not in ret_part.lower():
            return False

    # Parent filter
    if query.parent is not None:
        if not re.search(query.parent, node.parent_name, re.IGNORECASE):
            return False

    # Docstring filter
    if query.has_docstring is not None:
        has_doc = bool(node.docstring and node.docstring.strip())
        if has_doc != query.has_docstring:
            return False

    # General text pattern
    if query.pattern is not None:
        combined = f"{node.kind} {node.name} {node.signature} {node.docstring}"
        if not re.search(query.pattern, combined, re.IGNORECASE):
            return False

    return True


def search_snapshot(
    file_path: str,
    snapshot: FileSnapshot,
    query: SearchPattern,
) -> tuple[list[SearchResult], int]:
    """Search a single file snapshot. Returns (matches, nodes_searched)."""
    results: list[SearchResult] = []
    count = 0

    def _walk(nodes: list[SemanticNode], prefix: str = "") -> None:
        nonlocal count
        for node in nodes:
            count += 1
            qname = f"{prefix}.{node.name}" if prefix else node.name
            if _node_matches(node, query):
                results.append(
                    SearchResult(
                        file_path=file_path,
                        node=node,
                        qualified_name=qname,
                    )
                )
            if node.children:
                _walk(node.children, qname)

    _walk(snapshot.nodes)
    return results, count


def search_snapshots(
    snapshots: dict[str, FileSnapshot],
    query: SearchPattern,
) -> SearchResults:
    """Search across all file snapshots."""
    all_matches: list[SearchResult] = []
    total_nodes = 0

    for file_path, snapshot in sorted(snapshots.items()):
        matches, nodes_count = search_snapshot(file_path, snapshot, query)
        all_matches.extend(matches)
        total_nodes += nodes_count

    return SearchResults(
        matches=all_matches,
        total_files_searched=len(snapshots),
        total_nodes_searched=total_nodes,
    )
