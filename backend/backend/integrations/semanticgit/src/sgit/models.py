"""Core data models for s-git semantic version control."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SemanticNode:
    """A single semantic element extracted from code AST."""

    kind: str  # "module", "class", "function", "method", "import", "assignment"
    name: str
    signature: str = ""
    docstring: str = ""
    body_hash: str = ""
    line_start: int = 0
    line_end: int = 0
    decorators: list[str] = field(default_factory=list)
    children: list[SemanticNode] = field(default_factory=list)
    parent_name: str = ""

    def semantic_hash(self) -> str:
        payload = json.dumps(
            {
                "kind": self.kind,
                "name": self.name,
                "signature": self.signature,
                "body_hash": self.body_hash,
                "decorators": self.decorators,
                "children": [c.semantic_hash() for c in self.children],
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "name": self.name,
            "signature": self.signature,
            "docstring": self.docstring,
            "body_hash": self.body_hash,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "decorators": self.decorators,
            "parent_name": self.parent_name,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict) -> SemanticNode:
        children = [cls.from_dict(c) for c in data.get("children", [])]
        return cls(
            kind=data["kind"],
            name=data["name"],
            signature=data.get("signature", ""),
            docstring=data.get("docstring", ""),
            body_hash=data.get("body_hash", ""),
            line_start=data.get("line_start", 0),
            line_end=data.get("line_end", 0),
            decorators=data.get("decorators", []),
            parent_name=data.get("parent_name", ""),
            children=children,
        )

    @property
    def qualified_name(self) -> str:
        if self.parent_name:
            return f"{self.parent_name}.{self.name}"
        return self.name


@dataclass
class FileSnapshot:
    """Semantic snapshot of a single file."""

    path: str
    nodes: list[SemanticNode] = field(default_factory=list)
    raw_hash: str = ""

    def tree_hash(self) -> str:
        payload = json.dumps(
            {"path": self.path, "nodes": [n.semantic_hash() for n in self.nodes]},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "nodes": [n.to_dict() for n in self.nodes],
            "raw_hash": self.raw_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FileSnapshot:
        nodes = [SemanticNode.from_dict(n) for n in data.get("nodes", [])]
        return cls(path=data["path"], nodes=nodes, raw_hash=data.get("raw_hash", ""))


@dataclass
class SemanticDelta:
    """Semantic difference between two snapshots of a file."""

    file_path: str
    added: list[SemanticNode] = field(default_factory=list)
    removed: list[SemanticNode] = field(default_factory=list)
    modified: list[tuple[SemanticNode, SemanticNode]] = field(default_factory=list)
    moved: list[tuple[SemanticNode, str, str]] = field(default_factory=list)
    renamed: list[tuple[str, str, SemanticNode]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified or self.moved or self.renamed)


@dataclass
class Commit:
    """A semantic commit object."""

    commit_id: str
    parent_id: Optional[str]
    timestamp: str
    message: str
    branch: str
    snapshots: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "commit_id": self.commit_id,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp,
            "message": self.message,
            "branch": self.branch,
            "snapshots": self.snapshots,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Commit:
        return cls(
            commit_id=data["commit_id"],
            parent_id=data.get("parent_id"),
            timestamp=data["timestamp"],
            message=data["message"],
            branch=data.get("branch", "main"),
            snapshots=data.get("snapshots", {}),
        )
