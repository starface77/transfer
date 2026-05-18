"""LLM-powered standup report generation (Ollama local / OpenAI fallback)."""

from __future__ import annotations

import os
from typing import Optional

SYSTEM_PROMPT = (
    "You are an elite, highly professional software developer. "
    "Your task is to take a raw list of AST-level code changes and summarize them "
    "into a clean, concise Daily Standup update for Slack. "
    "GUIDELINES:\n"
    "1. Write in Russian. The tone should be slightly casual, like a developer writing a daily update in a team Slack channel.\n"
    "2. Use professional tech-slang naturally (e.g., 'отрефакторил', 'накатил', 'пофиксил').\n"
    "3. Format as a clean, bulleted list. Keep it very short and punchy.\n"
    "4. Focus on the BUSINESS/FUNCTIONAL value of the change, not just syntax details.\n"
    "5. Skip boilerplate greetings. Output ONLY the resulting bullet points, no extra text."
)


def _build_user_prompt(change_descriptions: list[str]) -> str:
    items = "\n".join(f"- {desc}" for desc in change_descriptions)
    return f"Here are the raw AST changes I made today:\n{items}"


def generate_report_ollama(
    change_descriptions: list[str],
    model: str = "llama3",
    base_url: str = "http://localhost:11434",
    timeout: int = 60,
) -> str:
    """Generate standup report using a local Ollama instance.

    Args:
        change_descriptions: List of human-readable AST change strings.
        model: Ollama model name.
        base_url: Ollama API base URL.
        timeout: Request timeout in seconds.

    Returns:
        Generated standup report text.
    """
    import requests

    url = f"{base_url}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(change_descriptions)},
        ],
        "stream": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.ConnectionError:
        raise ConnectionError(
            "Ollama is not running locally. "
            "Start it with `ollama run llama3` or use `--engine openai`."
        )
    except requests.Timeout:
        raise TimeoutError(
            f"Ollama request timed out after {timeout}s. "
            "Try a smaller model or increase --timeout."
        )
    except (KeyError, ValueError) as exc:
        raise RuntimeError(f"Unexpected Ollama response: {exc}")


def generate_report_openai(
    change_descriptions: list[str],
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """Generate standup report using OpenAI API.

    Args:
        change_descriptions: List of human-readable AST change strings.
        model: OpenAI model name.
        api_key: OpenAI API key (falls back to OPENAI_API_KEY env var).
        timeout: Request timeout in seconds.

    Returns:
        Generated standup report text.
    """
    import requests

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not set. "
            "Export it or pass --api-key."
        )

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(change_descriptions)},
        ],
        "temperature": 0.7,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.ConnectionError:
        raise ConnectionError(
            "Cannot reach OpenAI API. Check your internet connection."
        )
    except requests.Timeout:
        raise TimeoutError(f"OpenAI request timed out after {timeout}s.")
    except (KeyError, ValueError, IndexError) as exc:
        raise RuntimeError(f"Unexpected OpenAI response: {exc}")


def generate_report_gemini(
    change_descriptions: list[str],
    model: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """Generate standup report using Google Gemini API.

    Args:
        change_descriptions: List of human-readable AST change strings.
        model: Gemini model name.
        api_key: Gemini API key (falls back to GEMINI_API_KEY env var).
        timeout: Request timeout in seconds.

    Returns:
        Generated standup report text.
    """
    import requests

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Export it or pass --api-key."
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": _build_user_prompt(change_descriptions)}]}],
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except requests.ConnectionError:
        raise ConnectionError("Cannot reach Gemini API. Check your internet connection.")
    except requests.Timeout:
        raise TimeoutError(f"Gemini request timed out after {timeout}s.")
    except (KeyError, ValueError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {exc}")


def generate_report(
    change_descriptions: list[str],
    engine: str = "ollama",
    **kwargs,
) -> str:
    """Generate standup report using the specified engine.

    Args:
        change_descriptions: List of human-readable AST change strings.
        engine: "ollama" or "openai".
        **kwargs: Passed to the engine-specific function.

    Returns:
        Generated standup report text.
    """
    if not change_descriptions:
        return "No recent commits found. Did you run `sgit commit` today?"

    if engine == "ollama":
        return generate_report_ollama(change_descriptions, **kwargs)
    elif engine == "openai":
        return generate_report_openai(change_descriptions, **kwargs)
    elif engine == "gemini":
        return generate_report_gemini(change_descriptions, **kwargs)
    else:
        raise ValueError(f"Unknown engine: {engine}. Use 'ollama', 'openai', or 'gemini'.")


def generate_report_offline(change_descriptions: list[str]) -> str:
    """Generate a simple standup report without any LLM (offline fallback).

    This creates a clean bulleted list from raw AST change descriptions.
    Useful when no LLM is available.
    """
    if not change_descriptions:
        return "No recent commits found. Did you run `sgit commit` today?"

    lines = ["**Daily Standup Report**", ""]
    for desc in change_descriptions:
        lines.append(f"- {desc}")
    lines.append("")
    lines.append(f"_({len(change_descriptions)} changes total)_")
    return "\n".join(lines)
