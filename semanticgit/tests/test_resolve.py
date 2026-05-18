"""Tests for AI-powered conflict resolution."""

from __future__ import annotations

import unittest

from sgit.core.merge_engine import MergeResult
from sgit.plugins.resolve import (
    ResolveResult,
    _heuristic_resolve,
    format_resolve_result,
    resolve_merge_conflicts,
)


class TestHeuristicResolve(unittest.TestCase):
    def test_appends_new_lines_from_theirs(self) -> None:
        base = "def hello(): pass\n"
        ours = "def hello(): pass\n"
        theirs = "def hello(): pass\ndef goodbye(): pass\n"
        result = _heuristic_resolve("test.py", base, ours, theirs, ["conflict1"])
        self.assertTrue(result.success)
        self.assertIn("goodbye", result.resolved_code)
        self.assertEqual(result.conflicts_resolved, 1)

    def test_keeps_ours_when_no_new_lines(self) -> None:
        base = "def hello(): pass\ndef goodbye(): pass\n"
        ours = "def hello(): pass\ndef goodbye(): pass\n"
        theirs = "def hello(): pass\n"
        result = _heuristic_resolve("test.py", base, ours, theirs, ["conflict1"])
        self.assertFalse(result.success)
        self.assertEqual(result.resolved_code, ours)

    def test_explanation_mentions_sgit_llm(self) -> None:
        result = _heuristic_resolve("test.py", "a", "a", "a", ["c"])
        self.assertIn("sgit-llm", result.explanation)


class TestResolveMergeConflicts(unittest.TestCase):
    def test_no_conflicts_returns_success(self) -> None:
        merge_result = MergeResult(
            file_path="test.py",
            merged_nodes=[],
            conflicts=[],
        )
        result = resolve_merge_conflicts(merge_result, "base", "ours", "theirs")
        self.assertTrue(result.success)
        self.assertIn("No conflicts", result.explanation)

    def test_with_conflicts_uses_heuristic(self) -> None:
        merge_result = MergeResult(
            file_path="test.py",
            merged_nodes=[],
            conflicts=["conflict in function foo"],
        )
        base = "def foo(): return 1\n"
        ours = "def foo(): return 2\n"
        theirs = "def foo(): return 3\ndef bar(): pass\n"
        result = resolve_merge_conflicts(merge_result, base, ours, theirs)
        self.assertIsInstance(result, ResolveResult)
        self.assertEqual(result.file_path, "test.py")


class TestFormatResolveResult(unittest.TestCase):
    def test_format_success(self) -> None:
        result = ResolveResult(
            file_path="test.py",
            resolved_code="merged",
            explanation="Resolved by AI",
            success=True,
            conflicts_resolved=2,
        )
        out = format_resolve_result(result)
        self.assertIn("test.py", out)
        self.assertIn("2 conflict(s)", out)

    def test_format_failure(self) -> None:
        result = ResolveResult(
            file_path="test.py",
            resolved_code="ours",
            explanation="Could not resolve",
            success=False,
        )
        out = format_resolve_result(result)
        self.assertIn("Failed", out)


if __name__ == "__main__":
    unittest.main()
