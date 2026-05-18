"""CLI entry point for lazystandup."""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.theme import Theme

# Curated premium theme for a high-end DeepTech co-pilot vibe
custom_theme = Theme({
    "info": "cyan bold",
    "warning": "yellow bold",
    "error": "red bold",
    "success": "green bold",
    "accent": "magenta bold",
    "muted": "grey50",
})
console = Console(theme=custom_theme)


@click.command()
@click.option(
    "--hours",
    default=8,
    show_default=True,
    help="How many hours of history to scan.",
)
@click.option(
    "--engine",
    default="ollama",
    type=click.Choice(["ollama", "openai", "gemini", "offline"]),
    help="LLM backend for report generation.",
)
@click.option("--model", default=None, help="Override the default model name.")
@click.option("--api-key", default=None, help="API key for OpenAI/Gemini (or set ENV vars).")
@click.option("--no-clipboard", is_flag=True, help="Skip clipboard copy.")
@click.option("--json", "as_json", is_flag=True, help="Output raw changes as JSON.")
@click.option(
    "--repo",
    default=None,
    help="Path to s-git repository (auto-detected if omitted).",
)
def main(
    hours: float,
    engine: str,
    model: str | None,
    api_key: str | None,
    no_clipboard: bool,
    as_json: bool,
    repo: str | None,
) -> None:
    """Generate your daily standup report from s-git AST commits.

    Scans s-git commit history, extracts semantic AST changes,
    compiles them into a professional standup report via LLM,
    and copies the result to your clipboard.
    """
    from lazystandup.harvester import harvest_changes

    console.print()
    # Premium Header Card
    console.print(
        Panel(
            "[accent]🛋️  LAZYSTANDUP[/accent] [muted]v0.1.0[/muted] • [info]Zero-Telemetry Smart Standup Engine[/info]",
            border_style="magenta",
            padding=(0, 1),
        )
    )

    with console.status(
        f"[accent]🔍 Gathers AST-level history for the last [info]{hours}[/info] hours...[/accent]",
        spinner="dots",
    ):
        result = harvest_changes(repo_path=repo, hours=hours)

    if not result.changes:
        console.print()
        console.print(
            Panel(
                "[warning]No semantic modifications found in this timeframe. Make some commits first![/warning]",
                title="⚠️ Empty Harvest",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        return

    console.print(
        f"[success]✔[/success] Harvested [info]{len(result.changes)} AST nodes[/info] "
        f"across [info]{result.commits_scanned} commits[/info]."
    )

    if as_json:
        import json

        out = [
            {
                "commit_id": ch.commit_id,
                "timestamp": ch.timestamp,
                "message": ch.message,
                "file": ch.file_path,
                "change_type": ch.change_type,
                "kind": ch.node_kind,
                "name": ch.node_name,
                "signature": ch.signature,
                "description": ch.describe(),
            }
            for ch in result.changes
        ]
        console.print_json(data=out)
        return

    descriptions = result.descriptions

    # Spinner for LLM generation
    with console.status(
        f"[accent]🧠 Translating code signatures to human Standup via [info]{engine}[/info]...[/accent]",
        spinner="shark",
    ):
        from lazystandup.reporter import generate_report, generate_report_offline

        try:
            if engine == "offline":
                report = generate_report_offline(descriptions)
            else:
                kwargs: dict = {}
                if model:
                    kwargs["model"] = model
                if api_key:
                    kwargs["api_key"] = api_key
                report = generate_report(descriptions, engine=engine, **kwargs)
        except (ConnectionError, TimeoutError, ValueError, RuntimeError) as exc:
            console.print(f"\n[error]LLM Error: {exc}[/error]", err=True)
            console.print("[muted]Falling back to structured offline parser...[/muted]")
            report = generate_report_offline(descriptions)

    # Render report inside a beautiful markdown-friendly panel
    console.print()
    console.print(
        Panel(
            Markdown(report),
            title="✨ YOUR DAILY STANDUP REPORT",
            title_align="left",
            border_style="green",
            subtitle=f"Source: {engine.upper()} • {len(result.changes)} structural deltas parsed",
            subtitle_align="right",
            padding=(1, 2),
        )
    )
    console.print()

    # Clipboard copy with status feedback
    if not no_clipboard:
        try:
            import pyperclip

            pyperclip.copy(report)
            console.print(
                "[success]📋 Copy successful![/success] Report saved directly to clipboard. [muted]Just Ctrl+V in Slack.[/muted]"
            )
        except Exception:
            console.print(
                "[warning]⚠️ Clipboard access failed.[/warning] [muted]Please copy the panel text manually.[/muted]",
                err=True,
            )
    console.print()


if __name__ == "__main__":
    main()
