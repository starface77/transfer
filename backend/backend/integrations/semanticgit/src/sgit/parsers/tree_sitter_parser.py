"""Multi-language parser using tree-sitter for 8+ languages."""

from __future__ import annotations

import hashlib
from typing import Optional

from tree_sitter import Language, Node, Parser

from sgit.models import FileSnapshot, SemanticNode

# ---------------------------------------------------------------------------
# Language registry
# ---------------------------------------------------------------------------

_LANG_CACHE: dict[str, Language] = {}


def _get_language(lang_id: str) -> Language:
    if lang_id in _LANG_CACHE:
        return _LANG_CACHE[lang_id]

    loaders: dict[str, tuple[str, str]] = {
        "python": ("tree_sitter_python", "language"),
        "javascript": ("tree_sitter_javascript", "language"),
        "typescript": ("tree_sitter_typescript", "language_typescript"),
        "tsx": ("tree_sitter_typescript", "language_tsx"),
        "go": ("tree_sitter_go", "language"),
        "rust": ("tree_sitter_rust", "language"),
        "java": ("tree_sitter_java", "language"),
        "c": ("tree_sitter_c", "language"),
        "cpp": ("tree_sitter_cpp", "language"),
    }

    if lang_id not in loaders:
        raise ValueError(f"Unsupported language: {lang_id}")

    mod_name, func_name = loaders[lang_id]
    import importlib

    mod = importlib.import_module(mod_name)
    lang = Language(getattr(mod, func_name)())
    _LANG_CACHE[lang_id] = lang
    return lang


EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
}

SUPPORTED_EXTENSIONS = set(EXTENSION_MAP.keys())

# ---------------------------------------------------------------------------
# Language-specific node type mappings
# ---------------------------------------------------------------------------

LANG_CONFIG: dict[str, dict[str, list[str]]] = {
    "python": {
        "function": ["function_definition"],
        "async_function": ["async_function_definition"],  # not in tree-sitter python? Hmm
        "class": ["class_definition"],
        "import": ["import_statement", "import_from_statement"],
        "variable": ["expression_statement"],  # assignments
    },
    "javascript": {
        "function": [
            "function_declaration",
            "generator_function_declaration",
            "arrow_function",
        ],
        "class": ["class_declaration"],
        "import": ["import_statement"],
        "export": ["export_statement"],
        "variable": ["variable_declaration", "lexical_declaration"],
    },
    "typescript": {
        "function": [
            "function_declaration",
            "generator_function_declaration",
            "arrow_function",
        ],
        "class": ["class_declaration"],
        "interface": ["interface_declaration"],
        "type_alias": ["type_alias_declaration"],
        "import": ["import_statement"],
        "export": ["export_statement"],
        "variable": ["variable_declaration", "lexical_declaration"],
    },
    "tsx": {
        "function": [
            "function_declaration",
            "generator_function_declaration",
            "arrow_function",
        ],
        "class": ["class_declaration"],
        "interface": ["interface_declaration"],
        "type_alias": ["type_alias_declaration"],
        "import": ["import_statement"],
        "export": ["export_statement"],
        "variable": ["variable_declaration", "lexical_declaration"],
    },
    "go": {
        "function": ["function_declaration"],
        "method": ["method_declaration"],
        "type": ["type_declaration"],
        "import": ["import_declaration"],
        "variable": ["var_declaration", "short_var_declaration", "const_declaration"],
    },
    "rust": {
        "function": ["function_item"],
        "struct": ["struct_item"],
        "enum": ["enum_item"],
        "impl": ["impl_item"],
        "trait": ["trait_item"],
        "import": ["use_declaration"],
        "variable": ["let_declaration", "const_item", "static_item"],
        "mod": ["mod_item"],
    },
    "java": {
        "class": ["class_declaration"],
        "interface": ["interface_declaration"],
        "enum": ["enum_declaration"],
        "import": ["import_declaration"],
        "method": ["method_declaration", "constructor_declaration"],
        "variable": ["field_declaration", "local_variable_declaration"],
    },
    "c": {
        "function": ["function_definition"],
        "struct": ["struct_specifier"],
        "enum": ["enum_specifier"],
        "variable": ["declaration"],
        "typedef": ["type_definition"],
        "preproc": ["preproc_include", "preproc_def"],
    },
    "cpp": {
        "function": ["function_definition"],
        "class": ["class_specifier"],
        "struct": ["struct_specifier"],
        "enum": ["enum_specifier"],
        "namespace": ["namespace_definition"],
        "variable": ["declaration"],
        "typedef": ["type_definition"],
        "template": ["template_declaration"],
        "preproc": ["preproc_include", "preproc_def"],
    },
}


