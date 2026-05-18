"""Tests for the incremental parsing cache."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sgit.models import FileSnapshot, SemanticNode
from sgit.parsers.cache import ParseCache


class TestParseCache(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.cache_dir = Path(self.tmp) / ".sgit" / "cache"
        self.cache = ParseCache(self.cache_dir)

        self.src_dir = Path(self.tmp) / "src"
        self.src_dir.mkdir()
        self.test_file = self.src_dir / "example.py"
        self.test_file.write_text("def hello(): pass\n")

        self.snapshot = FileSnapshot(
            path=str(self.test_file),
            nodes=[
                SemanticNode(
                    kind="function", name="hello", signature="()", line_start=1, line_end=1
                )
            ],
            raw_hash="abc123",
        )

    def test_cache_dir_created(self) -> None:
        self.assertTrue(self.cache_dir.exists())

    def test_miss_on_empty_cache(self) -> None:
        result = self.cache.get(str(self.test_file))
        self.assertIsNone(result)

    def test_put_and_get(self) -> None:
        self.cache.put(str(self.test_file), self.snapshot)
        result = self.cache.get(str(self.test_file))
        self.assertIsNotNone(result)
        self.assertEqual(result.path, self.snapshot.path)
        self.assertEqual(len(result.nodes), 1)
        self.assertEqual(result.nodes[0].name, "hello")

    def test_miss_after_file_change(self) -> None:
        import os
        import time

        self.cache.put(str(self.test_file), self.snapshot)
        # Ensure mtime changes by waiting and touching
        time.sleep(0.05)
        self.test_file.write_text("def goodbye(): pass\n")
        os.utime(str(self.test_file), (time.time() + 1, time.time() + 1))
        result = self.cache.get(str(self.test_file))
        self.assertIsNone(result)

    def test_invalidate(self) -> None:
        self.cache.put(str(self.test_file), self.snapshot)
        self.cache.invalidate(str(self.test_file))
        result = self.cache.get(str(self.test_file))
        self.assertIsNone(result)

    def test_clear(self) -> None:
        self.cache.put(str(self.test_file), self.snapshot)
        self.cache.clear()
        self.assertEqual(self.cache.stats()["cached_files"], 0)

    def test_stats(self) -> None:
        self.cache.get(str(self.test_file))
        self.cache.put(str(self.test_file), self.snapshot)
        self.cache.get(str(self.test_file))
        stats = self.cache.stats()
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["cached_files"], 1)

    def test_flush_persists(self) -> None:
        self.cache.put(str(self.test_file), self.snapshot)
        self.cache.flush()
        cache2 = ParseCache(self.cache_dir)
        result = cache2.get(str(self.test_file))
        self.assertIsNotNone(result)
        self.assertEqual(result.nodes[0].name, "hello")

    def test_miss_on_deleted_file(self) -> None:
        self.cache.put(str(self.test_file), self.snapshot)
        self.test_file.unlink()
        result = self.cache.get(str(self.test_file))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
