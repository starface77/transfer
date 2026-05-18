"""Gemini REST client for Sharrowkin."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import requests


@dataclass(slots=True)
class GeneratedPatch:
    rationale: str
    files: dict[str, str]


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate_patch(
        self,
        *,
        task: str,
        workspace_summary: str,
        memory_context: str,
        previous_error: str = "",
    ) -> GeneratedPatch:
        if not self.api_key:
            raise GeminiConfigurationError(
                "GEMINI_API_KEY is not set. Add it to the environment to enable code generation."
            )

        prompt = self._build_prompt(task, workspace_summary, memory_context, previous_error)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            "You are Sharrowkin, a local autonomous developer agent. "
                            "Return only strict JSON with keys rationale and files. "
                            "The files object maps relative file paths to complete replacement contents. "
                            "Do not wrap JSON in markdown. Do not include secrets."
                        )
                    }
                ]
            },
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=90)
                response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return parse_generated_patch(text)
            except requests.exceptions.HTTPError as e:
                if response.status_code >= 500 and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise

    def _build_prompt(
        self,
        task: str,
        workspace_summary: str,
        memory_context: str,
        previous_error: str,
    ) -> str:
        sections = [
            "TASK",
            task,
            "WORKSPACE AST SUMMARY",
            workspace_summary,
            "RLD AND DSM MEMORY CONTEXT",
            memory_context,
        ]
        if previous_error:
            sections.extend(["PREVIOUS PYTEST OUTPUT OR PATCH ERROR", previous_error])
        sections.append(
            "Generate the smallest safe patch. Return complete replacement text only for files you change."
        )
        return "\n\n".join(sections)


def parse_generated_patch(raw: str) -> GeneratedPatch:
    text = raw.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response must be a JSON object.")
    rationale_raw = parsed.get("rationale", "")
    files_raw = parsed.get("files", {})
    if not isinstance(rationale_raw, str) or not isinstance(files_raw, dict):
        raise ValueError("Gemini response must contain string rationale and object files.")
    files: dict[str, str] = {}
    for path, content in files_raw.items():
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError("Each files entry must map a path string to content string.")
        files[path] = content
    return GeneratedPatch(rationale=rationale_raw, files=files)
