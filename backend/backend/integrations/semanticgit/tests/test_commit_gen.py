"""Tests for the commit message generator."""

from __future__ import annotations

import unittest

from sgit.core.commit_gen import generate_commit_message
from sgit.core.diff_engine import compute_delta
from sgit.models import FileSnapshot
from sgit.parsers.ast_parser import parse_file


class TestGenerateCommitMessage(unittest.TestCase):
    def test_single_addition(self) -> None:
        old = FileSnapshot(path="app.py")
        new = parse_file("app.py", source="def hello(): pass")
        delta = compute_delta(old, new)
        msg = generate_commit_message([delta])
        self.assertIn("Add", msg)
        self.assertIn("hello", msg)

    def test_single_removal(self) -> None:
        old = parse_file("app.py", source="def hello(): pass")
        new = FileSnapshot(path="app.py")
        delta = compute_delta(old, new)
        msg = generate_commit_message([delta])
        self.assertIn("Remove", msg)

    def test_modification(self) -> None:
        old = parse_file("app.py", source="def hello(): pass")
        new = parse_file("app.py", source="def hello(): return 42")
        delta = compute_delta(old, new)
        msg = generate_commit_message([delta])
        self.assertIn("Update", msg)

    def test_empty_deltas(self) -> None:
        msg = generate_commit_message([])
        self.assertEqual(msg, "Empty commit")

    def test_multiple_changes(self) -> None:
        old = parse_file("app.py", source="def a(): pass")
        new = parse_file("app.py", source="def a(): return 1\ndef b(): pass")
        delta = compute_delta(old, new)
        msg = generate_commit_message([delta])
        self.assertTrue(len(msg) > 0)

    def test_message_includes_file(self) -> None:
        old = FileSnapshot(path="module.py")
        new = parse_file("module.py", source="class Foo: pass")
        delta = compute_delta(old, new)
        msg = generate_commit_message([delta])
        self.assertIn("module.py", msg)


if __name__ == "__main__":
    unittest.main()
