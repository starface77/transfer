"""Gemini REST client for Sharrowkin."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import requests

# Manually load .env variables if present
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


@dataclass(slots=True)
class GeneratedPatch:
    rationale: str
    subtasks: list[str]
    files: dict[str, str]
    commands: list[str]


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        
        # Omniroute proxy support (Anthropic-compatible endpoint)
        self.omniroute_base_url = os.getenv("ANTHROPIC_BASE_URL")
        self.omniroute_token = (
            os.getenv("ANTHROPIC_AUTH_TOKEN")
            or os.getenv("ANTHROPIC_API_KEY")
            or ""
        )
        self.omniroute_model = os.getenv("ANTHROPIC_MODEL") or "kr/claude-sonnet-4.5"

    @property
    def configured(self) -> bool:
        return bool(self.api_key) or bool(self.omniroute_base_url)

    def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        if not self.api_key and not self.omniroute_base_url:
            raise GeminiConfigurationError(
                "Neither GEMINI_API_KEY nor ANTHROPIC_BASE_URL is set."
            )
            
        if self.omniroute_base_url:
            base_url = self.omniroute_base_url.rstrip("/")
            url = f"{base_url}/messages"
            headers = {
                "x-api-key": self.omniroute_token,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            system = system_instruction or "You are Sharrowkin, a local autonomous developer agent."
            payload = {
                "model": self.omniroute_model,
                "max_tokens": 2048,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "stream": False,
            }
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 404:
                    # Try OpenAI fallback
                    openai_url = f"{base_url}/chat/completions"
                    openai_headers = {
                        "Authorization": f"Bearer {self.omniroute_token}",
                        "Content-Type": "application/json",
                    }
                    openai_payload = {
                        "model": self.omniroute_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "stream": False,
                    }
                    openai_response = requests.post(openai_url, headers=openai_headers, json=openai_payload, timeout=30)
                    openai_response.raise_for_status()
                    data = openai_response.json()
                    return data["choices"][0]["message"]["content"]
                
                response.raise_for_status()
                data = response.json()
                if "content" in data and len(data["content"]) > 0:
                    return data["content"][0]["text"]
                elif "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                elif "candidates" in data and len(data["candidates"]) > 0:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                return ""
            except Exception as e:
                raise RuntimeError(f"Omniroute call failed: {e}")
        else:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent?key={self.api_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            }
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
            try:
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                raise RuntimeError(f"Gemini call failed: {e}")

    def classify_intent(self, task: str) -> dict[str, object]:
        import re
        
        # Fast heuristic: catch obvious greetings/conversational queries without LLM
        normalized = task.strip().lower()
        # Remove punctuation for matching
        clean = re.sub(r'[^\w\s]', '', normalized)
        
        greeting_patterns = {
            "привет", "здравствуй", "здравствуйте", "хай", "хей", "салам",
            "hello", "hi", "hey", "yo", "sup",
            "как дела", "как ты", "что нового", "как поживаешь",
            "кто ты", "что ты", "что ты умеешь", "что ты можешь",
            "who are you", "what are you", "how are you",
            "thanks", "thank you", "спасибо", "пока", "bye",
            "доброе утро", "добрый день", "добрый вечер", "good morning",
            "ку", "qq", "q", "прив", "даров", "здорова",
        }
        
        # Check if the entire message (cleaned) matches a greeting pattern
        if clean in greeting_patterns:
            print(f"[INTENT] Heuristic match: '{task}' -> conversational")
            return {"is_conversational": True, "response": None}
        
        # Check if the message starts with a greeting and is short (< 8 words)
        words = clean.split()
        if len(words) <= 6 and any(clean.startswith(g) for g in greeting_patterns):
            print(f"[INTENT] Heuristic prefix match: '{task}' -> conversational")
            return {"is_conversational": True, "response": None}
        
        # For ambiguous queries, use LLM classification
        system_instruction = (
            "You are Sharrowkin, an agentic AI coding assistant. Classify the user query.\n"
            "Return a JSON object with two keys:\n"
            " - 'is_conversational': true if this is a greeting, small talk, or general question NOT about code/files.\n"
            " - 'response': if is_conversational is true, write a helpful response. Otherwise null.\n"
            "Return ONLY the raw JSON object, no markdown."
        )
        
        prompt = f"User query: {task}"
        
        try:
            raw_response = self.generate_text(prompt, system_instruction)
            text = raw_response.strip()
            print(f"[INTENT] LLM raw response: {text[:200]}")
            
            # Clean markdown if returned
            code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if code_block_match:
                text = code_block_match.group(1).strip()
            
            # Parse outer braces
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                text = text[start_idx:end_idx+1].strip()
                
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "is_conversational" in parsed:
                print(f"[INTENT] LLM classified: is_conversational={parsed['is_conversational']}")
                return parsed
        except Exception as exc:
            print(f"[INTENT] LLM classification failed: {exc}")
            
        return {"is_conversational": False, "response": None}

    def generate_patch(
        self,
        *,
        task: str,
        workspace_summary: str,
        memory_context: str,
        previous_error: str = "",
    ) -> GeneratedPatch:
        if not self.api_key and not self.omniroute_base_url:
            raise GeminiConfigurationError(
                "Neither GEMINI_API_KEY nor ANTHROPIC_BASE_URL is set. "
                "Add one of them to the environment to enable code generation."
            )

        prompt = self._build_prompt(task, workspace_summary, memory_context, previous_error)
        
        # If Omniroute proxy is configured, route via Anthropic Messages API
        if self.omniroute_base_url:
            base_url = self.omniroute_base_url.rstrip("/")
            url = f"{base_url}/messages"
            headers = {
                "x-api-key": self.omniroute_token,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            system_prompt = (
                "You are Sharrowkin, a local autonomous developer agent. "
                "Return only strict JSON with keys: rationale, subtasks, commands, and files. "
                " - 'rationale': short explanation of your reasoning.\n"
                " - 'subtasks': list of decomposed subtasks for complex goals (Task Decomposition).\n"
                " - 'commands': list of terminal commands to execute (e.g. npm install, pip install, git commit) (Tool Router).\n"
                " - 'files': object mapping relative file paths to complete replacement contents (Multi-file Reasoning).\n"
                "Do not wrap JSON in markdown. Do not include secrets."
            )
            payload = {
                "model": self.omniroute_model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "stream": False,  # Explicitly request non-streaming response
            }
            
            import time
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=90)
                    
                    # Check for 402 Specifically
                    if response.status_code == 402:
                        raise GeminiConfigurationError(
                            "Omniroute proxy returned 402 (Payment Required). "
                            "Please check your API key, billing status, or funds/credits on your Omniroute console. "
                            f"Response details: {response.text[:200]}"
                        )
                    
                    response.raise_for_status()
                    
                    body_text = response.text or ""
                    
                    # High-res Server-Sent Events (SSE) Auto-Detect Stream Parser
                    if "event: " in body_text or "data: " in body_text:
                        chunks = []
                        for line in body_text.splitlines():
                            line = line.strip()
                            if line.startswith("data:"):
                                data_str = line[5:].strip()
                                if data_str == "[DONE]":
                                    continue
                                try:
                                    chunk_data = json.loads(data_str)
                                    if isinstance(chunk_data, dict):
                                        # Anthropic Stream Schema:
                                        if "delta" in chunk_data and isinstance(chunk_data["delta"], dict) and "text" in chunk_data["delta"]:
                                            chunks.append(chunk_data["delta"]["text"])
                                        # OpenAI Stream Schema:
                                        elif "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                            choice = chunk_data["choices"][0]
                                            if "delta" in choice and isinstance(choice["delta"], dict) and "content" in choice["delta"]:
                                                chunks.append(choice["delta"]["content"])
                                except Exception:
                                    pass
                        if chunks:
                            text = "".join(chunks)
                            return parse_generated_patch(text)
                    
                    # Normal JSON Parsing
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        raise GeminiConfigurationError(
                            f"Failed to parse JSON response from Omniroute proxy (status code: {response.status_code}). "
                            f"The response body was not valid JSON. Response body starts with: {response.text[:400]!r}"
                        )
                    
                    # Check if proxy returned an error payload inside a 200 OK
                    if isinstance(data, dict) and "error" in data:
                        err = data["error"]
                        err_msg = err.get("message") if isinstance(err, dict) else str(err)
                        raise GeminiConfigurationError(f"Omniroute proxy returned an error: {err_msg}")
                    
                    # Robust multi-schema parsing
                    if isinstance(data, dict) and "content" in data and len(data["content"]) > 0:
                        text = data["content"][0]["text"]
                    elif isinstance(data, dict) and "choices" in data and len(data["choices"]) > 0:
                        text = data["choices"][0]["message"]["content"]
                    elif isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        raise GeminiConfigurationError(
                            f"Omniroute proxy returned an unrecognized JSON structure: {json.dumps(data)[:500]}"
                        )
                        
                    return parse_generated_patch(text)
                    
                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code == 402:
                        raise GeminiConfigurationError(
                            "Omniroute proxy returned 402 (Payment Required). "
                            "Please check your API key, billing status, or funds/credits on your Omniroute console. "
                            f"Response details: {e.response.text[:200]}"
                        )
                    if response.status_code >= 500 and attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    # Fallback check if the proxy returned 404 on /messages (e.g. OpenAI compatibility)
                    if response.status_code == 404 and attempt == 0:
                        # Try OpenAI-compatible chat completion endpoint as fallback
                        openai_url = f"{base_url}/chat/completions"
                        openai_headers = {
                            "Authorization": f"Bearer {self.omniroute_token}",
                            "Content-Type": "application/json",
                        }
                        openai_payload = {
                            "model": self.omniroute_model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.2,
                            "stream": False,  # Explicitly request non-streaming response
                        }
                        try:
                            openai_response = requests.post(openai_url, headers=openai_headers, json=openai_payload, timeout=90)
                            if openai_response.status_code == 402:
                                raise GeminiConfigurationError(
                                    "Omniroute proxy returned 402 (Payment Required) on fallback. "
                                    "Please check your API key, billing status, or funds/credits on your Omniroute console. "
                                    f"Response details: {openai_response.text[:200]}"
                                )
                            openai_response.raise_for_status()
                            
                            openai_body = openai_response.text or ""
                            
                            # Fallback SSE Parsing
                            if "event: " in openai_body or "data: " in openai_body:
                                chunks = []
                                for line in openai_body.splitlines():
                                    line = line.strip()
                                    if line.startswith("data:"):
                                        data_str = line[5:].strip()
                                        if data_str == "[DONE]":
                                            continue
                                        try:
                                            chunk_data = json.loads(data_str)
                                            if isinstance(chunk_data, dict):
                                                if "delta" in chunk_data and isinstance(chunk_data["delta"], dict) and "text" in chunk_data["delta"]:
                                                    chunks.append(chunk_data["delta"]["text"])
                                                elif "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                                    choice = chunk_data["choices"][0]
                                                    if "delta" in choice and isinstance(choice["delta"], dict) and "content" in choice["delta"]:
                                                        chunks.append(choice["delta"]["content"])
                                        except Exception:
                                            pass
                                if chunks:
                                    text = "".join(chunks)
                                    return parse_generated_patch(text)
                                    
                            try:
                                openai_data = openai_response.json()
                            except json.JSONDecodeError:
                                raise GeminiConfigurationError(
                                    f"Failed to parse JSON response from OpenAI fallback endpoint (status code: {openai_response.status_code}). "
                                    f"Response body starts with: {openai_response.text[:400]!r}"
                                )
                            
                            if isinstance(openai_data, dict) and "error" in openai_data:
                                err = openai_data["error"]
                                err_msg = err.get("message") if isinstance(err, dict) else str(err)
                                raise GeminiConfigurationError(f"OpenAI fallback returned an error: {err_msg}")
                            
                            if isinstance(openai_data, dict) and "choices" in openai_data and len(openai_data["choices"]) > 0:
                                text = openai_data["choices"][0]["message"]["content"]
                            elif isinstance(openai_data, dict) and "content" in openai_data and len(openai_data["content"]) > 0:
                                text = openai_data["content"][0]["text"]
                            else:
                                raise GeminiConfigurationError(
                                    f"OpenAI fallback returned an unrecognized JSON structure: {json.dumps(openai_data)[:500]}"
                                )
                                
                            return parse_generated_patch(text)
                        except GeminiConfigurationError:
                            raise
                        except Exception:
                            pass
                    raise
        else:
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
                                "Return only strict JSON with keys: rationale, subtasks, commands, and files. "
                                " - 'rationale': short explanation of your reasoning.\n"
                                " - 'subtasks': list of decomposed subtasks for complex goals (Task Decomposition).\n"
                                " - 'commands': list of terminal commands to execute (e.g. npm install, pip install, git commit) (Tool Router).\n"
                                " - 'files': object mapping relative file paths to complete replacement contents (Multi-file Reasoning).\n"
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
            "Generate the smallest safe patch. Return complete replacement text only for files you change. "
            "You can specify shell commands in 'commands' if you need to install packages, run scripts, or compile things."
        )
        return "\n\n".join(sections)


def parse_generated_patch(raw: str) -> GeneratedPatch:
    text = raw.strip()
    
    # 1. Try to extract from markdown code blocks
    import re
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        text = code_block_match.group(1).strip()
        
    # 2. Try parsing, and fall back to scanning outer braces if it fails
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = text[start_idx:end_idx+1].strip()
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Failed to parse JSON even after bracket extraction. "
                    f"Content: {candidate[:300]!r}. Error: {exc}"
                )
        else:
            raise ValueError(
                f"Could not locate a valid JSON block in LLM response. "
                f"Content: {raw[:300]!r}"
            )
            
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must parse to a JSON object.")
    rationale_raw = parsed.get("rationale", "")
    subtasks_raw = parsed.get("subtasks", [])
    files_raw = parsed.get("files", {})
    commands_raw = parsed.get("commands", [])

    if not isinstance(rationale_raw, str) or not isinstance(files_raw, dict):
        raise ValueError("Gemini response must contain string rationale and object files.")
    
    files: dict[str, str] = {}
    for path, content in files_raw.items():
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError("Each files entry must map a path string to content string.")
        files[path] = content

    subtasks = [t for t in subtasks_raw if isinstance(t, str)]
    commands = [c for c in commands_raw if isinstance(c, str)]

    return GeneratedPatch(
        rationale=rationale_raw,
        subtasks=subtasks,
        files=files,
        commands=commands
    )

