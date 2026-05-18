"""Tests for structural code search."""

from __future__ import annotations

import textwrap

from sgit.core.search import SearchPattern, search_snapshot, search_snapshots
from sgit.models import FileSnapshot
from sgit.parsers.ast_parser import parse_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _snap(path: str, source: str) -> FileSnapshot:
    return parse_file(path, source=source)


SAMPLE_SOURCE = textwrap.dedent("""\
    import os

    MAX_SIZE = 100

    def add(x, y):
        return x + y

    def multiply(x, y, z):
        return x * y * z

    async def fetch_data(url: str) -> dict:
        pass

    class Calculator:
        \"\"\"A simple calculator.\"\"\"

        def __init__(self, name):
            self.name = name

        def solve(self, x, y):
            return x + y

        async def remote_solve(self, url, x, y):
            pass

        @staticmethod
        def version():
            return "1.0"

        @property
        def info(self):
            return self.name
""")


# ---------------------------------------------------------------------------
# Search by kind
# ---------------------------------------------------------------------------


class TestSearchByKind:
    def test_find_functions(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(kind="function")
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "add" in names
        assert "multiply" in names
        assert "fetch_data" in names

    def test_find_classes(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(kind="class")
        results, _ = search_snapshot("calc.py", snap, q)
        assert len(results) == 1
        assert results[0].qualified_name == "Calculator"

    def test_find_methods(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(kind="method")
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "Calculator.solve" in names
        assert "Calculator.__init__" in names

    def test_find_async(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(kind="async")
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "fetch_data" in names
        assert "Calculator.remote_solve" in names
        assert "add" not in names


# ---------------------------------------------------------------------------
# Search by name
# ---------------------------------------------------------------------------


class TestSearchByName:
    def test_exact_name(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(name="^add$")
        results, _ = search_snapshot("calc.py", snap, q)
        assert len(results) == 1
        assert results[0].qualified_name == "add"

    def test_name_regex(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(name="solve")
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "Calculator.solve" in names
        assert "Calculator.remote_solve" in names

    def test_name_case_insensitive(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(name="CALCULATOR")
        results, _ = search_snapshot("calc.py", snap, q)
        assert len(results) == 1
        assert results[0].qualified_name == "Calculator"


# ---------------------------------------------------------------------------
# Search by async
# ---------------------------------------------------------------------------


class TestSearchAsync:
    def test_async_only(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(is_async=True)
        results, _ = search_snapshot("calc.py", snap, q)
        for r in results:
            assert r.node.kind.startswith("async_")

    def test_sync_only(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(is_async=False)
        results, _ = search_snapshot("calc.py", snap, q)
        for r in results:
            assert not r.node.kind.startswith("async_")


# ---------------------------------------------------------------------------
# Search by parameter count
# ---------------------------------------------------------------------------


class TestSearchParams:
    def test_exact_params(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(exact_params=3)
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "multiply" in names

    def test_min_params(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(min_params=3)
        results, _ = search_snapshot("calc.py", snap, q)
        # multiply(x, y, z) = 3 params, remote_solve(self, url, x, y) = 4 params
        names = [r.qualified_name for r in results]
        assert "multiply" in names

    def test_max_params(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(max_params=1)
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        # version() = 0 params, info(self) = 1 param, fetch_data(url) = 1
        assert "Calculator.version" in names


# ---------------------------------------------------------------------------
# Search by decorator
# ---------------------------------------------------------------------------


class TestSearchDecorator:
    def test_find_staticmethod(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(has_decorator="staticmethod")
        results, _ = search_snapshot("calc.py", snap, q)
        assert len(results) == 1
        assert results[0].qualified_name == "Calculator.version"

    def test_find_property(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(has_decorator="property")
        results, _ = search_snapshot("calc.py", snap, q)
        assert len(results) == 1
        assert results[0].qualified_name == "Calculator.info"


# ---------------------------------------------------------------------------
# Search by return type
# ---------------------------------------------------------------------------


class TestSearchReturnType:
    def test_find_dict_return(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(return_type="dict")
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "fetch_data" in names


# ---------------------------------------------------------------------------
# Search by parent
# ---------------------------------------------------------------------------


class TestSearchParent:
    def test_methods_of_class(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(parent="Calculator")
        results, _ = search_snapshot("calc.py", snap, q)
        for r in results:
            assert r.node.parent_name == "Calculator"
        names = [r.qualified_name for r in results]
        assert "Calculator.solve" in names

    def test_no_parent(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(parent="NonExistent")
        results, _ = search_snapshot("calc.py", snap, q)
        assert results == []


# ---------------------------------------------------------------------------
# Search by docstring
# ---------------------------------------------------------------------------


class TestSearchDocstring:
    def test_has_docstring(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(has_docstring=True)
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "Calculator" in names

    def test_no_docstring(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(has_docstring=False, kind="function")
        results, _ = search_snapshot("calc.py", snap, q)
        for r in results:
            assert not r.node.docstring


# ---------------------------------------------------------------------------
# Combined / multi-criteria search
# ---------------------------------------------------------------------------


class TestCombinedSearch:
    def test_async_method_with_params(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(is_async=True, kind="method")
        results, _ = search_snapshot("calc.py", snap, q)
        assert len(results) == 1
        assert results[0].qualified_name == "Calculator.remote_solve"

    def test_function_named_pattern_with_min_params(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(kind="function", min_params=2)
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "add" in names
        assert "multiply" in names


# ---------------------------------------------------------------------------
# General pattern search
# ---------------------------------------------------------------------------


class TestPatternSearch:
    def test_general_pattern(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(pattern="add")
        results, _ = search_snapshot("calc.py", snap, q)
        names = [r.qualified_name for r in results]
        assert "add" in names

    def test_no_match(self):
        snap = _snap("calc.py", SAMPLE_SOURCE)
        q = SearchPattern(pattern="zzz_nonexistent_zzz")
        results, _ = search_snapshot("calc.py", snap, q)
        assert results == []


# ---------------------------------------------------------------------------
# Multi-file search
# ---------------------------------------------------------------------------


class TestMultiFileSearch:
    def test_search_across_files(self):
        snap1 = _snap("a.py", "def foo():\n    pass\n")
        snap2 = _snap("b.py", "def bar():\n    pass\n")
        q = SearchPattern(kind="function")
        results = search_snapshots({"a.py": snap1, "b.py": snap2}, q)
        assert len(results.matches) == 2
        assert results.total_files_searched == 2
        files = {m.file_path for m in results.matches}
        assert files == {"a.py", "b.py"}

    def test_empty_snapshots(self):
        q = SearchPattern(kind="function")
        results = search_snapshots({}, q)
        assert results.matches == []
        assert results.total_files_searched == 0


# ---------------------------------------------------------------------------
# SearchResults serialization
# ---------------------------------------------------------------------------


class TestSearchResultsSerialization:
    def test_to_dict(self):
        snap = _snap("calc.py", "def add(x, y):\n    return x + y\n")
        q = SearchPattern(kind="function")
        results = search_snapshots({"calc.py": snap}, q)
        d = results.to_dict()
        assert d["total_matches"] == 1
        assert d["matches"][0]["name"] == "add"
        assert d["matches"][0]["file"] == "calc.py"
