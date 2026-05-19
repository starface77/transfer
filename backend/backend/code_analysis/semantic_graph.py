"""Semantic graph for understanding code structure and relationships.

This module builds a comprehensive graph of code entities (modules, classes,
functions) and their semantic relationships, integrating with DSM for storage.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class CodeNodeType(Enum):
    """Types of code entities."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"


@dataclass
class CodeNode:
    """Represents a code entity in the semantic graph."""

    id: str  # Unique identifier (e.g., "module.Class.method")
    name: str
    node_type: CodeNodeType
    file_path: str = ""
    line_number: int = 0
    end_line_number: int = 0

    # Code content
    docstring: str = ""
    signature: str = ""
    source_code: str = ""

    # Relationships
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)

    # Metadata
    is_public: bool = True
    is_async: bool = False
    is_property: bool = False
    decorators: list[str] = field(default_factory=list)
    complexity: int = 0  # Cyclomatic complexity

    # Additional context
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "end_line_number": self.end_line_number,
            "docstring": self.docstring,
            "signature": self.signature,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "is_public": self.is_public,
            "is_async": self.is_async,
            "decorators": self.decorators,
            "complexity": self.complexity,
            "metadata": self.metadata,
        }


class SemanticGraph:
    """Graph of code entities and their semantic relationships."""

    def __init__(self, dsm_path: Path | None = None) -> None:
        self.nodes: dict[str, CodeNode] = {}
        self.dsm_path = dsm_path or Path(".sharrowkin/semantic_graph")
        self.dsm_path.mkdir(parents=True, exist_ok=True)

    def add_node(self, node: CodeNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

        # Update parent's children list
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.id not in parent.children_ids:
                parent.children_ids.append(node.id)

    def get_node(self, node_id: str) -> CodeNode | None:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> list[CodeNode]:
        """Get all children of a node."""
        node = self.get_node(node_id)
        if not node:
            return []
        return [self.nodes[child_id] for child_id in node.children_ids if child_id in self.nodes]

    def get_descendants(self, node_id: str) -> list[CodeNode]:
        """Get all descendants of a node (recursive)."""
        descendants = []
        to_visit = [node_id]

        while to_visit:
            current_id = to_visit.pop()
            children = self.get_children(current_id)
            descendants.extend(children)
            to_visit.extend(child.id for child in children)

        return descendants

    def get_modules(self) -> list[CodeNode]:
        """Get all module nodes."""
        return [node for node in self.nodes.values() if node.node_type == CodeNodeType.MODULE]

    def get_classes(self, module_id: str | None = None) -> list[CodeNode]:
        """Get all class nodes, optionally filtered by module."""
        classes = [node for node in self.nodes.values() if node.node_type == CodeNodeType.CLASS]
        if module_id:
            classes = [c for c in classes if c.parent_id == module_id]
        return classes

    def get_functions(self, parent_id: str | None = None) -> list[CodeNode]:
        """Get all function/method nodes, optionally filtered by parent."""
        functions = [
            node for node in self.nodes.values()
            if node.node_type in (CodeNodeType.FUNCTION, CodeNodeType.METHOD)
        ]
        if parent_id:
            functions = [f for f in functions if f.parent_id == parent_id]
        return functions

    def search(self, query: str, node_type: CodeNodeType | None = None) -> list[CodeNode]:
        """Search for nodes by name."""
        query_lower = query.lower()
        results = []

        for node in self.nodes.values():
            if node_type and node.node_type != node_type:
                continue

            if query_lower in node.name.lower() or query_lower in node.id.lower():
                results.append(node)

        return results

    def get_call_graph(self, from_dependency_graph: Any) -> dict[str, list[str]]:
        """Build a call graph from dependency information.

        Args:
            from_dependency_graph: DependencyGraph instance with function call info
        """
        call_graph: dict[str, list[str]] = {}

        # Import here to avoid circular dependency
        from .dependency_analyzer import DependencyType

        for dep in from_dependency_graph.dependencies:
            if dep.dep_type == DependencyType.FUNCTION_CALL:
                if dep.source not in call_graph:
                    call_graph[dep.source] = []
                call_graph[dep.source].append(dep.target)

        return call_graph

    def calculate_complexity_metrics(self) -> dict[str, Any]:
        """Calculate complexity metrics for the codebase."""
        total_nodes = len(self.nodes)
        by_type = {}
        for node_type in CodeNodeType:
            by_type[node_type.value] = sum(1 for n in self.nodes.values() if n.node_type == node_type)

        # Calculate average complexity
        functions = [n for n in self.nodes.values() if n.node_type in (CodeNodeType.FUNCTION, CodeNodeType.METHOD)]
        avg_complexity = sum(f.complexity for f in functions) / len(functions) if functions else 0

        # Find most complex functions
        most_complex = sorted(functions, key=lambda f: f.complexity, reverse=True)[:10]

        return {
            "total_nodes": total_nodes,
            "by_type": by_type,
            "total_functions": len(functions),
            "average_complexity": avg_complexity,
            "most_complex": [
                {"id": f.id, "complexity": f.complexity, "line": f.line_number}
                for f in most_complex
            ],
        }

    def visualize(self, root_id: str | None = None, max_depth: int = 3) -> str:
        """Generate a text visualization of the semantic graph."""
        lines = ["Semantic Code Graph", "=" * 50]

        if root_id:
            node = self.get_node(root_id)
            if node:
                self._visualize_node(node, lines, depth=0, max_depth=max_depth)
        else:
            # Show all modules
            for module in self.get_modules():
                self._visualize_node(module, lines, depth=0, max_depth=max_depth)

        return "\n".join(lines)

    def _visualize_node(self, node: CodeNode, lines: list[str], depth: int, max_depth: int) -> None:
        """Recursively visualize a node and its children."""
        if depth >= max_depth:
            return

        indent = "  " * depth
        symbol = {
            CodeNodeType.MODULE: "📦",
            CodeNodeType.CLASS: "🏛️",
            CodeNodeType.FUNCTION: "🔧",
            CodeNodeType.METHOD: "⚙️",
            CodeNodeType.VARIABLE: "📊",
            CodeNodeType.CONSTANT: "🔒",
        }.get(node.node_type, "•")

        # Build node info
        info_parts = [node.name]
        if node.signature:
            info_parts.append(f"({node.signature})")
        if node.complexity > 0:
            info_parts.append(f"[complexity: {node.complexity}]")
        if node.decorators:
            info_parts.append(f"@{', @'.join(node.decorators)}")

        lines.append(f"{indent}{symbol} {' '.join(info_parts)}")

        # Show docstring if available
        if node.docstring and depth < 2:
            doc_preview = node.docstring.split("\n")[0][:60]
            lines.append(f"{indent}   \"{doc_preview}...\"")

        # Recursively show children
        for child in self.get_children(node.id):
            self._visualize_node(child, lines, depth + 1, max_depth)

    def save_to_dsm(self) -> None:
        """Save the semantic graph to DSM storage."""
        graph_file = self.dsm_path / "semantic_graph.json"
        data = {
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "metadata": {
                "total_nodes": len(self.nodes),
                "timestamp": Path(__file__).stat().st_mtime,
            },
        }

        try:
            graph_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Warning: Could not save semantic graph: {e}")

    def load_from_dsm(self) -> bool:
        """Load the semantic graph from DSM storage."""
        graph_file = self.dsm_path / "semantic_graph.json"

        if not graph_file.exists():
            return False

        try:
            data = json.loads(graph_file.read_text())
            self.nodes.clear()

            for node_id, node_data in data["nodes"].items():
                node = CodeNode(
                    id=node_data["id"],
                    name=node_data["name"],
                    node_type=CodeNodeType(node_data["node_type"]),
                    file_path=node_data.get("file_path", ""),
                    line_number=node_data.get("line_number", 0),
                    end_line_number=node_data.get("end_line_number", 0),
                    docstring=node_data.get("docstring", ""),
                    signature=node_data.get("signature", ""),
                    parent_id=node_data.get("parent_id"),
                    children_ids=node_data.get("children_ids", []),
                    is_public=node_data.get("is_public", True),
                    is_async=node_data.get("is_async", False),
                    decorators=node_data.get("decorators", []),
                    complexity=node_data.get("complexity", 0),
                    metadata=node_data.get("metadata", {}),
                )
                self.nodes[node_id] = node

            return True
        except Exception as e:
            print(f"Warning: Could not load semantic graph: {e}")
            return False


class SemanticGraphBuilder:
    """Builds a semantic graph from Python source code."""

    def __init__(self, graph: SemanticGraph) -> None:
        self.graph = graph

    def build_from_file(self, file_path: Path, module_name: str | None = None) -> None:
        """Build semantic graph from a Python file."""
        if module_name is None:
            module_name = file_path.stem

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))

            # Create module node
            module_node = CodeNode(
                id=module_name,
                name=module_name,
                node_type=CodeNodeType.MODULE,
                file_path=str(file_path),
                docstring=ast.get_docstring(tree) or "",
            )
            self.graph.add_node(module_node)

            # Visit AST
            visitor = SemanticGraphVisitor(module_name, str(file_path), self.graph)
            visitor.visit(tree)

        except Exception as e:
            print(f"Warning: Could not build semantic graph for {file_path}: {e}")

    def build_from_directory(self, directory: Path, recursive: bool = True) -> None:
        """Build semantic graph from all Python files in a directory."""
        pattern = "**/*.py" if recursive else "*.py"
        for file_path in directory.glob(pattern):
            if file_path.name.startswith("__") or file_path.name.startswith("."):
                continue

            relative = file_path.relative_to(directory)
            module_name = str(relative.with_suffix("")).replace("/", ".").replace("\\", ".")
            self.build_from_file(file_path, module_name)


