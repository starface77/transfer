"""Incremental parsing cache (DSM-style): only re-parse changed files."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

from sgit.models import FileSnapshot


class ParseCache:
    """File-system backed cache mapping (path, content-hash) -> FileSnapshot.

    Uses file modification timestamps for fast staleness checks and falls
    back to content hashing only when the timestamp has changed.
    """

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.cache_dir / "cache_index.json"
        self._index: dict[str, dict] = self._load_index()
        self._hits = 0
        self._misses = 0

    def _load_index(self) -> dict[str, dict]:
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_index(self) -> None:
        self._index_path.write_text(json.dumps(self._index, indent=2) + "\n")

    @staticmethod
    def _content_hash(path: str) -> str:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]

    def get(self, path: str) -> Optional[FileSnapshot]:
        """Return cached FileSnapshot if the file hasn't changed, else None."""
        abs_path = str(Path(path).resolve())
        entry = self._index.get(abs_path)
        if entry is None:
            self._misses += 1
            return None

        try:
            stat = os.stat(abs_path)
        except OSError:
            self._misses += 1
            return None

        mtime = stat.st_mtime
        if mtime == entry.get("mtime"):
            self._hits += 1
            return FileSnapshot.from_dict(entry["snapshot"])

        content_hash = self._content_hash(abs_path)
        if content_hash == entry.get("content_hash"):
            entry["mtime"] = mtime
            self._hits += 1
            return FileSnapshot.from_dict(entry["snapshot"])

        self._misses += 1
        return None

    def put(self, path: str, snapshot: FileSnapshot) -> None:
        """Store a FileSnapshot in the cache."""
        abs_path = str(Path(path).resolve())
        try:
            stat = os.stat(abs_path)
            mtime = stat.st_mtime
        except OSError:
            mtime = time.time()

        self._index[abs_path] = {
            "mtime": mtime,
            "content_hash": self._content_hash(abs_path) if Path(abs_path).exists() else "",
            "snapshot": snapshot.to_dict(),
            "cached_at": time.time(),
        }

    def invalidate(self, path: str) -> None:
        """Remove a path from the cache."""
        abs_path = str(Path(path).resolve())
        self._index.pop(abs_path, None)

    def flush(self) -> None:
        """Write the index to disk."""
        self._save_index()

    def stats(self) -> dict[str, int]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "cached_files": len(self._index),
        }

    def clear(self) -> None:
        """Clear the entire cache."""
        self._index.clear()
        self._save_index()
