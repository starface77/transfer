"""Local workspace tools for Sharrowkin."""

from __future__ import annotations

import ast
import difflib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for relative in ("integrations/semanticgit/src",):
    candidate = REPO_ROOT / relative
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from sgit.parsers.ast_parser import parse_file as parse_semantic_file
except Exception:
    parse_semantic_file = None

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".sharrowkin",
    "__pycache__",
    "dist",
    "node_modules",
    "venv",
    ".venv",
    "blocksuite",
    "benchmarks",
    "devin_transfer",
    "shrrowkincleanui",
    "build",
    "public",
}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".toml", ".yml", ".yaml", ".css"}


@dataclass(slots=True)
class SymbolSummary:
    kind: str
    name: str
    signature: str
    line: int


@dataclass(slots=True)
class FileSummary:
    path: str
    language: str
    imports: list[str] = field(default_factory=list)
    symbols: list[SymbolSummary] = field(default_factory=list)
    error: str = ""


@dataclass(slots=True)
class ProposedFileChange:
    path: str
    content: str


@dataclass(slots=True)
class PatchResult:
    diff: str
    changed_files: list[str]


@dataclass(slots=True)
class TestResult:
    success: bool
    exit_code: int
    output: str


def resolve_workspace(workspace_path: str) -> Path:
    workspace = Path(workspace_path).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise FileNotFoundError(f"Workspace does not exist or is not a directory: {workspace}")
    return workspace


def safe_relative_path(workspace: Path, candidate: str) -> Path:
    rel = Path(candidate)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe patch path: {candidate}")
    target = (workspace / rel).resolve()
    if workspace not in target.parents and target != workspace:
        raise ValueError(f"Patch path escapes workspace: {candidate}")
    return target


def iter_source_files(workspace: Path, max_files: int = 160) -> list[Path]:
    files: list[Path] = []
    for root, dirs, names in os.walk(workspace):
        dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
        root_path = Path(root)
        for name in sorted(names):
            path = root_path / name
            if path.suffix not in TEXT_SUFFIXES or path.stat().st_size > 200_000:
                continue
            files.append(path)
            if len(files) >= max_files:
                return files
    return files


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _annotation_text(annotation: ast.expr | None) -> str:
    if annotation is None:
        return ""
    return ast.unparse(annotation)


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    parts: list[str] = []
    for arg in node.args.posonlyargs:
        parts.append(arg.arg)
    if node.args.posonlyargs:
        parts.append("/")
    for arg in node.args.args:
        annotation = _annotation_text(arg.annotation)
        parts.append(f"{arg.arg}: {annotation}" if annotation else arg.arg)
    if node.args.vararg:
        parts.append(f"*{node.args.vararg.arg}")
    elif node.args.kwonlyargs:
        parts.append("*")
    for arg in node.args.kwonlyargs:
        annotation = _annotation_text(arg.annotation)
        parts.append(f"{arg.arg}: {annotation}" if annotation else arg.arg)
    if node.args.kwarg:
        parts.append(f"**{node.args.kwarg.arg}")
    returns = _annotation_text(node.returns)
    suffix = f" -> {returns}" if returns else ""
    return f"({', '.join(parts)}){suffix}"


def _append_semantic_node(summary: FileSummary, node) -> None:
    if node.kind == "import":
        summary.imports.append(node.name)
        return
    summary.symbols.append(
        SymbolSummary(node.kind, node.qualified_name, node.signature, node.line_start)
    )
    for child in node.children:
        _append_semantic_node(summary, child)


