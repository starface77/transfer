"""Storage layer: manages .sgit directory, objects, commits, and refs."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

from sgit.models import Commit, FileSnapshot

SGIT_DIR = ".sgit"


def find_root(start: str = ".") -> Optional[Path]:
    """Find the nearest parent directory containing .sgit."""
    current = Path(start).resolve()
    while True:
        if (current / SGIT_DIR).is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def init_repo(path: str = ".") -> Path:
    """Initialize a new .sgit repository."""
    root = Path(path).resolve()
    sgit = root / SGIT_DIR

    if sgit.exists():
        raise FileExistsError(f"Repository already initialized at {root}")

    sgit.mkdir(parents=True)
    (sgit / "objects").mkdir()
    (sgit / "commits").mkdir()
    (sgit / "refs").mkdir()
    (sgit / "refs" / "heads").mkdir()
    (sgit / "sources").mkdir()

    (sgit / "HEAD").write_text("ref: refs/heads/main\n")
    (sgit / "index.json").write_text("{}\n")
    (sgit / "config.json").write_text(json.dumps({"version": 1}, indent=2) + "\n")

    return root


class Repository:
    """Interface to a .sgit repository."""

    def __init__(self, root: Optional[str] = None) -> None:
        if root is not None:
            self.root = Path(root).resolve()
        else:
            found = find_root()
            if found is None:
                raise FileNotFoundError("Not inside an s-git repository (no .sgit found)")
            self.root = found
        self.sgit = self.root / SGIT_DIR

    @property
    def head_ref(self) -> str:
        text = (self.sgit / "HEAD").read_text().strip()
        if text.startswith("ref: "):
            return text[5:]
        return text

    @property
    def current_branch(self) -> str:
        ref = self.head_ref
        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/") :]
        return ref

    def head_commit_id(self) -> Optional[str]:
        ref = self.head_ref
        ref_path = self.sgit / ref
        if ref_path.exists():
            return ref_path.read_text().strip() or None
        return None

    def get_commit(self, commit_id: str) -> Optional[Commit]:
        path = self.sgit / "commits" / f"{commit_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return Commit.from_dict(data)

    def read_index(self) -> dict[str, str]:
        """Read the staging index: {relative_path: raw_hash}."""
        idx_path = self.sgit / "index.json"
        if idx_path.exists():
            return json.loads(idx_path.read_text())
        return {}

    def write_index(self, index: dict[str, str]) -> None:
        (self.sgit / "index.json").write_text(json.dumps(index, indent=2) + "\n")

    def add_file(self, rel_path: str) -> None:
        """Stage a file by adding it to the index."""
        full_path = self.root / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {rel_path}")

        content = full_path.read_text(encoding="utf-8")
        raw_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        index = self.read_index()
        index[rel_path] = raw_hash
        self.write_index(index)

    def store_snapshot(self, snapshot: FileSnapshot) -> str:
        """Store a file snapshot as a JSON object. Returns the tree hash."""
        tree_hash = snapshot.tree_hash()
        obj_path = self.sgit / "objects" / f"{tree_hash}.json"
        obj_path.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n")
        return tree_hash

    def load_snapshot(self, tree_hash: str) -> Optional[FileSnapshot]:
        obj_path = self.sgit / "objects" / f"{tree_hash}.json"
        if not obj_path.exists():
            return None
        data = json.loads(obj_path.read_text())
        return FileSnapshot.from_dict(data)

    def store_source(self, rel_path: str, source: str, commit_id: str) -> None:
        """Store raw file source for a commit."""
        src_dir = self.sgit / "sources" / commit_id
        src_dir.mkdir(parents=True, exist_ok=True)
        dest = src_dir / rel_path.replace("/", "__").replace("\\", "__")
        dest.write_text(source, encoding="utf-8")

    def load_source(self, commit_id: str, rel_path: str) -> Optional[str]:
        """Load raw source for a file in a specific commit."""
        dest = self.sgit / "sources" / commit_id / rel_path.replace("/", "__").replace("\\", "__")
        if dest.exists():
            return dest.read_text(encoding="utf-8")
        return None

    def create_commit(
        self,
        message: str,
        snapshots: dict[str, FileSnapshot],
        sources: Optional[dict[str, str]] = None,
    ) -> Commit:
        """Create a new commit with the given snapshots."""
        parent_id = self.head_commit_id()

        stored: dict[str, dict] = {}
        for rel_path, snap in snapshots.items():
            tree_hash = self.store_snapshot(snap)
            stored[rel_path] = {"tree_hash": tree_hash, "raw_hash": snap.raw_hash}

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        commit_payload = json.dumps(
            {
                "parent": parent_id,
                "timestamp": timestamp,
                "message": message,
                "files": sorted(stored.keys()),
            },
            sort_keys=True,
        )
        commit_id = hashlib.sha256(commit_payload.encode()).hexdigest()[:20]

        commit = Commit(
            commit_id=commit_id,
            parent_id=parent_id,
            timestamp=timestamp,
            message=message,
            branch=self.current_branch,
            snapshots=stored,
        )

        commit_path = self.sgit / "commits" / f"{commit_id}.json"
        commit_path.write_text(json.dumps(commit.to_dict(), indent=2) + "\n")

        if sources:
            for rel_path, src in sources.items():
                self.store_source(rel_path, src, commit_id)

        ref_path = self.sgit / self.head_ref
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(commit_id + "\n")

        self.write_index({})

        return commit

    def get_commit_snapshots(self, commit: Commit) -> dict[str, FileSnapshot]:
        """Load all FileSnapshots for a given commit."""
        result: dict[str, FileSnapshot] = {}
        for rel_path, info in commit.snapshots.items():
            snap = self.load_snapshot(info["tree_hash"])
            if snap is not None:
                result[rel_path] = snap
        return result

    def log(self, max_count: int = 50) -> list[Commit]:
        """Return commit history starting from HEAD."""
        commits: list[Commit] = []
        current_id = self.head_commit_id()

        while current_id and len(commits) < max_count:
            commit = self.get_commit(current_id)
            if commit is None:
                break
            commits.append(commit)
            current_id = commit.parent_id

        return commits

    def list_tracked_files(self) -> list[str]:
        """List all supported source files in the repo (excluding .sgit)."""
        from sgit.parsers.registry import is_supported

        result: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [
                d
                for d in dirnames
                if d != SGIT_DIR
                and not d.startswith(".")
                and d != "node_modules"
                and d != "__pycache__"
                and d != "target"
                and d != "vendor"
            ]
            for fname in filenames:
                if is_supported(fname):
                    full = Path(dirpath) / fname
                    rel = str(full.relative_to(self.root))
                    result.append(rel)
        return sorted(result)

    def create_branch(self, name: str) -> None:
        """Create a new branch pointing to current HEAD commit."""
        commit_id = self.head_commit_id()
        ref_path = self.sgit / "refs" / "heads" / name
        if ref_path.exists():
            raise FileExistsError(f"Branch '{name}' already exists")
        ref_path.write_text((commit_id or "") + "\n")

    def switch_branch(self, name: str) -> None:
        """Switch HEAD to point to the given branch."""
        ref_path = self.sgit / "refs" / "heads" / name
        if not ref_path.exists():
            raise FileNotFoundError(f"Branch '{name}' does not exist")
        (self.sgit / "HEAD").write_text(f"ref: refs/heads/{name}\n")

    def list_branches(self) -> list[str]:
        heads = self.sgit / "refs" / "heads"
        if not heads.exists():
            return []
        return sorted(p.name for p in heads.iterdir() if p.is_file())
