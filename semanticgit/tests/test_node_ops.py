"""Tests for node-level operations: find, history, and checkout."""

from __future__ import annotations

import textwrap

import pytest

from sgit.core.node_ops import (
    _count_params,
    checkout_node,
    extract_node_text,
    find_node_across_snapshots,
    find_node_in_snapshot,
    node_history,
    replace_node_text,
)
from sgit.core.storage import Repository, init_repo
from sgit.models import FileSnapshot
from sgit.parsers.ast_parser import parse_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot(path: str, source: str) -> FileSnapshot:
    """Parse Python source into a FileSnapshot."""
    return parse_file(path, source=source)


def _setup_repo(tmp_path) -> Repository:
    """Create an initialized repo."""
    init_repo(str(tmp_path))
    return Repository(str(tmp_path))


def _commit_file(repo: Repository, rel_path: str, source: str, message: str):
    """Write a file, parse, stage, and commit with source storage."""
    full = repo.root / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(source, encoding="utf-8")
    snap = parse_file(str(full), source=source)
    repo.add_file(rel_path)
    return repo.create_commit(message, {rel_path: snap}, sources={rel_path: source})


# ---------------------------------------------------------------------------
# find_node_in_snapshot
# ---------------------------------------------------------------------------


class TestFindNodeInSnapshot:
    def test_find_top_level_function(self):
        src = "def add(x, y):\n    return x + y\n"
        snap = _make_snapshot("test.py", src)
        node = find_node_in_snapshot(snap, "add")
        assert node is not None
        assert node.name == "add"
        assert node.kind == "function"

    def test_find_class(self):
        src = "class Calculator:\n    pass\n"
        snap = _make_snapshot("test.py", src)
        node = find_node_in_snapshot(snap, "Calculator")
        assert node is not None
        assert node.kind == "class"

    def test_find_method_qualified(self):
        src = textwrap.dedent("""\
            class Calculator:
                def solve(self, x):
                    return x * 2
        """)
        snap = _make_snapshot("test.py", src)
        node = find_node_in_snapshot(snap, "Calculator.solve")
        assert node is not None
        assert node.name == "solve"
        assert node.kind == "method"

    def test_find_nonexistent(self):
        src = "def add(x, y):\n    return x + y\n"
        snap = _make_snapshot("test.py", src)
        assert find_node_in_snapshot(snap, "nonexistent") is None

    def test_find_nested_class_method(self):
        src = textwrap.dedent("""\
            class Outer:
                class Inner:
                    def deep(self):
                        pass
        """)
        snap = _make_snapshot("test.py", src)
        node = find_node_in_snapshot(snap, "Outer.Inner.deep")
        assert node is not None
        assert node.name == "deep"


# ---------------------------------------------------------------------------
# find_node_across_snapshots
# ---------------------------------------------------------------------------


class TestFindNodeAcrossSnapshots:
    def test_find_in_first_file(self):
        snap1 = _make_snapshot("a.py", "def foo(): pass\n")
        snap2 = _make_snapshot("b.py", "def bar(): pass\n")
        result = find_node_across_snapshots({"a.py": snap1, "b.py": snap2}, "foo")
        assert result is not None
        assert result[0] == "a.py"
        assert result[1].name == "foo"

    def test_find_in_second_file(self):
        snap1 = _make_snapshot("a.py", "def foo(): pass\n")
        snap2 = _make_snapshot("b.py", "def bar(): pass\n")
        result = find_node_across_snapshots({"a.py": snap1, "b.py": snap2}, "bar")
        assert result is not None
        assert result[0] == "b.py"

    def test_not_found(self):
        snap = _make_snapshot("a.py", "def foo(): pass\n")
        assert find_node_across_snapshots({"a.py": snap}, "missing") is None


# ---------------------------------------------------------------------------
# extract_node_text / replace_node_text
# ---------------------------------------------------------------------------


