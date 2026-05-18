"""Git plugin: integrate s-git as a transparent overlay on standard Git."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

GIT_DIFF_SCRIPT = """\
#!/usr/bin/env bash
# git-semantic-diff: drop this on PATH so `git semantic-diff` works.
# It forwards to `sgit diff` with all arguments.
exec sgit diff "$@"
"""

GIT_MERGE_SCRIPT = """\
#!/usr/bin/env bash
# git-semantic-merge: drop this on PATH so `git semantic-merge` works.
# It forwards to `sgit merge` with all arguments.
exec sgit merge "$@"
"""

GIT_LOG_SCRIPT = """\
#!/usr/bin/env bash
# git-semantic-log: drop this on PATH so `git semantic-log` works.
# It forwards to `sgit log` with all arguments.
exec sgit log "$@"
"""


def install_git_aliases() -> list[str]:
    """Install git aliases that delegate to sgit commands.

    Adds:
      git sdiff  -> sgit diff
      git slog   -> sgit log
      git smerge -> sgit merge

    Returns list of installed alias names.
    """
    import subprocess

    aliases = {
        "sdiff": "!sgit diff",
        "slog": "!sgit log",
        "smerge": "!sgit merge",
        "sstatus": "!sgit status",
        "scommit": "!sgit commit",
    }

    installed: list[str] = []
    for name, cmd in aliases.items():
        try:
            subprocess.run(
                ["git", "config", "--global", f"alias.{name}", cmd],
                check=True,
                capture_output=True,
            )
            installed.append(name)
        except subprocess.CalledProcessError:
            pass

    return installed


def install_git_subcommands(bin_dir: str | None = None) -> list[str]:
    """Install git-semantic-* scripts on PATH.

    After installation:
      git semantic-diff  -> sgit diff
      git semantic-merge -> sgit merge
      git semantic-log   -> sgit log
    """
    if bin_dir is None:
        bin_dir = os.path.expanduser("~/.local/bin")

    bin_path = Path(bin_dir)
    bin_path.mkdir(parents=True, exist_ok=True)

    scripts = {
        "git-semantic-diff": GIT_DIFF_SCRIPT,
        "git-semantic-merge": GIT_MERGE_SCRIPT,
        "git-semantic-log": GIT_LOG_SCRIPT,
    }

    installed: list[str] = []
    for name, content in scripts.items():
        script_path = bin_path / name
        script_path.write_text(content)
        script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
        installed.append(name)

    return installed


def check_git_integration() -> dict[str, bool]:
    """Check which git integrations are active."""
    import subprocess

    result: dict[str, bool] = {}

    for alias in ("sdiff", "slog", "smerge", "sstatus", "scommit"):
        try:
            proc = subprocess.run(
                ["git", "config", "--global", f"alias.{alias}"],
                capture_output=True,
                text=True,
            )
            result[f"alias.{alias}"] = proc.returncode == 0
        except FileNotFoundError:
            result[f"alias.{alias}"] = False

    for cmd in ("git-semantic-diff", "git-semantic-merge", "git-semantic-log"):
        result[cmd] = shutil.which(cmd) is not None

    return result
