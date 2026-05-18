"""Tests for the semantic merge engine."""

from __future__ import annotations

import unittest

from sgit.core.merge_engine import format_merge_result, merge_snapshots
from sgit.models import FileSnapshot
from sgit.parsers.ast_parser import parse_file

BASE_CODE = """\
class Service:
    def process(self, data):
        return data

    def validate(self, data):
        return True
"""

OURS_CODE = """\
class Service:
    def process(self, data):
        # optimized
        return data.strip()

    def validate(self, data):
        return True
"""

THEIRS_CODE = """\
import logging

class Service:
    def process(self, data):
        return data

    def validate(self, data):
        logging.info("validating")
        return True
"""

CONFLICT_CODE = """\
class Service:
    def process(self, data):
        # different optimization
        return data.upper()

    def validate(self, data):
        return True
"""


class TestMergeSnapshots(unittest.TestCase):
    def test_clean_merge_non_overlapping(self) -> None:
        base = parse_file("svc.py", source=BASE_CODE)
        ours = parse_file("svc.py", source=OURS_CODE)
        theirs = parse_file("svc.py", source=THEIRS_CODE)
        result = merge_snapshots(base, ours, theirs)
        self.assertTrue(len(result.auto_resolved) > 0)

    def test_conflict_same_function(self) -> None:
        base = parse_file("svc.py", source=BASE_CODE)
        ours = parse_file("svc.py", source=OURS_CODE)
        theirs = parse_file("svc.py", source=CONFLICT_CODE)
        result = merge_snapshots(base, ours, theirs)
        self.assertTrue(result.has_conflicts)
        self.assertTrue(any("process" in c for c in result.conflicts))

    def test_identical_changes(self) -> None:
        base = parse_file("svc.py", source=BASE_CODE)
        ours = parse_file("svc.py", source=OURS_CODE)
        result = merge_snapshots(base, ours, ours)
        self.assertFalse(result.has_conflicts)
        self.assertTrue(
            any("identical" in msg for msg in result.auto_resolved),
            f"Expected 'identical' in auto_resolved, got: {result.auto_resolved}",
        )

    def test_new_file_one_side(self) -> None:
        base = FileSnapshot(path="new.py")
        ours = parse_file("new.py", source="def foo(): pass")
        theirs = FileSnapshot(path="new.py")
        result = merge_snapshots(base, ours, theirs)
        self.assertFalse(result.has_conflicts)
        self.assertTrue(len(result.merged_nodes) > 0)

    def test_format_merge_result(self) -> None:
        base = parse_file("svc.py", source=BASE_CODE)
        ours = parse_file("svc.py", source=OURS_CODE)
        theirs = parse_file("svc.py", source=THEIRS_CODE)
        result = merge_snapshots(base, ours, theirs)
        text = format_merge_result(result)
        self.assertIn("svc.py", text)


if __name__ == "__main__":
    unittest.main()