class TestNodeTextOps:
    def test_extract_function(self):
        src = "x = 1\ndef add(a, b):\n    return a + b\ny = 2\n"
        snap = _make_snapshot("test.py", src)
        node = find_node_in_snapshot(snap, "add")
        assert node is not None
        text = extract_node_text(src, node)
        assert "def add(a, b):" in text
        assert "return a + b" in text

    def test_extract_class(self):
        src = textwrap.dedent("""\
            class Calc:
                def run(self):
                    return 42
        """)
        snap = _make_snapshot("test.py", src)
        node = find_node_in_snapshot(snap, "Calc")
        assert node is not None
        text = extract_node_text(src, node)
        assert "class Calc:" in text
        assert "return 42" in text

    def test_replace_function(self):
        src = "x = 1\ndef add(a, b):\n    return a + b\ny = 2\n"
        snap = _make_snapshot("test.py", src)
        node = find_node_in_snapshot(snap, "add")
        assert node is not None
        new_src = replace_node_text(src, node, "def add(a, b):\n    return a + b + 1\n")
        assert "return a + b + 1" in new_src
        assert "x = 1" in new_src
        assert "y = 2" in new_src

    def test_replace_preserves_surrounding(self):
        src = "a = 1\ndef foo():\n    pass\nb = 2\n"
        snap = _make_snapshot("test.py", src)
        node = find_node_in_snapshot(snap, "foo")
        assert node is not None
        new_src = replace_node_text(src, node, "def foo():\n    return 99\n")
        assert "a = 1\n" in new_src
        assert "b = 2\n" in new_src
        assert "return 99" in new_src


# ---------------------------------------------------------------------------
# _count_params
# ---------------------------------------------------------------------------


class TestCountParams:
    def test_empty(self):
        assert _count_params("()") == 0
        assert _count_params("") == 0

    def test_simple(self):
        assert _count_params("(x, y)") == 2

    def test_self(self):
        assert _count_params("(self, x, y)") == 3

    def test_defaults(self):
        assert _count_params("(x, y=...)") == 2

    def test_star(self):
        assert _count_params("(*, key)") == 1

    def test_kwargs(self):
        assert _count_params("(**kwargs)") == 1


# ---------------------------------------------------------------------------
# node_history (integration)
# ---------------------------------------------------------------------------


class TestNodeHistory:
    def test_single_creation(self, tmp_path):
        repo = _setup_repo(tmp_path)
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "add function")
        changes = node_history(repo, "add")
        assert len(changes) == 1
        assert changes[0].change_type == "created"

    def test_modification_detected(self, tmp_path):
        repo = _setup_repo(tmp_path)
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v1")
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y + 1\n", "v2")
        changes = node_history(repo, "add")
        assert len(changes) == 2
        assert changes[0].change_type == "modified"
        assert changes[1].change_type == "created"

    def test_unmodified_not_listed(self, tmp_path):
        repo = _setup_repo(tmp_path)
        src = "def add(x, y):\n    return x + y\ndef sub(x, y):\n    return x - y\n"
        _commit_file(repo, "math.py", src, "v1")
        src2 = "def add(x, y):\n    return x + y\ndef sub(x, y):\n    return x - y - 1\n"
        _commit_file(repo, "math.py", src2, "v2 - only sub changed")
        changes = node_history(repo, "add")
        assert len(changes) == 1
        assert changes[0].change_type == "created"

    def test_deletion_detected(self, tmp_path):
        repo = _setup_repo(tmp_path)
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v1")
        _commit_file(repo, "math.py", "x = 1\n", "v2 - removed add")
        changes = node_history(repo, "add")
        assert len(changes) == 2
        assert changes[0].change_type == "deleted"
        assert changes[1].change_type == "created"

    def test_signature_change(self, tmp_path):
        repo = _setup_repo(tmp_path)
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v1")
        _commit_file(repo, "math.py", "def add(x, y, z=0):\n    return x + y\n", "v2")
        changes = node_history(repo, "add")
        assert len(changes) == 2
        assert changes[0].change_type == "modified"

    def test_method_history(self, tmp_path):
        repo = _setup_repo(tmp_path)
        src1 = textwrap.dedent("""\
            class Calc:
                def solve(self, x):
                    return x
        """)
        _commit_file(repo, "calc.py", src1, "v1")
        src2 = textwrap.dedent("""\
            class Calc:
                def solve(self, x):
                    return x * 2
        """)
        _commit_file(repo, "calc.py", src2, "v2")
        changes = node_history(repo, "Calc.solve")
        assert len(changes) == 2
        assert changes[0].change_type == "modified"

    def test_no_history(self, tmp_path):
        repo = _setup_repo(tmp_path)
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v1")
        changes = node_history(repo, "nonexistent")
        assert changes == []

    def test_max_count(self, tmp_path):
        repo = _setup_repo(tmp_path)
        for i in range(5):
            _commit_file(repo, "math.py", f"def add(x, y):\n    return x + y + {i}\n", f"v{i}")
        changes = node_history(repo, "add", max_count=3)
        assert len(changes) == 3