class SemanticGraphVisitor(ast.NodeVisitor):
    """AST visitor for building semantic graph."""

    def __init__(self, module_name: str, file_path: str, graph: SemanticGraph) -> None:
        self.module_name = module_name
        self.file_path = file_path
        self.graph = graph
        self.current_class: str | None = None

    def _get_full_name(self, name: str) -> str:
        """Get fully qualified name."""
        parts = [self.module_name]
        if self.current_class:
            parts.append(self.current_class)
        parts.append(name)
        return ".".join(parts)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Handle class definitions."""
        old_class = self.current_class
        self.current_class = node.name

        full_name = self._get_full_name(node.name)
        parent_id = self.module_name if not old_class else f"{self.module_name}.{old_class}"

        class_node = CodeNode(
            id=full_name,
            name=node.name,
            node_type=CodeNodeType.CLASS,
            file_path=self.file_path,
            line_number=node.lineno,
            end_line_number=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node) or "",
            parent_id=parent_id,
            is_public=not node.name.startswith("_"),
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
        )
        self.graph.add_node(class_node)

        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function definitions."""
        full_name = self._get_full_name(node.name)
        parent_id = self.module_name if not self.current_class else f"{self.module_name}.{self.current_class}"

        # Determine if it's a method or function
        node_type = CodeNodeType.METHOD if self.current_class else CodeNodeType.FUNCTION

        # Build signature
        args = [arg.arg for arg in node.args.args]
        signature = ", ".join(args)

        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)

        func_node = CodeNode(
            id=full_name,
            name=node.name,
            node_type=node_type,
            file_path=self.file_path,
            line_number=node.lineno,
            end_line_number=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node) or "",
            signature=signature,
            parent_id=parent_id,
            is_public=not node.name.startswith("_"),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            complexity=complexity,
        )
        self.graph.add_node(func_node)

        self.generic_visit(node)

    def _get_decorator_name(self, node: ast.expr) -> str:
        """Get decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
        return "unknown"

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity
