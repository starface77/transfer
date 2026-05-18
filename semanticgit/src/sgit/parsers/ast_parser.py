"""AST parser: converts Python source code into semantic trees."""

from __future__ import annotations

import ast
import hashlib
from typing import Optional

from sgit.models import FileSnapshot, SemanticNode


def _hash_source(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()[:16]


def _body_hash(node: ast.AST, source_lines: list[str]) -> str:
    """Hash the source text of an AST node's body."""
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", 0)
    if start and end and start <= len(source_lines) and end <= len(source_lines):
        body_text = "\n".join(source_lines[start - 1 : end])
        return hashlib.sha256(body_text.encode()).hexdigest()[:16]
    return ""


def _get_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Extract function signature as a string."""
    args = node.args
    parts: list[str] = []

    for arg in args.posonlyargs:
        parts.append(_format_arg(arg))
    if args.posonlyargs:
        parts.append("/")

    num_defaults = len(args.defaults)
    num_args = len(args.args)
    for i, arg in enumerate(args.args):
        default_idx = i - (num_args - num_defaults)
        suffix = "=..." if default_idx >= 0 else ""
        parts.append(_format_arg(arg) + suffix)

    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    elif args.kwonlyargs:
        parts.append("*")

    for i, arg in enumerate(args.kwonlyargs):
        suffix = "=..." if i < len(args.kw_defaults) and args.kw_defaults[i] is not None else ""
        parts.append(_format_arg(arg) + suffix)

    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")

    ret = ""
    if node.returns:
        ret = f" -> {ast.dump(node.returns)}"

    return f"({', '.join(parts)}){ret}"


def _format_arg(arg: ast.arg) -> str:
    if arg.annotation:
        return f"{arg.arg}: {ast.dump(arg.annotation)}"
    return arg.arg


def _get_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    decorators: list[str] = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            decorators.append(ast.dump(dec))
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                decorators.append(f"{dec.func.id}(...)")
            elif isinstance(dec.func, ast.Attribute):
                decorators.append(f"{ast.dump(dec.func)}(...)")
            else:
                decorators.append(ast.dump(dec))
        else:
            decorators.append(ast.dump(dec))
    return decorators


def _get_docstring(node: ast.AST) -> str:
    """Extract docstring from a node if present."""
    try:
        return ast.get_docstring(node) or ""
    except TypeError:
        return ""


def _parse_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
    parent_name: str = "",
) -> SemanticNode:
    kind = "method" if parent_name else "function"
    if isinstance(node, ast.AsyncFunctionDef):
        kind = "async_" + kind

    children: list[SemanticNode] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            children.append(_parse_function(child, source_lines, parent_name=node.name))

    return SemanticNode(
        kind=kind,
        name=node.name,
        signature=_get_signature(node),
        docstring=_get_docstring(node),
        body_hash=_body_hash(node, source_lines),
        line_start=node.lineno,
        line_end=node.end_lineno or node.lineno,
        decorators=_get_decorators(node),
        parent_name=parent_name,
        children=children,
    )


def _parse_class(node: ast.ClassDef, source_lines: list[str]) -> SemanticNode:
    bases = ", ".join(ast.dump(b) for b in node.bases)
    children: list[SemanticNode] = []

    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            children.append(_parse_function(child, source_lines, parent_name=node.name))
        elif isinstance(child, ast.ClassDef):
            inner = _parse_class(child, source_lines)
            inner.parent_name = node.name
            children.append(inner)
        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    children.append(
                        SemanticNode(
                            kind="class_var",
                            name=target.id,
                            body_hash=_body_hash(child, source_lines),
                            line_start=child.lineno,
                            line_end=child.end_lineno or child.lineno,
                            parent_name=node.name,
                        )
                    )
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            children.append(
                SemanticNode(
                    kind="class_var",
                    name=child.target.id,
                    body_hash=_body_hash(child, source_lines),
                    line_start=child.lineno,
                    line_end=child.end_lineno or child.lineno,
                    parent_name=node.name,
                )
            )

    return SemanticNode(
        kind="class",
        name=node.name,
        signature=f"({bases})" if bases else "",
        docstring=_get_docstring(node),
        body_hash=_body_hash(node, source_lines),
        line_start=node.lineno,
        line_end=node.end_lineno or node.lineno,
        decorators=_get_decorators(node),
        children=children,
    )


def _parse_import(node: ast.Import | ast.ImportFrom) -> list[SemanticNode]:
    nodes: list[SemanticNode] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            nodes.append(
                SemanticNode(
                    kind="import",
                    name=name,
                    signature=(
                        f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
                    ),
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                )
            )
    else:
        module = node.module or ""
        for alias in node.names:
            name = alias.asname or alias.name
            nodes.append(
                SemanticNode(
                    kind="import",
                    name=name,
                    signature=f"from {module} import {alias.name}"
                    + (f" as {alias.asname}" if alias.asname else ""),
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                )
            )
    return nodes


def parse_file(path: str, source: Optional[str] = None) -> FileSnapshot:
    """Parse a Python file into a FileSnapshot of semantic nodes."""
    if source is None:
        with open(path, encoding="utf-8") as f:
            source = f.read()

    source_lines = source.splitlines()
    raw_hash = _hash_source(source)

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return FileSnapshot(path=path, nodes=[], raw_hash=raw_hash)

    nodes: list[SemanticNode] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes.append(_parse_function(node, source_lines))
        elif isinstance(node, ast.ClassDef):
            nodes.append(_parse_class(node, source_lines))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            nodes.extend(_parse_import(node))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    nodes.append(
                        SemanticNode(
                            kind="global_var",
                            name=target.id,
                            body_hash=_body_hash(node, source_lines),
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                        )
                    )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            nodes.append(
                SemanticNode(
                    kind="global_var",
                    name=node.target.id,
                    body_hash=_body_hash(node, source_lines),
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                )
            )

    return FileSnapshot(path=path, nodes=nodes, raw_hash=raw_hash)


def flatten_nodes(snapshot: FileSnapshot) -> dict[str, SemanticNode]:
    """Flatten all nodes into a dict keyed by qualified name."""
    result: dict[str, SemanticNode] = {}

    def _walk(nodes: list[SemanticNode], prefix: str = "") -> None:
        for node in nodes:
            qname = f"{prefix}.{node.name}" if prefix else node.name
            result[qname] = node
            if node.children:
                _walk(node.children, qname)

    _walk(snapshot.nodes)
    return result
