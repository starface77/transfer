"""Tests for the tree-sitter multi-language parser."""

from __future__ import annotations

import unittest

from sgit.parsers.tree_sitter_parser import (
    EXTENSION_MAP,
    detect_language,
    list_supported_languages,
    parse_file_tree_sitter,
)

JS_CODE = """\
import { useState } from 'react';

function greet(name) {
    return `Hello, ${name}!`;
}

class Calculator {
    add(a, b) {
        return a + b;
    }
}

const PI = 3.14;
"""

TS_CODE = """\
interface User {
    name: string;
    age: number;
}

type Status = 'active' | 'inactive';

function getUser(id: number): User {
    return { name: "Alice", age: 30 };
}

class UserService {
    findById(id: number): User | null {
        return null;
    }
}
"""

GO_CODE = """\
package main

import "fmt"

func greet(name string) string {
    return fmt.Sprintf("Hello, %s!", name)
}

type Calculator struct {
    Precision int
}

func (c *Calculator) Add(a, b float64) float64 {
    return a + b
}
"""

RUST_CODE = """\
use std::collections::HashMap;

fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

struct Calculator {
    precision: u32,
}

impl Calculator {
    fn add(&self, a: f64, b: f64) -> f64 {
        a + b
    }
}
"""

JAVA_CODE = """\
import java.util.List;

public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }
}
"""

C_CODE = """\
#include <stdio.h>

struct Point {
    int x;
    int y;
};

int add(int a, int b) {
    return a + b;
}
"""

CPP_CODE = """\
#include <iostream>

namespace math {

class Calculator {
public:
    int add(int a, int b) {
        return a + b;
    }
};

}
"""


class TestDetectLanguage(unittest.TestCase):
    def test_python(self) -> None:
        self.assertEqual(detect_language("app.py"), "python")

    def test_javascript(self) -> None:
        self.assertEqual(detect_language("app.js"), "javascript")
        self.assertEqual(detect_language("app.mjs"), "javascript")
        self.assertEqual(detect_language("app.jsx"), "javascript")

    def test_typescript(self) -> None:
        self.assertEqual(detect_language("app.ts"), "typescript")

    def test_tsx(self) -> None:
        self.assertEqual(detect_language("app.tsx"), "tsx")

    def test_go(self) -> None:
        self.assertEqual(detect_language("main.go"), "go")

    def test_rust(self) -> None:
        self.assertEqual(detect_language("lib.rs"), "rust")

    def test_java(self) -> None:
        self.assertEqual(detect_language("App.java"), "java")

    def test_c(self) -> None:
        self.assertEqual(detect_language("main.c"), "c")
        self.assertEqual(detect_language("header.h"), "c")

    def test_cpp(self) -> None:
        self.assertEqual(detect_language("main.cpp"), "cpp")
        self.assertEqual(detect_language("main.cc"), "cpp")
        self.assertEqual(detect_language("header.hpp"), "cpp")

    def test_unknown(self) -> None:
        self.assertIsNone(detect_language("data.csv"))
        self.assertIsNone(detect_language("README.md"))


class TestListSupportedLanguages(unittest.TestCase):
    def test_returns_all_languages(self) -> None:
        langs = list_supported_languages()
        self.assertIn("python", langs)
        self.assertIn("javascript", langs)
        self.assertIn("typescript", langs)
        self.assertIn("go", langs)
        self.assertIn("rust", langs)
        self.assertIn("java", langs)
        self.assertIn("c", langs)
        self.assertIn("cpp", langs)
        self.assertGreaterEqual(len(langs), 8)


class TestParseJavaScript(unittest.TestCase):
    def test_parses_functions(self) -> None:
        snap = parse_file_tree_sitter("app.js", source=JS_CODE)
        names = {n.name for n in snap.nodes}
        self.assertIn("greet", names)

    def test_parses_classes(self) -> None:
        snap = parse_file_tree_sitter("app.js", source=JS_CODE)
        classes = [n for n in snap.nodes if n.kind == "class"]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, "Calculator")

    def test_parses_variables(self) -> None:
        snap = parse_file_tree_sitter("app.js", source=JS_CODE)
        kinds = {n.kind for n in snap.nodes}
        self.assertIn("variable", kinds)


