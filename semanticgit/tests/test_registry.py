"""Tests for the parser registry."""

from __future__ import annotations

import unittest

from sgit.parsers.registry import is_supported, parse_any_file


class TestIsSupported(unittest.TestCase):
    def test_python(self) -> None:
        self.assertTrue(is_supported("app.py"))

    def test_javascript(self) -> None:
        self.assertTrue(is_supported("app.js"))

    def test_typescript(self) -> None:
        self.assertTrue(is_supported("app.ts"))

    def test_tsx(self) -> None:
        self.assertTrue(is_supported("component.tsx"))

    def test_go(self) -> None:
        self.assertTrue(is_supported("main.go"))

    def test_rust(self) -> None:
        self.assertTrue(is_supported("lib.rs"))

    def test_java(self) -> None:
        self.assertTrue(is_supported("App.java"))

    def test_c(self) -> None:
        self.assertTrue(is_supported("main.c"))

    def test_cpp(self) -> None:
        self.assertTrue(is_supported("main.cpp"))

    def test_unsupported(self) -> None:
        self.assertFalse(is_supported("data.csv"))
        self.assertFalse(is_supported("README.md"))
        self.assertFalse(is_supported("image.png"))


class TestParseAnyFile(unittest.TestCase):
    def test_python_uses_ast_parser(self) -> None:
        snap = parse_any_file("test.py", source="def greet(): pass\n")
        self.assertEqual(snap.path, "test.py")
        names = {n.name for n in snap.nodes}
        self.assertIn("greet", names)

    def test_javascript_uses_tree_sitter(self) -> None:
        snap = parse_any_file("app.js", source="function hello() { return 1; }\n")
        self.assertEqual(snap.path, "app.js")
        self.assertTrue(len(snap.nodes) > 0)

    def test_unsupported_returns_empty(self) -> None:
        snap = parse_any_file("data.csv", source="a,b,c\n1,2,3\n")
        self.assertEqual(snap.path, "data.csv")
        self.assertEqual(len(snap.nodes), 0)


if __name__ == "__main__":
    unittest.main()
