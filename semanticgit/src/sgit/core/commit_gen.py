"""Auto-generate human-readable commit messages from semantic deltas."""

from __future__ import annotations

from sgit.models import SemanticDelta


def _pluralize(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def generate_commit_message(deltas: list[SemanticDelta]) -> str:
    """Generate a descriptive commit message from a list of semantic deltas."""
    if not deltas:
        return "Empty commit"

    all_added: list[str] = []
    all_removed: list[str] = []
    all_modified: list[str] = []
    all_renamed: list[str] = []
    all_moved: list[str] = []
    files_changed: list[str] = []

    for delta in deltas:
        if not delta.has_changes:
            continue
        files_changed.append(delta.file_path)

        for node in delta.added:
            all_added.append(f"{node.kind} '{node.qualified_name}'")

        for node in delta.removed:
            all_removed.append(f"{node.kind} '{node.qualified_name}'")

        for old_node, new_node in delta.modified:
            desc = f"{new_node.kind} '{new_node.qualified_name}'"
            if old_node.signature != new_node.signature:
                desc += " (signature changed)"
            all_modified.append(desc)

        for old_name, new_name, node in delta.renamed:
            all_renamed.append(f"'{old_name}' -> '{new_name}'")

        for node, old_parent, new_parent in delta.moved:
            all_moved.append(f"'{node.name}' from {old_parent} to {new_parent}")

    if not files_changed:
        return "No semantic changes"

    parts: list[str] = []

    if len(all_added) == 1 and not all_removed and not all_modified:
        parts.append(f"Add {all_added[0]}")
    elif len(all_removed) == 1 and not all_added and not all_modified:
        parts.append(f"Remove {all_removed[0]}")
    elif len(all_modified) == 1 and not all_added and not all_removed:
        parts.append(f"Update {all_modified[0]}")
    elif len(all_renamed) == 1 and not all_added and not all_removed and not all_modified:
        parts.append(f"Rename {all_renamed[0]}")
    else:
        if all_added:
            parts.append(f"Add {_pluralize(len(all_added), 'element', 'elements')}")
        if all_removed:
            parts.append(f"Remove {_pluralize(len(all_removed), 'element', 'elements')}")
        if all_modified:
            parts.append(f"Update {_pluralize(len(all_modified), 'element', 'elements')}")
        if all_renamed:
            parts.append(f"Rename {_pluralize(len(all_renamed), 'element', 'elements')}")
        if all_moved:
            parts.append(f"Move {_pluralize(len(all_moved), 'element', 'elements')}")

    title = "; ".join(parts)

    body_lines: list[str] = []

    if all_added:
        body_lines.append("Added:")
        for item in all_added[:10]:
            body_lines.append(f"  + {item}")
        if len(all_added) > 10:
            body_lines.append(f"  ... and {len(all_added) - 10} more")

    if all_removed:
        body_lines.append("Removed:")
        for item in all_removed[:10]:
            body_lines.append(f"  - {item}")
        if len(all_removed) > 10:
            body_lines.append(f"  ... and {len(all_removed) - 10} more")

    if all_modified:
        body_lines.append("Modified:")
        for item in all_modified[:10]:
            body_lines.append(f"  ~ {item}")
        if len(all_modified) > 10:
            body_lines.append(f"  ... and {len(all_modified) - 10} more")

    if all_renamed:
        body_lines.append("Renamed:")
        for item in all_renamed[:10]:
            body_lines.append(f"  > {item}")

    if all_moved:
        body_lines.append("Moved:")
        for item in all_moved[:10]:
            body_lines.append(f"  >> {item}")

    files_note = _pluralize(len(files_changed), "file", "files")
    body_lines.append(f"\nAffected {files_note}: {', '.join(files_changed)}")

    if body_lines:
        return title + "\n\n" + "\n".join(body_lines)
    return title