def parse_python_summary(relative_path: str, source: str) -> FileSummary:
    summary = FileSummary(path=relative_path, language="python")
    if parse_semantic_file is not None:
        snapshot = parse_semantic_file(relative_path, source)
        for node in snapshot.nodes:
            _append_semantic_node(summary, node)
        return summary

    try:
        tree = ast.parse(source, filename=relative_path)
    except SyntaxError as exc:
        summary.error = f"SyntaxError: {exc}"
        return summary

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                summary.imports.extend(alias.name for alias in node.names)
            else:
                module = node.module or ""
                summary.imports.append(module)
        elif isinstance(node, ast.ClassDef):
            summary.symbols.append(SymbolSummary("class", node.name, "", node.lineno))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    kind = "async_method" if isinstance(child, ast.AsyncFunctionDef) else "method"
                    summary.symbols.append(
                        SymbolSummary(kind, f"{node.name}.{child.name}", _function_signature(child), child.lineno)
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            summary.symbols.append(SymbolSummary(kind, node.name, _function_signature(node), node.lineno))
    return summary


def scan_workspace(workspace: Path) -> list[FileSummary]:
    summaries: list[FileSummary] = []
    for path in iter_source_files(workspace):
        relative_path = path.relative_to(workspace).as_posix()
        source = read_text(path)
        if path.suffix == ".py":
            summaries.append(parse_python_summary(relative_path, source))
        else:
            summaries.append(FileSummary(path=relative_path, language=path.suffix.lstrip(".")))
    return summaries


def summarize_workspace(summaries: list[FileSummary], max_files: int = 80) -> str:
    lines: list[str] = []
    for summary in summaries[:max_files]:
        lines.append(f"FILE {summary.path} [{summary.language}]")
        if summary.error:
            lines.append(f"  error: {summary.error}")
        if summary.imports:
            imports = ", ".join(sorted(set(summary.imports))[:12])
            lines.append(f"  imports: {imports}")
        for symbol in summary.symbols[:24]:
            lines.append(f"  {symbol.kind} {symbol.name}{symbol.signature} @ line {symbol.line}")
    if len(summaries) > max_files:
        lines.append(f"... {len(summaries) - max_files} more files omitted")
    return "\n".join(lines)


def apply_changes(workspace: Path, changes: list[ProposedFileChange]) -> PatchResult:
    originals: dict[str, str] = {}
    next_contents: dict[str, str] = {}
    changed_files: list[str] = []
    for change in changes:
        target = safe_relative_path(workspace, change.path)
        original = read_text(target) if target.exists() else ""
        originals[change.path] = original
        next_contents[change.path] = change.content
        if original != change.content:
            changed_files.append(change.path)

    diff = unified_diff(originals, next_contents)
    for change in changes:
        if change.path in changed_files:
            write_text(safe_relative_path(workspace, change.path), change.content)
    return PatchResult(diff=diff, changed_files=changed_files)


def unified_diff(originals: dict[str, str], next_contents: dict[str, str]) -> str:
    chunks: list[str] = []
    for path in sorted(next_contents):
        before = originals.get(path, "").splitlines(keepends=True)
        after = next_contents[path].splitlines(keepends=True)
        chunks.extend(
            difflib.unified_diff(
                before,
                after,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
    return "\n".join(chunks)


def git_diff(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "--"],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    return result.stdout


def run_pytest(workspace: Path, timeout_seconds: int = 120) -> TestResult:
    result = subprocess.run(
        ["python", "-m", "pytest"],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_seconds,
        check=False,
    )
    output = result.stdout[-12_000:]
    no_tests_collected = result.returncode == 5 and "no tests" in output.lower()
    return TestResult(success=result.returncode == 0 or no_tests_collected, exit_code=result.returncode, output=output)


import urllib.request
import urllib.parse
import re

def search_web(query: str, limit: int = 5) -> str:
    """Search the web for documentation or answers using DuckDuckGo."""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        results = []
        snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
        urls = re.findall(r'<a class="result__url" href="([^"]+)">', html, re.IGNORECASE)
        
        for i in range(min(limit, len(snippets), len(urls))):
            text = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            results.append(f"{i+1}. {urls[i]}\n   {text}")
            
        if not results:
            return "No web results found."
        return "\n\n".join(results)
    except Exception as e:
        return f"Web search failed: {str(e)}"

def fetch_url(url: str) -> str:
    """Fetch and extract text content from a URL."""
    try:
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:10000]
    except Exception as e:
        return f"Failed to fetch URL: {str(e)}"


def run_terminal_command(workspace: Path, command: str, timeout_seconds: int = 120) -> TestResult:
    """Run a terminal command (git, npm, pip, etc.) within the workspace."""
    try:
        result = subprocess.run(
            command,
            cwd=workspace,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
        return TestResult(
            success=result.returncode == 0,
            exit_code=result.returncode,
            output=result.stdout or "Command completed with no output."
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            success=False,
            exit_code=-1,
            output=f"Command timed out after {timeout_seconds} seconds."
        )
    except Exception as e:
        return TestResult(
            success=False,
            exit_code=-2,
            output=f"Failed to execute command: {str(e)}"
        )

