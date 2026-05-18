"""Tests for semantic hooks."""

from __future__ import annotations

import tempfile
import unittest

from sgit.models import SemanticDelta, SemanticNode
from sgit.plugins.hooks import (
    HookResult,
    default_hooks_config,
    format_hook_result,
    load_hooks_config,
    run_hooks,
    save_hooks_config,
)


def _make_node(
    kind: str = "function",
    name: str = "foo",
    signature: str = "()",
    docstring: str = "",
    line_start: int = 1,
    line_end: int = 5,
    parent_name: str = "",
) -> SemanticNode:
    return SemanticNode(
        kind=kind,
        name=name,
        signature=signature,
        docstring=docstring,
        line_start=line_start,
        line_end=line_end,
        parent_name=parent_name,
    )


class TestSignatureDocsRule(unittest.TestCase):
    def test_flags_changed_signature_unchanged_docs(self) -> None:
        old = _make_node(signature="(a)", docstring="Does stuff")
        new = _make_node(signature="(a, b)", docstring="Does stuff")
        delta = SemanticDelta(file_path="test.py", modified=[(old, new)])
        config = {
            "rules": {
                "signature-docs": {"enabled": True},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].rule, "signature-docs")

    def test_no_flag_when_docs_updated(self) -> None:
        old = _make_node(signature="(a)", docstring="Old docs")
        new = _make_node(signature="(a, b)", docstring="New docs")
        delta = SemanticDelta(file_path="test.py", modified=[(old, new)])
        config = {
            "rules": {
                "signature-docs": {"enabled": True},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 0)

    def test_skips_private_methods(self) -> None:
        old = _make_node(name="_private", signature="(a)", docstring="Docs")
        new = _make_node(name="_private", signature="(a, b)", docstring="Docs")
        delta = SemanticDelta(file_path="test.py", modified=[(old, new)])
        config = {
            "rules": {
                "signature-docs": {"enabled": True},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 0)


class TestComplexityRule(unittest.TestCase):
    def test_flags_long_function(self) -> None:
        node = _make_node(line_start=1, line_end=60)
        delta = SemanticDelta(file_path="test.py", added=[node])
        config = {
            "rules": {
                "complexity": {"enabled": True, "max_lines": 50},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].rule, "complexity")

    def test_no_flag_short_function(self) -> None:
        node = _make_node(line_start=1, line_end=10)
        delta = SemanticDelta(file_path="test.py", added=[node])
        config = {
            "rules": {
                "complexity": {"enabled": True, "max_lines": 50},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 0)


class TestNoDeletePublicRule(unittest.TestCase):
    def test_flags_deleted_public_function(self) -> None:
        node = _make_node(kind="function", name="public_fn")
        delta = SemanticDelta(file_path="test.py", removed=[node])
        config = {
            "rules": {
                "no-delete-public": {"enabled": True},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].severity, "warning")

    def test_skips_private(self) -> None:
        node = _make_node(kind="function", name="_private")
        delta = SemanticDelta(file_path="test.py", removed=[node])
        config = {
            "rules": {
                "no-delete-public": {"enabled": True},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 0)


class TestNamingRule(unittest.TestCase):
    def test_flags_camel_case_function(self) -> None:
        node = _make_node(kind="function", name="getData")
        delta = SemanticDelta(file_path="test.py", added=[node])
        config = {
            "rules": {
                "naming": {"enabled": True, "style": "snake_case"},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 1)

    def test_passes_snake_case(self) -> None:
        node = _make_node(kind="function", name="get_data")
        delta = SemanticDelta(file_path="test.py", added=[node])
        config = {
            "rules": {
                "naming": {"enabled": True, "style": "snake_case"},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 0)


class TestRunHooks(unittest.TestCase):
    def test_default_config(self) -> None:
        delta = SemanticDelta(file_path="test.py", added=[_make_node()])
        result = run_hooks([delta])
        self.assertIsInstance(result, HookResult)

    def test_disabled_rules_skipped(self) -> None:
        node = _make_node(line_start=1, line_end=100)
        delta = SemanticDelta(file_path="test.py", added=[node])
        config = {
            "rules": {
                "complexity": {"enabled": False, "max_lines": 10},
            }
        }
        result = run_hooks([delta], config)
        self.assertEqual(len(result.violations), 0)

    def test_ok_property(self) -> None:
        result = HookResult()
        self.assertTrue(result.ok)


class TestHooksConfig(unittest.TestCase):
    def test_save_and_load(self) -> None:
        tmp = tempfile.mkdtemp()
        config = default_hooks_config()
        save_hooks_config(tmp, config)
        loaded = load_hooks_config(tmp)
        self.assertEqual(config, loaded)

    def test_load_missing_returns_empty(self) -> None:
        result = load_hooks_config("/nonexistent/path")
        self.assertEqual(result, {})


class TestFormatHookResult(unittest.TestCase):
    def test_no_violations(self) -> None:
        result = HookResult()
        out = format_hook_result(result)
        self.assertIn("passed", out.lower())

    def test_with_violations(self) -> None:
        from sgit.plugins.hooks import HookViolation

        result = HookResult(
            violations=[
                HookViolation(
                    rule="test-rule",
                    file="test.py",
                    element="foo",
                    message="test failure",
                )
            ]
        )
        out = format_hook_result(result)
        self.assertIn("test-rule", out)


if __name__ == "__main__":
    unittest.main()
