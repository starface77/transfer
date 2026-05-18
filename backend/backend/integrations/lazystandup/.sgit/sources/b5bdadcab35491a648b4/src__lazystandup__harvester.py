"""Harvest AST-level semantic changes from s-git commit history."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sgit.core.diff_engine import compute_delta
from sgit.core.storage import Repository
from sgit.models import FileSnapshot, SemanticDelta


@dataclass
class ASTChange:
    """A single AST-level change extracted from a commit."""

    commit_id: str
    timestamp: str
    message: str
    file_path: str
    change_type: str  # "added", "removed", "modified", "renamed", "moved"
    node_kind: str
    node_name: str
    signature: str = ""
    old_name: str = ""
    details: str = ""

    def describe(self) -> str:
        """Human-readable one-liner for this change."""
        if self.change_type == "added":
            sig = f"{self.signature}" if self.signature else ""
            return f"Added {self.node_kind} `{self.node_name}{sig}` in {self.file_path}"
        elif self.change_type == "removed":
            return f"Removed {self.node_kind} `{self.node_name}` from {self.file_path}"
        elif self.change_type == "modified":
            return f"Modified {self.node_kind} `{self.node_name}` in {self.file_path}"
        elif self.change_type == "renamed":
            return (
                f"Renamed {self.node_kind} `{self.old_name}` -> "
                f"`{self.node_name}` in {self.file_path}"
            )
        elif self.change_type == "moved":
            return f"Moved {self.node_kind} `{self.node_name}` in {self.file_path}"
        return f"{self.change_type}: {self.node_kind} `{self.node_name}` in {self.file_path}"


@dataclass
class HarvestResult:
    """Result of harvesting AST changes from history."""

    changes: list[ASTChange] = field(default_factory=list)
    commits_scanned: int = 0
    time_range_hours: float = 0

    @property
    def descriptions(self) -> list[str]:
        return [ch.describe() for ch in self.changes]


def _delta_to_changes(
    delta: SemanticDelta,
    commit_id: str,
    timestamp: str,
    message: str,
) -> list[ASTChange]:
    """Convert a SemanticDelta into a list of ASTChange records."""
    changes: list[ASTChange] = []

    for node in delta.added:
        changes.append(
            ASTChange(
                commit_id=commit_id,
                timestamp=timestamp,
                message=message,
                file_path=delta.file_path,
                change_type="added",
                node_kind=node.kind,
                node_name=node.qualified_name,
                signature=node.signature,
            )
        )

    for node in delta.removed:
        changes.append(
            ASTChange(
                commit_id=commit_id,
                timestamp=timestamp,
                message=message,
                file_path=delta.file_path,
                change_type="removed",
                node_kind=node.kind,
                node_name=node.qualified_name,
            )
        )

    for old_node, new_node in delta.modified:
        details_parts: list[str] = []
        if old_node.signature != new_node.signature:
            details_parts.append(
                f"signature: {old_node.signature} -> {new_node.signature}"
            )
        if old_node.body_hash != new_node.body_hash:
            details_parts.append("body changed")

        changes.append(
            ASTChange(
                commit_id=commit_id,
                timestamp=timestamp,
                message=message,
                file_path=delta.file_path,
                change_type="modified",
                node_kind=new_node.kind,
                node_name=new_node.qualified_name,
                signature=new_node.signature,
                details="; ".join(details_parts),
            )
        )

    for old_name, new_name, node in delta.renamed:
        changes.append(
            ASTChange(
                commit_id=commit_id,
                timestamp=timestamp,
                message=message,
                file_path=delta.file_path,
                change_type="renamed",
                node_kind=node.kind,
                node_name=new_name,
                old_name=old_name,
            )
        )

    for node, old_parent, new_parent in delta.moved:
        changes.append(
            ASTChange(
                commit_id=commit_id,
                timestamp=timestamp,
                message=message,
                file_path=delta.file_path,
                change_type="moved",
                node_kind=node.kind,
                node_name=node.qualified_name,
                details=f"{old_parent} -> {new_parent}",
            )
        )

    return changes


def harvest_changes(
    repo_path: Optional[str] = None,
    hours: float = 8,
    max_commits: int = 200,
) -> HarvestResult:
    """Scan s-git history and gather all AST changes from the last N hours.

    Args:
        repo_path: Path to s-git repo root (auto-detected if None).
        hours: How many hours of history to scan.
        max_commits: Max commits to look back.

    Returns:
        HarvestResult with all AST changes found.
    """
    try:
        repo = Repository(repo_path)
    except FileNotFoundError:
        return HarvestResult()

    commits = repo.log(max_count=max_commits)
    if not commits:
        return HarvestResult()

    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(hours=hours)

    all_changes: list[ASTChange] = []
    commits_in_range = 0

    for commit in commits:
        try:
            commit_time = datetime.datetime.fromisoformat(
                commit.timestamp.replace("Z", "+00:00")
            )
        except ValueError:
            continue

        if commit_time < cutoff:
            break

        commits_in_range += 1

        # Compute deltas between this commit and its parent
        current_snapshots = repo.get_commit_snapshots(commit)

        if commit.parent_id:
            parent = repo.get_commit(commit.parent_id)
            if parent:
                parent_snapshots = repo.get_commit_snapshots(parent)
            else:
                parent_snapshots = {}
        else:
            parent_snapshots = {}

        all_files = set(current_snapshots) | set(parent_snapshots)
        for fpath in all_files:
            old_snap = parent_snapshots.get(fpath, FileSnapshot(path=fpath))
            new_snap = current_snapshots.get(fpath, FileSnapshot(path=fpath))
            delta = compute_delta(old_snap, new_snap)
            if delta.has_changes:
                changes = _delta_to_changes(
                    delta,
                    commit_id=commit.commit_id,
                    timestamp=commit.timestamp,
                    message=commit.message,
                )
                all_changes.extend(changes)

    return HarvestResult(
        changes=all_changes,
        commits_scanned=commits_in_range,
        time_range_hours=hours,
    )
