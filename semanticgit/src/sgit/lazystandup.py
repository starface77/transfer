"""lazystandup: automated, privacy-first developer standup generator."""

from __future__ import annotations

import datetime
import os
import sys
import time
import requests
import pyperclip

from sgit.core.storage import Repository
from sgit.core.diff_engine import compute_delta, format_delta
from sgit.models import FileSnapshot, SemanticDelta


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


def get_ast_changes_for_last_n_hours(hours: int = 8) -> list[str]:
    """
    Scans the local s-git commit history and gathers all AST change descriptions
    committed in the last N hours.
    """
    try:
        repo = Repository()
    except FileNotFoundError:
        return []

    commits = repo.log(max_count=100)
    now = datetime.datetime.now(datetime.timezone.utc)
    
    changes: list[str] = []
    for commit in commits:
        try:
            # Timestamp format: "2026-05-17T18:14:34Z"
            ts_str = commit.timestamp.rstrip('Z')
            commit_time = datetime.datetime.fromisoformat(ts_str).replace(tzinfo=datetime.timezone.utc)
        except Exception:
            continue
            
        time_diff = now - commit_time
        if time_diff.total_seconds() <= (hours * 3600):
            # Compute AST deltas for this commit
            commit_snaps = repo.get_commit_snapshots(commit)
            parent = repo.get_commit(commit.parent_id) if commit.parent_id else None
            parent_snaps = repo.get_commit_snapshots(parent) if parent else {}
            
            deltas = _compute_deltas_between(parent_snaps, commit_snaps)
            active_deltas = [d for d in deltas if d.has_changes]
            for delta in active_deltas:
                changes.append(format_delta(delta))
                
    return changes


def generate_standup_report(ast_changes: list[str], engine: str = "ollama") -> str:
    """
    Sends the gathered AST change descriptions to the LLM (Ollama or OpenAI)
    and returns a beautifully structured Russian standup log.
    """
    if not ast_changes:
        return "No recent commits found. Did you run `sgit commit` today?"

    system_prompt = (
        "You are an elite, highly professional software developer. "
        "Your task is to take a raw list of AST-level code changes and summarize them "
        "into a clean, concise, human-grade Daily Standup update for Slack. "
        "GUIDELINES:\n"
        "1. Write in Russian. Use casual but highly professional tech-slang (e.g. 'отрефакторил', 'оптимизировал', 'добавил метод').\n"
        "2. Format as a clean, bulleted list. Keep it short and readable.\n"
        "3. Focus on the BUSINESS/FUNCTIONAL value of the change, not just syntax details.\n"
        "4. DO NOT write robot-like text or mention AST/compiler concepts unless necessary.\n"
        "5. Output ONLY the resulting bullet points, nothing else."
    )
    
    user_prompt = "Here are the raw AST changes I made today:\n" + "\n".join(ast_changes)

    if engine == "ollama":
        try:
            url = "http://localhost:11434/api/chat"
            payload = {
                "model": "llama3",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
            response = requests.post(url, json=payload, timeout=20)
            return response.json()['message']['content']
        except Exception:
            return "Ollama is not running locally. Please start it with `ollama run llama3` or switch to `--engine openai`."
            
    elif engine == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Error: OPENAI_API_KEY environment variable is not set."
            
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"

    return "Unknown engine selected."