class TestParseTypeScript(unittest.TestCase):
    def test_parses_interface(self) -> None:
        snap = parse_file_tree_sitter("app.ts", source=TS_CODE)
        interfaces = [n for n in snap.nodes if n.kind == "interface"]
        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0].name, "User")

    def test_parses_type_alias(self) -> None:
        snap = parse_file_tree_sitter("app.ts", source=TS_CODE)
        type_aliases = [n for n in snap.nodes if n.kind == "type_alias"]
        self.assertEqual(len(type_aliases), 1)

    def test_parses_function(self) -> None:
        snap = parse_file_tree_sitter("app.ts", source=TS_CODE)
        funcs = [n for n in snap.nodes if n.kind == "function"]
        names = {n.name for n in funcs}
        self.assertIn("getUser", names)


class TestParseGo(unittest.TestCase):
    def test_parses_function(self) -> None:
        snap = parse_file_tree_sitter("main.go", source=GO_CODE)
        funcs = [n for n in snap.nodes if n.kind == "function"]
        names = {n.name for n in funcs}
        self.assertIn("greet", names)

    def test_parses_struct(self) -> None:
        snap = parse_file_tree_sitter("main.go", source=GO_CODE)
        types = [n for n in snap.nodes if n.kind == "type"]
        self.assertTrue(len(types) >= 1)

    def test_parses_method(self) -> None:
        snap = parse_file_tree_sitter("main.go", source=GO_CODE)
        methods = [n for n in snap.nodes if n.kind == "method"]
        self.assertTrue(len(methods) >= 1)


class TestParseRust(unittest.TestCase):
    def test_parses_function(self) -> None:
        snap = parse_file_tree_sitter("lib.rs", source=RUST_CODE)
        funcs = [n for n in snap.nodes if n.kind == "function"]
        names = {n.name for n in funcs}
        self.assertIn("greet", names)

    def test_parses_struct(self) -> None:
        snap = parse_file_tree_sitter("lib.rs", source=RUST_CODE)
        structs = [n for n in snap.nodes if n.kind == "struct"]
        self.assertEqual(len(structs), 1)
        self.assertEqual(structs[0].name, "Calculator")

    def test_parses_impl(self) -> None:
        snap = parse_file_tree_sitter("lib.rs", source=RUST_CODE)
        impls = [n for n in snap.nodes if n.kind == "impl"]
        self.assertEqual(len(impls), 1)


class TestParseJava(unittest.TestCase):
    def test_parses_class(self) -> None:
        snap = parse_file_tree_sitter("App.java", source=JAVA_CODE)
        classes = [n for n in snap.nodes if n.kind == "class"]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, "Calculator")

    def test_parses_methods(self) -> None:
        snap = parse_file_tree_sitter("App.java", source=JAVA_CODE)
        classes = [n for n in snap.nodes if n.kind == "class"]
        calc = classes[0]
        method_names = {c.name for c in calc.children if c.kind == "method"}
        self.assertIn("add", method_names)
        self.assertIn("subtract", method_names)


class TestParseC(unittest.TestCase):
    def test_parses_function(self) -> None:
        snap = parse_file_tree_sitter("main.c", source=C_CODE)
        funcs = [n for n in snap.nodes if n.kind == "function"]
        self.assertTrue(len(funcs) >= 1)

    def test_parses_struct(self) -> None:
        snap = parse_file_tree_sitter("main.c", source=C_CODE)
        structs = [n for n in snap.nodes if n.kind == "struct"]
        self.assertTrue(len(structs) >= 1)


class TestParseCpp(unittest.TestCase):
    def test_parses_namespace(self) -> None:
        snap = parse_file_tree_sitter("main.cpp", source=CPP_CODE)
        namespaces = [n for n in snap.nodes if n.kind == "namespace"]
        self.assertEqual(len(namespaces), 1)

    def test_snapshot_has_nodes(self) -> None:
        snap = parse_file_tree_sitter("main.cpp", source=CPP_CODE)
        self.assertTrue(len(snap.nodes) > 0)


class TestExtensionMap(unittest.TestCase):
    def test_all_extensions_mapped(self) -> None:
        self.assertIn(".py", EXTENSION_MAP)
        self.assertIn(".js", EXTENSION_MAP)
        self.assertIn(".ts", EXTENSION_MAP)
        self.assertIn(".tsx", EXTENSION_MAP)
        self.assertIn(".go", EXTENSION_MAP)
        self.assertIn(".rs", EXTENSION_MAP)
        self.assertIn(".java", EXTENSION_MAP)
        self.assertIn(".c", EXTENSION_MAP)
        self.assertIn(".cpp", EXTENSION_MAP)


if __name__ == "__main__":
    unittest.main()
