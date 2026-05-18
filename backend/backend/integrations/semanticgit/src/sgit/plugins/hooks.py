"""Semantic hooks: AST-level pre-commit rules for code quality."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sgit.models import SemanticDelta, SemanticNode

HOOKS_FILE = ".sgit/hooks.json"


@dataclass
class HookViolation:
    """A single hook rule violation."""

    rule: str
    file: str
    element: str
    message: str
    severity: str = "error"


@dataclass
class HookResult:
    """Result of running all hooks."""

    violations: list[HookViolation] = field(default_factory=list)
    passed: int = 0
    failed: int = 0

    @property
    def ok(self) -> bool:
        return all(v.severity != "error" for v in self.violations)


# ---------------------------------------------------------------------------
# Built-in rules
# ---------------------------------------------------------------------------


def _check_signature_docs(
    delta: SemanticDelta,
    _config: dict,
) -> list[HookViolation]:
    """Flag public methods whose signature changed but docstring did not."""
    violations: list[HookViolation] = []
    for old_node, new_node in delta.modified:
        if old_node.signature != new_node.signature:
            if old_node.name.startswith("_"):
                continue
            if old_node.docstring and old_node.docstring == new_node.docstring:
                violations.append(
                    HookViolation(
                        rule="signature-docs",
                        file=delta.file_path,
                        element=new_node.qualified_name,
                        message=(
                            f"Signature of '{new_node.qualified_name}' changed "
                            f"but docstring was not updated"
                        ),
                    )
                )
    return violations


def _check_complexity(
    delta: SemanticDelta,
    config: dict,
) -> list[HookViolation]:
    """Flag functions that are too large (proxy for cyclomatic complexity)."""
    max_lines = config.get("max_lines", 50)
    violations: list[HookViolation] = []

    all_nodes: list[SemanticNode] = []
    all_nodes.extend(delta.added)
    all_nodes.extend(n for _, n in delta.modified)

    for node in all_nodes:
        if node.kind not in ("function", "method", "async_function", "async_method"):
            continue
        length = node.line_end - node.line_start + 1
        if length > max_lines:
            violations.append(
                HookViolation(
                    rule="complexity",
                    file=delta.file_path,
                    element=node.qualified_name,
                    message=(f"'{node.qualified_name}' is {length} lines (max {max_lines})"),
                )
            )
    return violations


def _check_no_delete_public(
    delta: SemanticDelta,
    _config: dict,
) -> list[HookViolation]:
    """Warn when a public symbol is deleted."""
    violations: list[HookViolation] = []
    for node in delta.removed:
        if node.name.startswith("_"):
            continue
        if node.kind in ("function", "method", "class"):
            violations.append(
                HookViolation(
                    rule="no-delete-public",
                    file=delta.file_path,
                    element=node.qualified_name,
                    message=f"Public {node.kind} '{node.qualified_name}' was deleted",
                    severity="warning",
                )
            )
    return violations


def _check_naming(
    delta: SemanticDelta,
    config: dict,
) -> list[HookViolation]:
    """Check naming conventions for new elements."""
    violations: list[HookViolation] = []
    style = config.get("style", "snake_case")

    for node in delta.added:
        if node.kind in ("import", "global_var", "class_var"):
            continue
        name = node.name
        if style == "snake_case" and node.kind in ("function", "method"):
            if name != name.lower() and not name.startswith("_"):
                violations.append(
                    HookViolation(
                        rule="naming",
                        file=delta.file_path,
                        element=node.qualified_name,
                        message=f"'{name}' should use snake_case",
                        severity="warning",
                    )
                )
    return violations


BUILTIN_RULES: dict[str, object] = {
    "signature-docs": _check_signature_docs,
    "complexity": _check_complexity,
    "no-delete-public": _check_no_delete_public,
    "naming": _check_naming,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_hooks_config(root: str | Path) -> dict:
    """Load hooks configuration from .sgit/hooks.json."""
    path = Path(root) / HOOKS_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_hooks_config(root: str | Path, config: dict) -> None:
    """Save hooks configuration to .sgit/hooks.json."""
    path = Path(root) / HOOKS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n")


def default_hooks_config() -> dict:
    """Return a default hooks configuration."""
    return {
        "rules": {
            "signature-docs": {"enabled": True},
            "complexity": {"enabled": True, "max_lines": 50},
            "no-delete-public": {"enabled": True},
            "naming": {"enabled": False, "style": "snake_case"},
        }
    }


def run_hooks(
    deltas: list[SemanticDelta],
    config: Optional[dict] = None,
) -> HookResult:
    """Run all enabled hooks against a list of SemanticDeltas."""
    if config is None:
        config = default_hooks_config()

    result = HookResult()
    rules_config = config.get("rules", {})

    for rule_name, check_fn in BUILTIN_RULES.items():
        rule_cfg = rules_config.get(rule_name, {})
        if not rule_cfg.get("enabled", False):
            continue

        for delta in deltas:
            if not delta.has_changes:
                continue
            violations = check_fn(delta, rule_cfg)
            result.violations.extend(violations)

        if not any(v.rule == rule_name and v.severity == "error" for v in result.violations):
            result.passed += 1
        else:
            result.failed += 1

    return result


def format_hook_result(result: HookResult) -> str:
    """Format hook results for display."""
    if not result.violations:
        return "All semantic hooks passed."

    lines: list[str] = ["Semantic hook results:"]
    for v in result.violations:
        icon = "X" if v.severity == "error" else "!"
        lines.append(f"  [{icon}] {v.rule}: {v.message}")
        lines.append(f"      in {v.file} -> {v.element}")

    errors = sum(1 for v in result.violations if v.severity == "error")
    warnings = sum(1 for v in result.violations if v.severity == "warning")
    lines.append(f"\n{errors} error(s), {warnings} warning(s)")

    if errors > 0:
        lines.append("Commit blocked by semantic hooks.")
    return "\n".join(lines)
