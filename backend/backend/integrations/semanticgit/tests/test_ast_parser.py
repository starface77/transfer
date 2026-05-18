"""Tests for the AST parser module."""

from __future__ import annotations

import unittest

from sgit.parsers.ast_parser import flatten_nodes, parse_file

SAMPLE_CODE = '''\
import os
from pathlib import Path

MAX_SIZE = 1024

class Calculator:
    """A simple calculator."""

    default_precision = 2

    def __init__(self, precision: int = 2):
        self.precision = precision

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return round(a + b, self.precision)

    def subtract(self, a: float, b: float) -> float:
        return round(a - b, self.precision)

def helper_function(x):
    return x * 2

async def async_loader(url: str) -> bytes:
    pass
'''


class TestParseFile(unittest.TestCase):
    def test_parse_basic_module(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        self.assertEqual(snap.path, "test.py")
        self.assertTrue(len(snap.nodes) > 0)
        self.assertTrue(snap.raw_hash)

    def test_detects_imports(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        imports = [n for n in snap.nodes if n.kind == "import"]
        names = {n.name for n in imports}
        self.assertIn("os", names)
        self.assertIn("Path", names)

    def test_detects_global_vars(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        gvars = [n for n in snap.nodes if n.kind == "global_var"]
        names = {n.name for n in gvars}
        self.assertIn("MAX_SIZE", names)

    def test_detects_class(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        classes = [n for n in snap.nodes if n.kind == "class"]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, "Calculator")
        self.assertIn("A simple calculator.", classes[0].docstring)

    def test_detects_methods(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        classes = [n for n in snap.nodes if n.kind == "class"]
        calc = classes[0]
        method_names = {c.name for c in calc.children if c.kind == "method"}
        self.assertIn("__init__", method_names)
        self.assertIn("add", method_names)
        self.assertIn("subtract", method_names)

    def test_detects_class_var(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        classes = [n for n in snap.nodes if n.kind == "class"]
        calc = classes[0]
        cvars = [c for c in calc.children if c.kind == "class_var"]
        self.assertEqual(len(cvars), 1)
        self.assertEqual(cvars[0].name, "default_precision")

    def test_detects_functions(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        funcs = [n for n in snap.nodes if n.kind == "function"]
        names = {n.name for n in funcs}
        self.assertIn("helper_function", names)

    def test_detects_async_function(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        afuncs = [n for n in snap.nodes if n.kind == "async_function"]
        self.assertEqual(len(afuncs), 1)
        self.assertEqual(afuncs[0].name, "async_loader")

    def test_function_signature(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        classes = [n for n in snap.nodes if n.kind == "class"]
        calc = classes[0]
        add_method = [c for c in calc.children if c.name == "add"][0]
        self.assertIn("a", add_method.signature)
        self.assertIn("b", add_method.signature)

    def test_flatten_nodes(self) -> None:
        snap = parse_file("test.py", source=SAMPLE_CODE)
        flat = flatten_nodes(snap)
        self.assertIn("Calculator", flat)
        self.assertIn("Calculator.add", flat)
        self.assertIn("Calculator.subtract", flat)
        self.assertIn("helper_function", flat)

    def test_handles_syntax_error(self) -> None:
        snap = parse_file("bad.py", source="def broken(:\n  pass")
        self.assertEqual(snap.nodes, [])
        self.assertTrue(snap.raw_hash)

    def test_semantic_hash_stable(self) -> None:
        snap1 = parse_file("test.py", source=SAMPLE_CODE)
        snap2 = parse_file("test.py", source=SAMPLE_CODE)
        self.assertEqual(snap1.tree_hash(), snap2.tree_hash())

    def test_semantic_hash_changes_on_code_change(self) -> None:
        snap1 = parse_file("test.py", source="def foo(): pass")
        snap2 = parse_file("test.py", source="def foo(): return 1")
        self.assertNotEqual(snap1.tree_hash(), snap2.tree_hash())


if __name__ == "__main__":
    unittest.main()
