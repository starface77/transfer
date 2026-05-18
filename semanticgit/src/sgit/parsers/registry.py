"""Parser registry: routes files to the correct parser (ast or tree-sitter)."""

from __future__ import annotations

from sgit.models import FileSnapshot


def parse_any_file(path: str, source: str | None = None) -> FileSnapshot:
    """Parse a file using the best available parser for its language.

    Python files use the stdlib ``ast`` parser for richer extraction;
    all other supported languages go through tree-sitter.
    """
    if path.endswith(".py"):
        from sgit.parsers.ast_parser import parse_file

        return parse_file(path, source=source)

    from sgit.parsers.tree_sitter_parser import detect_language, parse_file_tree_sitter

    lang = detect_language(path)
    if lang is not None:
        return parse_file_tree_sitter(path, source=source, lang_id=lang)

    return FileSnapshot(path=path, nodes=[], raw_hash="")


def is_supported(path: str) -> bool:
    """Return True if *path* has a file extension we can parse."""
    if path.endswith(".py"):
        return True

    from sgit.parsers.tree_sitter_parser import SUPPORTED_EXTENSIONS

    return any(path.endswith(ext) for ext in SUPPORTED_EXTENSIONS)