def _hash_source(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()[:16]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _node_text(node: Node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _find_child_by_type(node: Node, types: str | list[str]) -> Node | None:
    if isinstance(types, str):
        types = [types]
    for child in node.children:
        if child.type in types:
            return child
    return None


def _find_children_by_type(node: Node, types: str | list[str]) -> list[Node]:
    if isinstance(types, str):
        types = [types]
    return [c for c in node.children if c.type in types]


def _extract_name(node: Node, source_bytes: bytes, lang_id: str) -> str:
    """Extract the name of a semantic node."""
    name_node = _find_child_by_type(node, ["identifier", "name", "type_identifier"])
    if name_node:
        return _node_text(name_node, source_bytes)

    if lang_id in ("javascript", "typescript", "tsx"):
        prop = _find_child_by_type(node, "property_identifier")
        if prop:
            return _node_text(prop, source_bytes)

    if node.type in ("import_statement", "import_from_statement", "import_declaration"):
        return _node_text(node, source_bytes).strip()[:80]

    if node.type in ("preproc_include", "preproc_def"):
        return _node_text(node, source_bytes).strip()[:80]

    return f"<{node.type}>"


def _extract_signature(node: Node, source_bytes: bytes, lang_id: str) -> str:
    """Extract function/method signature."""
    params = _find_child_by_type(
        node,
        [
            "parameters",
            "formal_parameters",
            "parameter_list",
            "type_parameters",
        ],
    )
    if params:
        sig = _node_text(params, source_bytes)
        ret = _find_child_by_type(
            node,
            [
                "return_type",
                "type_annotation",
                "result",
                "type",
            ],
        )
        if ret:
            sig += f" -> {_node_text(ret, source_bytes)}"
        return sig
    return ""


def _extract_children_semantic(
    node: Node,
    source_bytes: bytes,
    lang_id: str,
    parent_name: str,
) -> list[SemanticNode]:
    """Extract semantic child nodes (methods, fields, etc.)."""
    config = LANG_CONFIG.get(lang_id, {})
    children: list[SemanticNode] = []

    body = _find_child_by_type(
        node,
        ["block", "class_body", "declaration_list", "field_declaration_list", "body"],
    )
    container = body if body else node

    for child in container.children:
        kind = _classify_node(child, config)
        if kind:
            sem = _make_semantic_node(child, source_bytes, lang_id, kind, parent_name)
            children.append(sem)

    return children


def _classify_node(node: Node, config: dict[str, list[str]]) -> str:
    """Classify a tree-sitter node into a semantic kind."""
    for kind, types in config.items():
        if node.type in types:
            return kind
    return ""


def _make_semantic_node(
    node: Node,
    source_bytes: bytes,
    lang_id: str,
    kind: str,
    parent_name: str = "",
) -> SemanticNode:
    """Convert a tree-sitter node to a SemanticNode."""
    name = _extract_name(node, source_bytes, lang_id)
    signature = ""
    if kind in ("function", "async_function", "method"):
        signature = _extract_signature(node, source_bytes, lang_id)

    body_text = _node_text(node, source_bytes)

    children: list[SemanticNode] = []
    if kind in ("class", "struct", "enum", "interface", "impl", "trait", "namespace", "mod"):
        children = _extract_children_semantic(node, source_bytes, lang_id, name)

    return SemanticNode(
        kind=kind,
        name=name,
        signature=signature,
        docstring="",
        body_hash=_hash_text(body_text),
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        decorators=[],
        parent_name=parent_name,
        children=children,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_language(path: str) -> str | None:
    """Detect language from file extension."""
    for ext, lang in EXTENSION_MAP.items():
        if path.endswith(ext):
            return lang
    return None


def parse_file_tree_sitter(
    path: str,
    source: Optional[str] = None,
    lang_id: Optional[str] = None,
) -> FileSnapshot:
    """Parse a source file using tree-sitter and return a FileSnapshot."""
    if lang_id is None:
        lang_id = detect_language(path)
    if lang_id is None:
        return FileSnapshot(path=path, nodes=[], raw_hash="")

    if source is None:
        with open(path, encoding="utf-8") as f:
            source = f.read()

    raw_hash = _hash_source(source)
    source_bytes = source.encode("utf-8")

    try:
        lang = _get_language(lang_id)
    except (ValueError, ImportError):
        return FileSnapshot(path=path, nodes=[], raw_hash=raw_hash)

    parser = Parser(lang)
    tree = parser.parse(source_bytes)

    config = LANG_CONFIG.get(lang_id, {})
    nodes: list[SemanticNode] = []

    for child in tree.root_node.children:
        kind = _classify_node(child, config)
        if kind:
            sem = _make_semantic_node(child, source_bytes, lang_id, kind)
            nodes.append(sem)

    return FileSnapshot(path=path, nodes=nodes, raw_hash=raw_hash)


def list_supported_languages() -> list[str]:
    """Return list of supported language identifiers."""
    return sorted(LANG_CONFIG.keys())
