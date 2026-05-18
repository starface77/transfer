"""Tests for JSON structured output."""

from __future__ import annotations

import json
import unittest

from sgit.models import Commit, SemanticDelta, SemanticNode
from sgit.plugins.json_output import (
    commit_to_dict,
    commits_to_json,
    delta_to_dict,
    deltas_to_json,
    status_to_json,
)


def _node(
    kind: str = "function",
    name: str = "foo",
    signature: str = "()",
    parent_name: str = "",
) -> SemanticNode:
    return SemanticNode(kind=kind, name=name, signature=signature, parent_name=parent_name)


class TestDeltaToDict(unittest.TestCase):
    def test_added(self) -> None:
        delta = SemanticDelta(file_path="test.py", added=[_node(name="greet")])
        d = delta_to_dict(delta)
        self.assertEqual(d["file"], "test.py")
        self.assertEqual(len(d["added"]), 1)
        self.assertEqual(d["added"][0]["name"], "greet")

    def test_removed(self) -> None:
        delta = SemanticDelta(file_path="test.py", removed=[_node(name="old_fn")])
        d = delta_to_dict(delta)
        self.assertEqual(len(d["removed"]), 1)

    def test_modified(self) -> None:
        old = _node(signature="(a)")
        new = _node(signature="(a, b)")
        delta = SemanticDelta(file_path="test.py", modified=[(old, new)])
        d = delta_to_dict(delta)
        self.assertEqual(len(d["modified"]), 1)
        self.assertTrue(d["modified"][0]["signature_changed"])

    def test_modified_same_signature(self) -> None:
        old = _node(signature="(a)")
        new = _node(signature="(a)")
        delta = SemanticDelta(file_path="test.py", modified=[(old, new)])
        d = delta_to_dict(delta)
        self.assertFalse(d["modified"][0]["signature_changed"])

    def test_renamed(self) -> None:
        node = _node(name="new_name")
        delta = SemanticDelta(file_path="test.py", renamed=[("old_name", "new_name", node)])
        d = delta_to_dict(delta)
        self.assertEqual(len(d["renamed"]), 1)
        self.assertEqual(d["renamed"][0]["old"], "old_name")
        self.assertEqual(d["renamed"][0]["new"], "new_name")

    def test_moved(self) -> None:
        node = _node(name="fn")
        delta = SemanticDelta(file_path="test.py", moved=[(node, "OldClass", "NewClass")])
        d = delta_to_dict(delta)
        self.assertEqual(len(d["moved"]), 1)
        self.assertEqual(d["moved"][0]["from"], "OldClass")
        self.assertEqual(d["moved"][0]["to"], "NewClass")

    def test_empty_delta_omits_keys(self) -> None:
        delta = SemanticDelta(file_path="test.py")
        d = delta_to_dict(delta)
        self.assertEqual(d, {"file": "test.py"})


class TestDeltasToJson(unittest.TestCase):
    def test_valid_json(self) -> None:
        delta = SemanticDelta(file_path="test.py", added=[_node()])
        result = deltas_to_json([delta])
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["file"], "test.py")

    def test_skips_empty_deltas(self) -> None:
        empty = SemanticDelta(file_path="empty.py")
        full = SemanticDelta(file_path="full.py", added=[_node()])
        result = deltas_to_json([empty, full])
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)


class TestCommitToDict(unittest.TestCase):
    def test_basic(self) -> None:
        commit = Commit(
            commit_id="abc123",
            parent_id="parent1",
            timestamp="2025-01-01T00:00:00",
            message="Add feature\n\nDetails here",
            branch="main",
            snapshots={"test.py": {}},
        )
        d = commit_to_dict(commit)
        self.assertEqual(d["id"], "abc123")
        self.assertEqual(d["message"], "Add feature")
        self.assertEqual(d["files"], ["test.py"])
        self.assertEqual(d["file_count"], 1)


class TestCommitsToJson(unittest.TestCase):
    def test_valid_json(self) -> None:
        commit = Commit(
            commit_id="abc",
            parent_id=None,
            timestamp="2025-01-01",
            message="init",
            branch="main",
        )
        result = commits_to_json([commit])
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)


class TestStatusToJson(unittest.TestCase):
    def test_valid_json(self) -> None:
        result = status_to_json(
            branch="main",
            head="abc123",
            staged={"test.py": "hash1", "app.py": "hash2"},
            untracked=["new_file.py"],
        )
        parsed = json.loads(result)
        self.assertEqual(parsed["branch"], "main")
        self.assertEqual(parsed["staged_count"], 2)
        self.assertEqual(parsed["untracked"], ["new_file.py"])
        self.assertEqual(parsed["untracked_count"], 1)


if __name__ == "__main__":
    unittest.main()
