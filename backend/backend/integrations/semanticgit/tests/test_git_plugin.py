"""Tests for the git plugin integration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sgit.plugins.git_plugin import (
    GIT_DIFF_SCRIPT,
    GIT_LOG_SCRIPT,
    GIT_MERGE_SCRIPT,
    install_git_subcommands,
)


class TestInstallGitSubcommands(unittest.TestCase):
    def test_creates_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            installed = install_git_subcommands(bin_dir=tmp)
            self.assertEqual(len(installed), 3)
            self.assertIn("git-semantic-diff", installed)
            self.assertIn("git-semantic-merge", installed)
            self.assertIn("git-semantic-log", installed)

    def test_scripts_are_executable(self) -> None:
        import os
        import stat

        with tempfile.TemporaryDirectory() as tmp:
            install_git_subcommands(bin_dir=tmp)
            for name in ("git-semantic-diff", "git-semantic-merge", "git-semantic-log"):
                script = Path(tmp) / name
                mode = os.stat(script).st_mode
                self.assertTrue(mode & stat.S_IEXEC)

    def test_script_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install_git_subcommands(bin_dir=tmp)
            diff_script = (Path(tmp) / "git-semantic-diff").read_text()
            self.assertEqual(diff_script, GIT_DIFF_SCRIPT)


class TestScriptConstants(unittest.TestCase):
    def test_diff_script_calls_sgit(self) -> None:
        self.assertIn("sgit diff", GIT_DIFF_SCRIPT)

    def test_merge_script_calls_sgit(self) -> None:
        self.assertIn("sgit merge", GIT_MERGE_SCRIPT)

    def test_log_script_calls_sgit(self) -> None:
        self.assertIn("sgit log", GIT_LOG_SCRIPT)


if __name__ == "__main__":
    unittest.main()
