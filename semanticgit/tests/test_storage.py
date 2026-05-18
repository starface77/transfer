"""Tests for the storage layer."""

from __future__ import annotations

import os
import tempfile
import unittest

from sgit.core.storage import Repository, init_repo
from sgit.parsers.ast_parser import parse_file

SAMPLE_CODE = """\
def greet(name: str) -> str:
    return f"Hello, {name}!"
"""


class TestInitRepo(unittest.TestCase):
    def test_init_creates_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            init_repo(tmp)
            sgit = os.path.join(tmp, ".sgit")
            self.assertTrue(os.path.isdir(sgit))
            self.assertTrue(os.path.isdir(os.path.join(sgit, "objects")))
            self.assertTrue(os.path.isdir(os.path.join(sgit, "commits")))
            self.assertTrue(os.path.isfile(os.path.join(sgit, "HEAD")))
            self.assertTrue(os.path.isfile(os.path.join(sgit, "index.json")))

    def test_init_twice_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            init_repo(tmp)
            with self.assertRaises(FileExistsError):
                init_repo(tmp)


class TestRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        init_repo(self.tmpdir)
        self.repo = Repository(self.tmpdir)

        self.py_file = os.path.join(self.tmpdir, "hello.py")
        with open(self.py_file, "w") as f:
            f.write(SAMPLE_CODE)

    def test_current_branch(self) -> None:
        self.assertEqual(self.repo.current_branch, "main")

    def test_add_and_index(self) -> None:
        self.repo.add_file("hello.py")
        index = self.repo.read_index()
        self.assertIn("hello.py", index)

    def test_commit(self) -> None:
        self.repo.add_file("hello.py")
        snap = parse_file(self.py_file)
        commit = self.repo.create_commit("test commit", {"hello.py": snap})
        self.assertTrue(commit.commit_id)
        self.assertEqual(commit.message, "test commit")
        self.assertIn("hello.py", commit.snapshots)

    def test_head_after_commit(self) -> None:
        self.repo.add_file("hello.py")
        snap = parse_file(self.py_file)
        commit = self.repo.create_commit("first", {"hello.py": snap})
        self.assertEqual(self.repo.head_commit_id(), commit.commit_id)

    def test_log(self) -> None:
        snap = parse_file(self.py_file)
        self.repo.create_commit("first", {"hello.py": snap})
        self.repo.create_commit("second", {"hello.py": snap})
        log = self.repo.log()
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0].message, "second")
        self.assertEqual(log[1].message, "first")

    def test_snapshot_roundtrip(self) -> None:
        snap = parse_file(self.py_file)
        tree_hash = self.repo.store_snapshot(snap)
        loaded = self.repo.load_snapshot(tree_hash)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.path, snap.path)
        self.assertEqual(len(loaded.nodes), len(snap.nodes))

    def test_branch_and_switch(self) -> None:
        snap = parse_file(self.py_file)
        self.repo.create_commit("initial", {"hello.py": snap})
        self.repo.create_branch("feature")
        self.repo.switch_branch("feature")
        self.assertEqual(self.repo.current_branch, "feature")

    def test_list_branches(self) -> None:
        snap = parse_file(self.py_file)
        self.repo.create_commit("initial", {"hello.py": snap})
        self.repo.create_branch("feature")
        branches = self.repo.list_branches()
        self.assertIn("main", branches)
        self.assertIn("feature", branches)


if __name__ == "__main__":
    unittest.main()