# ---------------------------------------------------------------------------
# checkout_node (integration)
# ---------------------------------------------------------------------------


class TestCheckoutNode:
    def test_restore_function(self, tmp_path):
        repo = _setup_repo(tmp_path)
        c1 = _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v1")
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y + 999\n", "v2")

        # Current file should have v2
        current = (repo.root / "math.py").read_text()
        assert "999" in current

        # Checkout v1
        file_path, msg = checkout_node(repo, "add", c1.commit_id)
        assert file_path == "math.py"
        assert "Restored" in msg

        restored = (repo.root / "math.py").read_text()
        assert "return x + y" in restored
        assert "999" not in restored

    def test_restore_preserves_other_functions(self, tmp_path):
        repo = _setup_repo(tmp_path)
        src1 = "def add(x, y):\n    return x + y\ndef sub(x, y):\n    return x - y\n"
        c1 = _commit_file(repo, "math.py", src1, "v1")
        src2 = "def add(x, y):\n    return x + y + 999\ndef sub(x, y):\n    return x - y - 1\n"
        _commit_file(repo, "math.py", src2, "v2")

        checkout_node(repo, "add", c1.commit_id)
        restored = (repo.root / "math.py").read_text()
        # add should be restored to v1
        assert "999" not in restored
        assert "return x + y" in restored
        # sub should still be v2
        assert "return x - y - 1" in restored

    def test_restore_method(self, tmp_path):
        repo = _setup_repo(tmp_path)
        src1 = textwrap.dedent("""\
            class Calc:
                def solve(self, x):
                    return x
                def reset(self):
                    pass
        """)
        c1 = _commit_file(repo, "calc.py", src1, "v1")
        src2 = textwrap.dedent("""\
            class Calc:
                def solve(self, x):
                    return x * 100
                def reset(self):
                    pass
        """)
        _commit_file(repo, "calc.py", src2, "v2")

        checkout_node(repo, "Calc.solve", c1.commit_id)
        restored = (repo.root / "calc.py").read_text()
        assert "return x\n" in restored
        assert "x * 100" not in restored

    def test_commit_not_found(self, tmp_path):
        repo = _setup_repo(tmp_path)
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v1")
        with pytest.raises(ValueError, match="not found"):
            checkout_node(repo, "add", "deadbeef12345678")

    def test_node_not_in_target_commit(self, tmp_path):
        repo = _setup_repo(tmp_path)
        c1 = _commit_file(repo, "math.py", "x = 1\n", "v1 - no add")
        _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v2")
        with pytest.raises(ValueError, match="not found in commit"):
            checkout_node(repo, "add", c1.commit_id)

    def test_node_not_in_current_file(self, tmp_path):
        repo = _setup_repo(tmp_path)
        c1 = _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v1")
        # Remove add from current file
        (repo.root / "math.py").write_text("x = 1\n")
        with pytest.raises(ValueError, match="not found in current"):
            checkout_node(repo, "add", c1.commit_id)

    def test_file_not_in_working_tree(self, tmp_path):
        repo = _setup_repo(tmp_path)
        c1 = _commit_file(repo, "math.py", "def add(x, y):\n    return x + y\n", "v1")
        (repo.root / "math.py").unlink()
        with pytest.raises(ValueError, match="does not exist"):
            checkout_node(repo, "add", c1.commit_id)
