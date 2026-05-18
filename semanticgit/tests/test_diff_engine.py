"""Tests for the semantic diff engine."""

from __future__ import annotations

import unittest

from sgit.core.diff_engine import compute_delta, format_delta
from sgit.parsers.ast_parser import parse_file

CODE_V1 = """\
class Service:
    def process(self, data):
        return data

    def validate(self, data):
        return True

def compute_discount(price, rate):
    return price * rate
"""

CODE_V2 = '''\
class Service:
    def process(self, data, timeout=30):
        """Process with timeout."""
        return data

    def validate(self, data):
        return True

class BillingManager:
    def compute_discount(self, price, rate, tax_rate=0.0):
        return price * rate * (1 - tax_rate)
'''

CODE_V3 = """\
class Service:
    def process(self, data):
        return data

    def check(self, data):
        return True

def compute_discount(price, rate):
    return price * rate
"""


class TestComputeDelta(unittest.TestCase):
    def test_detects_modification(self) -> None:
        old = parse_file("svc.py", source=CODE_V1)
        new = parse_file("svc.py", source=CODE_V2)
        delta = compute_delta(old, new)

        modified_names = {n.qualified_name for _, n in delta.modified}
        self.assertIn("Service.process", modified_names)

    def test_detects_added_class(self) -> None:
        old = parse_file("svc.py", source=CODE_V1)
        new = parse_file("svc.py", source=CODE_V2)
        delta = compute_delta(old, new)

        added_names = {n.qualified_name for n in delta.added}
        self.assertIn("BillingManager", added_names)

    def test_detects_removal(self) -> None:
        old = parse_file("svc.py", source=CODE_V1)
        new = parse_file("svc.py", source=CODE_V2)
        delta = compute_delta(old, new)

        removed_names = {n.qualified_name for n in delta.removed}
        self.assertIn("compute_discount", removed_names)

    def test_detects_rename(self) -> None:
        old = parse_file("svc.py", source=CODE_V1)
        new = parse_file("svc.py", source=CODE_V3)
        delta = compute_delta(old, new)

        renamed = {(old_name, new_name) for old_name, new_name, _ in delta.renamed}
        self.assertTrue(
            any("validate" in old_name and "check" in new_name for old_name, new_name in renamed),
            f"Expected rename of validate->check, got: {renamed}",
        )

    def test_no_changes(self) -> None:
        snap = parse_file("svc.py", source=CODE_V1)
        delta = compute_delta(snap, snap)
        self.assertFalse(delta.has_changes)

    def test_format_delta_output(self) -> None:
        old = parse_file("svc.py", source=CODE_V1)
        new = parse_file("svc.py", source=CODE_V2)
        delta = compute_delta(old, new)
        text = format_delta(delta)
        self.assertIn("svc.py", text)
        self.assertIn("Added", text)


class TestEmptySnapshots(unittest.TestCase):
    def test_all_new(self) -> None:
        from sgit.models import FileSnapshot

        old = FileSnapshot(path="new.py")
        new = parse_file("new.py", source="def hello(): pass")
        delta = compute_delta(old, new)
        self.assertTrue(delta.has_changes)
        self.assertEqual(len(delta.added), 1)

    def test_all_removed(self) -> None:
        from sgit.models import FileSnapshot

        old = parse_file("old.py", source="def hello(): pass")
        new = FileSnapshot(path="old.py")
        delta = compute_delta(old, new)
        self.assertTrue(delta.has_changes)
        self.assertEqual(len(delta.removed), 1)


if __name__ == "__main__":
    unittest.main()
