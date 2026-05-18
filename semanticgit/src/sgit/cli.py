"""CLI entry point for s-git: semantic version control."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from sgit.core.commit_gen import generate_commit_message
from sgit.core.diff_engine import compute_delta, format_deltas
from sgit.core.merge_engine import format_merge_result, merge_snapshots
from sgit.core.storage import Repository, init_repo
from sgit.models import FileSnapshot, SemanticDelta
from sgit.parsers.registry import is_supported, parse_any_file


@click.group()
@click.version_option(package_name="s-git")
def main() -> None:
    """s-git: Semantic Git -- version control that tracks meaning, not text."""


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def init(path: str) -> None:
    """Initialize a new s-git repository."""
    try:
        root = init_repo(path)
        click.echo(f"Initialized empty s-git repository in {root / '.sgit'}")
    except FileExistsError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("files", nargs=-1, type=click.Path())
def add(files: tuple[str, ...]) -> None:
    """Stage files for the next commit."""
    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if not files:
        click.echo("Nothing specified to add. Use 'sgit add <file>' or 'sgit add .'")
        return

    added_count = 0
    for file_arg in files:
        if file_arg == ".":
            for src_file in repo.list_tracked_files():
                repo.add_file(src_file)
                added_count += 1
        else:
            if Path(file_arg).is_absolute():
                rel = str(Path(file_arg).relative_to(repo.root))
            else:
                rel = file_arg
            if not is_supported(rel):
                click.echo(f"Skipping unsupported file: {rel}")
                continue
            try:
                repo.add_file(rel)
                added_count += 1
            except FileNotFoundError:
                click.echo(f"File not found: {rel}", err=True)

    click.echo(f"Staged {added_count} file(s)")


@main.command()
@click.option(
    "-m",
    "--message",
    default=None,
    help="Override auto-generated commit message.",
)
@click.option("--no-hooks", is_flag=True, help="Skip semantic hooks.")
def commit(message: str | None, no_hooks: bool) -> None:
    """Create a semantic commit (auto-generates message from AST diff)."""
    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    index = repo.read_index()
    if not index:
        click.echo("Nothing to commit. Use 'sgit add' to stage files first.")
        return

    current_snapshots: dict[str, FileSnapshot] = {}
    sources: dict[str, str] = {}
    for rel_path in index:
        full_path = repo.root / rel_path
        if full_path.exists():
            current_snapshots[rel_path] = parse_any_file(str(full_path))
            sources[rel_path] = full_path.read_text(encoding="utf-8")

    deltas = _compute_deltas_vs_head(repo, current_snapshots)

    if not no_hooks:
        from sgit.plugins.hooks import (
            format_hook_result,
            load_hooks_config,
            run_hooks,
        )

        hooks_config = load_hooks_config(repo.root)
        if hooks_config:
            hook_result = run_hooks(deltas, hooks_config)
            if not hook_result.ok:
                click.echo(format_hook_result(hook_result), err=True)
                click.echo("Use --no-hooks to skip.", err=True)
                sys.exit(1)
            if hook_result.violations:
                click.echo(format_hook_result(hook_result))

    if message is None:
        message = generate_commit_message(deltas)

    commit_obj = repo.create_commit(message, current_snapshots, sources=sources)

    title = message.split("\n")[0]
    click.echo(f"[{repo.current_branch} {commit_obj.commit_id[:8]}] {title}")
    click.echo(f"  {len(current_snapshots)} file(s) committed")


@main.command()
@click.argument("ref", default=None, required=False)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON for AI agents.",
)
def diff(ref: str | None, as_json: bool) -> None:
    """Show semantic diff (working tree vs HEAD, or between commits)."""
    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if ref is not None:
        parts = ref.split("..")
        if len(parts) == 2:
            deltas = _get_deltas_commits(repo, parts[0], parts[1])
        else:
            deltas = _get_deltas_ref_vs_working(repo, ref)
    else:
        deltas = _get_deltas_head_vs_working(repo)

    active = [d for d in deltas if d.has_changes]

    if not active:
        if as_json:
            click.echo("[]")
        else:
            click.echo("No semantic changes detected.")
        return

    if as_json:
        from sgit.plugins.json_output import deltas_to_json

        click.echo(deltas_to_json(active))
    else:
        click.echo(format_deltas(active))


def _get_deltas_head_vs_working(
    repo: Repository,
) -> list[SemanticDelta]:
    """Compute deltas: working directory vs HEAD."""
    src_files = repo.list_tracked_files()
    if not src_files:
        return []

    current_snapshots: dict[str, FileSnapshot] = {}
    for f in src_files:
        full = repo.root / f
        if full.exists():
            current_snapshots[f] = parse_any_file(str(full))

    return _compute_deltas_vs_head(repo, current_snapshots)


def _get_deltas_ref_vs_working(
    repo: Repository,
    ref: str,
) -> list[SemanticDelta]:
    """Compute deltas: a specific commit vs working directory."""
    commit_obj = repo.get_commit(ref)
    if commit_obj is None:
        click.echo(f"Commit not found: {ref}", err=True)
        sys.exit(1)

    old_snapshots = repo.get_commit_snapshots(commit_obj)

    src_files = repo.list_tracked_files()
    new_snapshots: dict[str, FileSnapshot] = {}
    for f in src_files:
        full = repo.root / f
        if full.exists():
            new_snapshots[f] = parse_any_file(str(full))

    return _compute_deltas_between(old_snapshots, new_snapshots)


def _get_deltas_commits(
    repo: Repository,
    ref_a: str,
    ref_b: str,
) -> list[SemanticDelta]:
    """Compute deltas between two commits."""
    commit_a = repo.get_commit(ref_a)
    commit_b = repo.get_commit(ref_b)
    if commit_a is None:
        click.echo(f"Commit not found: {ref_a}", err=True)
        sys.exit(1)
    if commit_b is None:
        click.echo(f"Commit not found: {ref_b}", err=True)
        sys.exit(1)

    old_snaps = repo.get_commit_snapshots(commit_a)
    new_snaps = repo.get_commit_snapshots(commit_b)
    return _compute_deltas_between(old_snaps, new_snaps)


@main.command()
@click.option("-n", "--count", default=10, help="Number of commits to show.")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON for AI agents.",
)
def log(count: int, as_json: bool) -> None:
    """Show commit history with semantic messages."""
    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    commits = repo.log(max_count=count)
    if not commits:
        if as_json:
            click.echo("[]")
        else:
            click.echo("No commits yet.")
        return

    if as_json:
        from sgit.plugins.json_output import commits_to_json

        click.echo(commits_to_json(commits))
    else:
        for c in commits:
            title = c.message.split("\n")[0]
            files = len(c.snapshots)
            click.echo(f"commit {c.commit_id} ({c.branch})")
            click.echo(f"  Date:  {c.timestamp}")
            click.echo(f"  Files: {files}")
            click.echo(f"  {title}")
            click.echo()


@main.command()
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON for AI agents.",
)
def status(as_json: bool) -> None:
    """Show repository status."""
    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    branch = repo.current_branch
    head = repo.head_commit_id()
    index = repo.read_index()
    src_files = repo.list_tracked_files()

    untracked: list[str] = []
    if head and src_files:
        head_commit = repo.get_commit(head)
        if head_commit:
            committed_files = set(head_commit.snapshots.keys())
            untracked = [f for f in src_files if f not in committed_files and f not in index]
    elif src_files and not index:
        untracked = src_files

    if as_json:
        from sgit.plugins.json_output import status_to_json

        click.echo(status_to_json(branch, head, index, untracked))
        return

    click.echo(f"On branch {branch}")
    if head:
        click.echo(f"HEAD: {head[:8]}")
    else:
        click.echo("No commits yet")

    if index:
        click.echo(f"\nStaged files ({len(index)}):")
        for path in sorted(index):
            click.echo(f"  {path}")

    if untracked:
        click.echo(f"\nUntracked files ({len(untracked)}):")
        for f in untracked:
            click.echo(f"  {f}")


@main.command()
@click.argument("branch_name")
def branch(branch_name: str) -> None:
    """Create a new branch."""
    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    try:
        repo.create_branch(branch_name)
        click.echo(f"Created branch '{branch_name}'")
    except FileExistsError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("branch_name")
def checkout(branch_name: str) -> None:
    """Switch to a different branch."""
    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    try:
        repo.switch_branch(branch_name)
        click.echo(f"Switched to branch '{branch_name}'")
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("branch_name")
def merge(branch_name: str) -> None:
    """Semantically merge a branch into the current branch."""
    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    their_ref = repo.sgit / "refs" / "heads" / branch_name
    if not their_ref.exists():
        click.echo(f"Branch '{branch_name}' not found.", err=True)
        sys.exit(1)

    their_commit_id = their_ref.read_text().strip()
    their_commit = repo.get_commit(their_commit_id)
    our_commit_id = repo.head_commit_id()

    if not their_commit:
        click.echo(
            f"Could not load commit for branch '{branch_name}'.",
            err=True,
        )
        sys.exit(1)

    if not our_commit_id:
        click.echo("Current branch has no commits.", err=True)
        sys.exit(1)

    our_commit = repo.get_commit(our_commit_id)
    if not our_commit:
        click.echo("Could not load HEAD commit.", err=True)
        sys.exit(1)

    base_commit_id = _find_common_ancestor(
        repo,
        our_commit_id,
        their_commit_id,
    )

    our_snaps = repo.get_commit_snapshots(our_commit)
    their_snaps = repo.get_commit_snapshots(their_commit)

    if base_commit_id:
        base_commit = repo.get_commit(base_commit_id)
        base_snaps = repo.get_commit_snapshots(base_commit) if base_commit else {}
    else:
        base_snaps = {}

    all_files = set(our_snaps) | set(their_snaps)
    total_conflicts = 0
    total_resolved = 0
    merged_snapshots: dict[str, FileSnapshot] = {}

    for fpath in sorted(all_files):
        base_snap = base_snaps.get(fpath, FileSnapshot(path=fpath))
        our_snap = our_snaps.get(fpath, FileSnapshot(path=fpath))
        their_snap = their_snaps.get(fpath, FileSnapshot(path=fpath))

        result = merge_snapshots(base_snap, our_snap, their_snap)
        click.echo(format_merge_result(result))
        click.echo()

        total_conflicts += len(result.conflicts)
        total_resolved += len(result.auto_resolved)
        merged_snapshots[fpath] = our_snap

    if total_conflicts == 0:
        merge_msg = f"Merge branch '{branch_name}' into {repo.current_branch}"
        if total_resolved:
            merge_msg += f"\n\nAuto-resolved {total_resolved} change(s) semantically."
        repo.create_commit(merge_msg, merged_snapshots)
        click.echo(f"Merge complete! {total_resolved} change(s) auto-resolved, 0 conflicts.")
    else:
        click.echo(
            f"\nMerge has {total_conflicts} conflict(s) and "
            f"{total_resolved} auto-resolved change(s)."
        )
        click.echo("Resolve conflicts manually or use 'sgit resolve'.")


@main.command()
@click.argument("file_path", required=False)
@click.option(
    "--model",
    default="default",
    help="LLM model to use for AI resolution.",
)
def resolve(file_path: str | None, model: str) -> None:
    """AI-powered conflict resolution.

    Sends conflicting code to an LLM (via sgit-llm on PATH) to produce
    a merged result.  Falls back to heuristic merge if no LLM is available.
    """
    from sgit.plugins.resolve import format_resolve_result, resolve_with_cli_llm

    if file_path is None:
        click.echo("Usage: sgit resolve <file>")
        click.echo("Sends conflicting versions to an AI model for intelligent resolution.")
        click.echo("\nRequires 'sgit-llm' on PATH (or set SGIT_LLM_COMMAND).")
        return

    p = Path(file_path)
    if not p.exists():
        click.echo(f"File not found: {file_path}", err=True)
        sys.exit(1)

    source = p.read_text(encoding="utf-8")
    result = resolve_with_cli_llm(
        file_path=file_path,
        base_code="",
        our_code=source,
        their_code=source,
        conflicts=["Manual resolve request"],
        model=model,
    )

    click.echo(format_resolve_result(result))


@main.command()
@click.argument("action", type=click.Choice(["init", "check", "list"]))
def hooks(action: str) -> None:
    r"""Manage semantic hooks (pre-commit AST rules).

    \b
    Actions:
      init   Create default hooks configuration
      check  Run hooks against staged changes
      list   Show configured rules
    """
    from sgit.plugins.hooks import (
        default_hooks_config,
        format_hook_result,
        load_hooks_config,
        run_hooks,
        save_hooks_config,
    )

    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if action == "init":
        config = default_hooks_config()
        save_hooks_config(repo.root, config)
        click.echo("Created default semantic hooks in .sgit/hooks.json")
        click.echo("Rules:")
        for name, cfg in config["rules"].items():
            state = "enabled" if cfg.get("enabled") else "disabled"
            click.echo(f"  {name}: {state}")

    elif action == "list":
        config = load_hooks_config(repo.root)
        if not config:
            click.echo("No hooks configured. Run 'sgit hooks init' first.")
            return
        click.echo("Semantic hook rules:")
        for name, cfg in config.get("rules", {}).items():
            state = "enabled" if cfg.get("enabled") else "disabled"
            click.echo(f"  {name}: {state}")

    elif action == "check":
        config = load_hooks_config(repo.root)
        if not config:
            click.echo("No hooks configured. Run 'sgit hooks init' first.")
            return

        src_files = repo.list_tracked_files()
        current: dict[str, FileSnapshot] = {}
        for f in src_files:
            full = repo.root / f
            if full.exists():
                current[f] = parse_any_file(str(full))

        deltas = _compute_deltas_vs_head(repo, current)
        result = run_hooks(deltas, config)
        click.echo(format_hook_result(result))
        if not result.ok:
            sys.exit(1)


@main.command(name="git-install")
def git_install() -> None:
    """Install git aliases and subcommands for seamless integration.

    After running this, you can use:
      git sdiff    -> sgit diff
      git slog     -> sgit log
      git smerge   -> sgit merge
      git sstatus  -> sgit status
      git scommit  -> sgit commit
    """
    from sgit.plugins.git_plugin import (
        install_git_aliases,
        install_git_subcommands,
    )

    aliases = install_git_aliases()
    if aliases:
        click.echo(f"Installed git aliases: {', '.join(aliases)}")
    else:
        click.echo("Failed to install git aliases.")

    scripts = install_git_subcommands()
    if scripts:
        click.echo(f"Installed git subcommands: {', '.join(scripts)}")
    else:
        click.echo("Failed to install git subcommands.")

    click.echo("\nYou can now use:")
    click.echo("  git sdiff          -- semantic diff")
    click.echo("  git slog           -- semantic log")
    click.echo("  git smerge <br>    -- semantic merge")
    click.echo("  git sstatus        -- semantic status")
    click.echo("  git scommit        -- semantic commit")


@main.command()
def languages() -> None:
    """List supported programming languages."""
    from sgit.parsers.tree_sitter_parser import (
        EXTENSION_MAP,
        list_supported_languages,
    )

    click.echo("Supported languages:")
    for lang in list_supported_languages():
        exts = [ext for ext, lid in EXTENSION_MAP.items() if lid == lang]
        click.echo(f"  {lang:14s}  {', '.join(exts)}")
    click.echo(f"\n{len(list_supported_languages())} languages supported via tree-sitter")


@main.command()
@click.argument("action", type=click.Choice(["stats", "clear"]))
def cache(action: str) -> None:
    r"""Manage the incremental parsing cache (DSM).

    \b
    Actions:
      stats  Show cache hit/miss statistics
      clear  Clear the entire cache
    """
    from sgit.parsers.cache import ParseCache

    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    pc = ParseCache(repo.sgit / "cache")
    if action == "stats":
        s = pc.stats()
        click.echo(f"Cached files: {s['cached_files']}")
        click.echo(f"Hits: {s['hits']}, Misses: {s['misses']}")
    elif action == "clear":
        pc.clear()
        click.echo("Cache cleared.")


@main.command("log-node")
@click.argument("node_name")
@click.option("-n", "--count", default=20, help="Max number of changes to show.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def log_node(node_name: str, count: int, as_json: bool) -> None:
    """Show commit history for a specific function/class.

    NODE_NAME is the qualified name, e.g. 'Calculator.solve' or 'add'.
    """
    from sgit.core.node_ops import node_history

    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    changes = node_history(repo, node_name, max_count=count)

    if not changes:
        click.echo(f"No history found for '{node_name}'.")
        return

    if as_json:
        import json

        out = [
            {
                "commit_id": ch.commit.commit_id,
                "timestamp": ch.commit.timestamp,
                "message": ch.commit.message,
                "change_type": ch.change_type,
                "file": ch.file_path,
                "kind": ch.node.kind,
                "signature": ch.node.signature,
                "body_hash": ch.node.body_hash,
            }
            for ch in changes
        ]
        click.echo(json.dumps(out, indent=2))
        return

    click.echo(f"History of {node_name}:")
    click.echo()
    for ch in changes:
        short_id = ch.commit.commit_id[:8]
        symbol = {"created": "+", "modified": "~", "deleted": "-"}.get(ch.change_type, "?")
        click.echo(f"  [{short_id}] {ch.commit.timestamp}")
        click.echo(f"    {symbol} {ch.change_type.capitalize()}: {ch.node.kind} {node_name}")
        if ch.change_type == "modified" and ch.old_node:
            if ch.old_node.signature != ch.node.signature:
                click.echo(f"      signature: {ch.old_node.signature} -> {ch.node.signature}")
            else:
                click.echo("      body changed")
        click.echo(f"    {ch.commit.message.split(chr(10))[0]}")
        click.echo()


@main.command("checkout-node")
@click.argument("node_name")
@click.option("--commit", "commit_id", required=True, help="Commit hash to restore from.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def checkout_node_cmd(node_name: str, commit_id: str, as_json: bool) -> None:
    """Restore a specific function/class from a past commit.

    This replaces only the specified node in the current file,
    leaving all other code untouched.

    \b
    Examples:
      sgit checkout-node Calculator.solve --commit d388a7
      sgit checkout-node add --commit f8a12b99
    """
    from sgit.core.node_ops import checkout_node

    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    try:
        file_path, msg = checkout_node(repo, node_name, commit_id)
    except ValueError as exc:
        if as_json:
            import json

            click.echo(json.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if as_json:
        import json

        out = {
            "file": file_path,
            "node": node_name,
            "commit": commit_id,
            "message": msg,
        }
        click.echo(json.dumps(out))
    else:
        click.echo(msg)


@main.command()
@click.option("--kind", help="Filter by node kind (function, class, method, async).")
@click.option("--name", "name_pattern", help="Filter by name (regex).")
@click.option("--signature", "sig_pattern", help="Filter by signature (regex).")
@click.option(
    "--async",
    "is_async",
    is_flag=True,
    default=None,
    help="Only async functions/methods.",
)
@click.option("--params", type=int, default=None, help="Exact parameter count.")
@click.option("--min-params", type=int, default=None, help="Minimum parameter count.")
@click.option("--max-params", type=int, default=None, help="Maximum parameter count.")
@click.option("--decorator", "has_decorator", help="Has decorator matching this string.")
@click.option("--return-type", help="Return type contains this string.")
@click.option("--parent", help="Parent class/module name (regex).")
@click.option("--has-docstring/--no-docstring", default=None, help="Filter by docstring presence.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.argument("pattern", required=False, default=None)
def search(
    kind: str | None,
    name_pattern: str | None,
    sig_pattern: str | None,
    is_async: bool | None,
    params: int | None,
    min_params: int | None,
    max_params: int | None,
    has_decorator: str | None,
    return_type: str | None,
    parent: str | None,
    has_docstring: bool | None,
    as_json: bool,
    pattern: str | None,
) -> None:
    r"""Structural code search across the working tree.

    Search by AST structure, not text. Find functions by kind, parameter count,
    return type, decorators, and more.

    \b
    Examples:
      sgit search --kind function
      sgit search --kind method --async --params 3
      sgit search --return-type dict --parent Calculator
      sgit search --decorator staticmethod
      sgit search "compute"
    """
    from sgit.core.search import SearchPattern, search_snapshots

    try:
        repo = Repository()
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # Build snapshots of working tree
    tracked = repo.list_tracked_files()
    if not tracked:
        # Fallback: scan all supported files
        tracked = []
        for p in repo.root.rglob("*"):
            if p.is_file() and is_supported(str(p)):
                tracked.append(str(p.relative_to(repo.root)))

    snapshots: dict[str, FileSnapshot] = {}
    for rel_path in tracked:
        full_path = repo.root / rel_path
        if full_path.exists() and is_supported(str(full_path)):
            snapshots[rel_path] = parse_any_file(str(full_path))

    # Handle --async flag: Click passes False when not set, None when default
    async_filter = True if is_async else None

    query = SearchPattern(
        kind=kind,
        name=name_pattern,
        signature=sig_pattern,
        is_async=async_filter,
        exact_params=params,
        min_params=min_params,
        max_params=max_params,
        has_decorator=has_decorator,
        return_type=return_type,
        parent=parent,
        has_docstring=has_docstring,
        pattern=pattern,
    )

    results = search_snapshots(snapshots, query)

    if as_json:
        import json

        click.echo(json.dumps(results.to_dict(), indent=2))
        return

    if not results.matches:
        click.echo("No matches found.")
        n = results.total_nodes_searched
        f = results.total_files_searched
        click.echo(f"Searched {n} nodes in {f} files.")
        return

    click.echo(f"Found {len(results.matches)} match(es):")
    click.echo()
    for match in results.matches:
        click.echo(f"  {match.file_path}:{match.node.line_start}")
        sig = match.node.signature
        click.echo(f"    {match.node.kind} {match.qualified_name}{sig}")
        if match.node.decorators:
            decos = ", ".join(match.node.decorators)
            click.echo(f"    decorators: {decos}")
        if match.node.docstring:
            doc_preview = match.node.docstring.split("\n")[0][:80]
            click.echo(f"    doc: {doc_preview}")
        click.echo()

    n = results.total_nodes_searched
    f = results.total_files_searched
    click.echo(f"Searched {n} nodes in {f} files.")


def _find_common_ancestor(
    repo: Repository,
    commit_a: str,
    commit_b: str,
) -> str | None:
    """Find common ancestor commit (simple linear walk)."""
    ancestors_a: set[str] = set()
    current = commit_a
    while current:
        ancestors_a.add(current)
        c = repo.get_commit(current)
        current = c.parent_id if c else None

    current = commit_b
    while current:
        if current in ancestors_a:
            return current
        c = repo.get_commit(current)
        current = c.parent_id if c else None

    return None


def _compute_deltas_vs_head(
    repo: Repository,
    current_snapshots: dict[str, FileSnapshot],
) -> list[SemanticDelta]:
    """Compute semantic deltas between HEAD and current snapshots."""
    head_id = repo.head_commit_id()
    if head_id is None:
        deltas: list[SemanticDelta] = []
        for path, snap in current_snapshots.items():
            delta = compute_delta(FileSnapshot(path=path), snap)
            deltas.append(delta)
        return deltas

    head_commit = repo.get_commit(head_id)
    if head_commit is None:
        return []

    old_snaps = repo.get_commit_snapshots(head_commit)
    return _compute_deltas_between(old_snaps, current_snapshots)


def _compute_deltas_between(
    old_snaps: dict[str, FileSnapshot],
    new_snaps: dict[str, FileSnapshot],
) -> list[SemanticDelta]:
    """Compute deltas between two sets of snapshots."""
    deltas: list[SemanticDelta] = []
    all_files = set(old_snaps) | set(new_snaps)

    for fpath in sorted(all_files):
        old = old_snaps.get(fpath, FileSnapshot(path=fpath))
        new = new_snaps.get(fpath, FileSnapshot(path=fpath))
        deltas.append(compute_delta(old, new))

    return deltas
