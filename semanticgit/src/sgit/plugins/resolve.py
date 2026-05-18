"""AI-powered conflict resolution for semantic merges."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from sgit.core.merge_engine import MergeResult


@dataclass
class ResolveResult:
    """Result of an AI resolve attempt."""

    file_path: str
    resolved_code: str
    explanation: str
    success: bool
    conflicts_resolved: int = 0


def _build_prompt(
    file_path: str,
    base_code: str,
    our_code: str,
    their_code: str,
    conflicts: list[str],
) -> str:
    """Build a prompt for the AI resolver."""
    return f"""You are a code merge expert. Resolve the following merge conflict.

FILE: {file_path}

CONFLICT SUMMARY:
{chr(10).join(f"- {c}" for c in conflicts)}

BASE VERSION (common ancestor):
```
{base_code}
```

OUR VERSION (current branch):
```
{our_code}
```

THEIR VERSION (incoming branch):
```
{their_code}
```

INSTRUCTIONS:
1. Analyze the semantic intent of both changes.
2. Merge them into a single correct version that preserves both intents.
3. If changes are truly incompatible, prefer the version that is more correct.
4. Return ONLY the merged source code, no explanation.
5. The output must be valid, compilable code.

MERGED CODE:"""


def resolve_with_cli_llm(
    file_path: str,
    base_code: str,
    our_code: str,
    their_code: str,
    conflicts: list[str],
    model: str = "default",
) -> ResolveResult:
    """Resolve conflicts by calling an external LLM via stdin/stdout.

    The resolver looks for an executable called ``sgit-llm`` on PATH.
    It sends the prompt on stdin and reads the merged code on stdout.
    If no ``sgit-llm`` is found, falls back to a simple heuristic merge.
    """
    prompt = _build_prompt(file_path, base_code, our_code, their_code, conflicts)

    try:
        proc = subprocess.run(
            ["sgit-llm", "--model", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return ResolveResult(
                file_path=file_path,
                resolved_code=proc.stdout.strip(),
                explanation="Resolved by AI model via sgit-llm",
                success=True,
                conflicts_resolved=len(conflicts),
            )
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass

    return _heuristic_resolve(file_path, base_code, our_code, their_code, conflicts)


def _heuristic_resolve(
    file_path: str,
    base_code: str,
    our_code: str,
    their_code: str,
    conflicts: list[str],
) -> ResolveResult:
    """Simple heuristic: prefer our version but append any new lines from theirs."""
    our_lines = set(our_code.splitlines())
    their_lines = their_code.splitlines()
    base_lines = set(base_code.splitlines())

    additions = [line for line in their_lines if line not in our_lines and line not in base_lines]

    if additions:
        merged = our_code.rstrip() + "\n" + "\n".join(additions) + "\n"
        return ResolveResult(
            file_path=file_path,
            resolved_code=merged,
            explanation=(
                "Heuristic merge: kept our version and appended "
                f"{len(additions)} new line(s) from theirs. "
                "Install sgit-llm for AI-powered resolution."
            ),
            success=True,
            conflicts_resolved=len(conflicts),
        )

    return ResolveResult(
        file_path=file_path,
        resolved_code=our_code,
        explanation=(
            "Could not auto-resolve: kept our version. Install sgit-llm for AI-powered resolution."
        ),
        success=False,
        conflicts_resolved=0,
    )


def resolve_merge_conflicts(
    merge_result: MergeResult,
    base_code: str,
    our_code: str,
    their_code: str,
    model: str = "default",
) -> ResolveResult:
    """Attempt to resolve all conflicts in a MergeResult."""
    if not merge_result.has_conflicts:
        return ResolveResult(
            file_path=merge_result.file_path,
            resolved_code=our_code,
            explanation="No conflicts to resolve.",
            success=True,
        )

    return resolve_with_cli_llm(
        file_path=merge_result.file_path,
        base_code=base_code,
        our_code=our_code,
        their_code=their_code,
        conflicts=merge_result.conflicts,
        model=model,
    )


def format_resolve_result(result: ResolveResult) -> str:
    """Format a ResolveResult for display."""
    lines: list[str] = [f"Resolve result for {result.file_path}:"]
    if result.success:
        lines.append(f"  Resolved {result.conflicts_resolved} conflict(s)")
        lines.append(f"  {result.explanation}")
    else:
        lines.append("  Failed to auto-resolve")
        lines.append(f"  {result.explanation}")
    return "\n".join(lines)
