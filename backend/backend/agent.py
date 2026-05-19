"""Real Sharrowkin cognitive agent loop with live thinking stream."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from llm import GeminiClient, GeminiConfigurationError
from memory import MemoryBridge
from tools import (
    ProposedFileChange,
    apply_changes,
    git_diff,
    resolve_workspace,
    run_pytest,
    scan_workspace,
    summarize_workspace,
    search_web,
    fetch_url,
    run_terminal_command,
)

PHASES = ["Observe", "Recall", "Reason", "Stabilize", "Commit"]


@dataclass(slots=True)
class AgentRunState:
    task: str
    workspace: Path
    states: list[str]
    actions: list[str]
    tools_used: list[str]
    workspace_summary: str = ""
    memory_context: str = ""
    last_error: str = ""
    final_diff: str = ""
    changes_made: bool = False
    last_rationale: str = ""


class SharrowkinAgent:
    def __init__(self, gemini_client: GeminiClient | None = None, max_iterations: int = 50) -> None:
        self.gemini = gemini_client or GeminiClient()
        self.max_iterations = max_iterations

    # --- helper emitters ---------------------------------------------------
    def _phase(self, name: str, status: str) -> dict[str, object]:
        return {"type": "phase_change", "phase": name.lower(), "status": status}

    def _log(self, level: str, message: str) -> dict[str, object]:
        return {"type": "log", "level": level, "message": message}

    def _status(self, status: str) -> dict[str, object]:
        return {"type": "status", "status": status}

    def _thinking(self, text: str) -> dict[str, object]:
        """Emit a 'thinking' event so the frontend shows live agent reasoning."""
        return {"type": "thinking", "content": text}

    # --- main run loop ------------------------------------------------------
    async def run(self, task: str, workspace_path: str) -> AsyncIterator[dict[str, object]]:
        print(f"[AGENT] run() called: task={task!r}, workspace_path={workspace_path!r}")
        workspace = resolve_workspace(workspace_path)
        state = AgentRunState(
            task=task,
            workspace=workspace,
            states=[],
            actions=[],
            tools_used=[],
        )
        memory = MemoryBridge(workspace)
        yield self._status("running")
        yield self._thinking("Получил задачу. Анализирую запрос...")

        # --- Intent Routing ---
        yield self._thinking("Определяю тип запроса: код или разговор...")
        try:
            intent = await asyncio.to_thread(self.gemini.classify_intent, task)
            print(f"[AGENT] Intent result: {intent}")
            if intent.get("is_conversational"):
                yield self._thinking("Это обычное сообщение — отвечаю напрямую через LLM...")
                response = intent.get("response")
                if not response:
                    if not self.gemini.configured:
                        response = "Привет! Я Sharrowkin — автономный агент-разработчик. Чем могу помочь?"
                    else:
                        try:
                            response = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.gemini.generate_text,
                                    task,
                                    "You are Sharrowkin, a friendly AI coding assistant. "
                                    "Respond naturally and helpfully to the user's message. "
                                    "Keep it concise and friendly. Answer in the same language the user writes in."
                                ),
                                timeout=15,
                            )
                        except Exception as exc:
                            print(f"[AGENT] LLM response generation failed: {exc}")
                            response = "Привет! Я Sharrowkin — автономный агент-разработчик. Чем могу помочь?"
                yield self._thinking("Ответ сгенерирован!")
                yield {"type": "content", "content": response}
                yield self._status("done")
                return
        except Exception as exc:
            print(f"[AGENT] Intent classification error: {exc}")

        # --- Informational / Read-Only Flow ---
        if intent.get("is_informational"):
            yield self._thinking("Это информационный запрос. Запускаю облегчённый цикл анализа...")
            yield self._log("system", "Sharrowkin informational analysis cycle started.")
            
            try:
                # 1. Observe Phase (AST Scan)
                async for event in self._observe(state, memory):
                    yield event
                
                # 2. Recall Phase (Memory Retrieval)
                async for event in self._recall(state, memory):
                    yield event
                
                # 3. Reason Phase (Rich response generation)
                yield self._phase("Reason", "active")
                yield self._thinking("Анализирую информацию и формирую подробный ответ...")
                yield self._log("info", "Generating comprehensive response for read-only query.")
                
                try:
                    import os
                    # Read README.md if it exists in the workspace
                    readme_content = ""
                    readme_path = os.path.join(state.workspace, "README.md")
                    if os.path.exists(readme_path):
                        try:
                            with open(readme_path, "r", encoding="utf-8") as rf:
                                readme_content = rf.read(12000)
                        except Exception:
                            pass
                    
                    # Clip AST summary to avoid proxy timeout
                    ws_summary_clipped = state.workspace_summary or ""
                    if len(ws_summary_clipped) > 8000:
                        ws_summary_clipped = ws_summary_clipped[:8000] + "\n... [truncated for brevity] ..."

                    rich_prompt = (
                        f"User request: {state.task}\n\n"
                        f"Workspace README.md:\n{readme_content}\n\n"
                        f"Workspace AST summary (clipped):\n{ws_summary_clipped}\n\n"
                        f"Associative Memory Context (from DSM/RLD):\n{state.memory_context}\n\n"
                        "Please answer the user's request thoroughly and naturally. "
                        "Since the query is informational/read-only, write a comprehensive, high-quality response. "
                        "Do not include any file-change instructions or patch content in the response. "
                        "Write the response in the same language the user asked in (which is usually Russian)."
                    )
                    
                    rich_response = await asyncio.to_thread(
                        self.gemini.generate_text,
                        rich_prompt,
                        "You are Sharrowkin, an expert AI developer agent. "
                        "Provide a professional, friendly, and very detailed response to the user's query about the project or code. "
                        "Structure your reply with clean markdown headers and bullet points. "
                        "Answer in the same language as the user query."
                    )
                    state.last_rationale = rich_response
                except Exception as exc:
                    print(f"[AGENT] Rich response generation failed: {exc}")
                    state.last_rationale = f"Не удалось сгенерировать ответ: {exc}"
                
                yield self._phase("Reason", "done")
                
                if state.last_rationale:
                    yield {"type": "content", "content": state.last_rationale}
                yield self._status("done")
                yield self._log("success", "Informational analysis completed.")
                return
            except Exception as e:
                print(f"[AGENT] Informational loop error: {e}")
                yield self._status("error", message=str(e))
                return

        # --- Full coding agent cycle ---
        yield self._thinking("Это задача по коду. Запускаю полный когнитивный цикл...")
        yield self._log("system", "Sharrowkin cognitive cycle started.")

        try:
            async for event in self._observe(state, memory):
                yield event
            async for event in self._recall(state, memory):
                yield event

            success = False
            for iteration in range(1, self.max_iterations + 1):
                async for event in self._reason(state, iteration):
                    yield event

                if not state.changes_made:
                    success = True
                    break

                async for event in self._stabilize(state, iteration):
                    yield event
                if not state.last_error:
                    success = True
                    break

            if success:
                async for event in self._commit(state, memory):
                    yield event
                if state.last_rationale:
                    yield {"type": "content", "content": state.last_rationale}
                yield self._status("done")
                yield self._log("success", "Task stabilized and stored in local memory.")
            else:
                if state.last_error:
                    yield {"type": "content", "content": f"⚠️ **Self-healing loop reached the iteration limit.**\n\nLast error:\n```log\n{state.last_error}\n```"}
                yield self._status("error")
                yield self._log("error", "Self-healing loop reached the iteration limit.")
        except GeminiConfigurationError as exc:
            yield self._phase("Reason", "error")
            yield self._thinking(f"Ошибка: не настроен API ключ. {exc}")
            yield {"type": "content", "content": f"⚠️ **API ключ не настроен.**\n\nДобавьте `GEMINI_API_KEY` в файл `backend/backend/.env` для работы с кодом.\n\n```\n{exc}\n```"}
            yield self._status("needs_key")
            yield self._log("error", str(exc))
        except Exception as exc:
            print(f"[AGENT] Cycle error: {exc}")
            yield self._thinking(f"Ошибка: {exc}")
            yield {"type": "content", "content": f"⚠️ **Ошибка агента:**\n\n```\n{exc}\n```"}
            yield self._status("error")
            yield self._log("error", f"Agent cycle failed: {exc}")

    # --- Phase: Observe -----------------------------------------------------
    async def _observe(
        self,
        state: AgentRunState,
        memory: MemoryBridge,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Observe", "active")
        yield self._thinking(f"Сканирую рабочее пространство: {state.workspace}")
        yield self._log("info", f"Scanning workspace: {state.workspace}")
        summaries = await asyncio.to_thread(scan_workspace, state.workspace)
        state.workspace_summary = summarize_workspace(summaries)
        state.states.append(state.workspace_summary)
        state.actions.append(f"Scanned {len(summaries)} source files with AST summaries")
        state.tools_used.append("pathlib")
        state.tools_used.append("ast")
        yield self._thinking(f"Найдено {len(summaries)} исходных файлов. Строю AST-карту проекта...")
        await asyncio.to_thread(memory.learn_project, state.workspace_summary)
        yield self._log("success", f"Observed {len(summaries)} source files.")
        yield self._phase("Observe", "done")

    # --- Phase: Recall ------------------------------------------------------
    async def _recall(
        self,
        state: AgentRunState,
        memory: MemoryBridge,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Recall", "active")
        yield self._thinking("Запрашиваю контекст из памяти (RLD + DSM)...")
        yield self._log("info", "Retrieving RLD and DSM context.")
        state.memory_context = await asyncio.to_thread(memory.recall, state.task)
        state.states.append(state.memory_context)
        state.actions.append("Loaded RLD active context and DSM active context")
        state.tools_used.append("rld")
        state.tools_used.append("dsm")
        yield self._thinking("Память загружена. Готов к генерации решения.")
        yield self._log("success", "Memory context is ready.")
        yield self._phase("Recall", "done")

    # --- Phase: Reason (patch generation) -----------------------------------
    async def _reason(
        self,
        state: AgentRunState,
        iteration: int,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Reason", "active")
        yield self._thinking(f"Генерирую решение через LLM (итерация {iteration})...")
        yield self._log("info", f"Generating patch with LLM, iteration {iteration}.")
        generated = await asyncio.to_thread(
            self.gemini.generate_patch,
            task=state.task,
            workspace_summary=state.workspace_summary,
            memory_context=state.memory_context,
            previous_error=state.last_error,
            action_history=state.actions,
        )
        state.last_rationale = generated.rationale

        # Task Decomposition
        if generated.subtasks:
            yield self._thinking("Разбиваю задачу на подзадачи:\n" + "\n".join(f"  → {t}" for t in generated.subtasks))
            yield self._log("info", "Plan decomposed into subtasks:\n" + "\n".join(f" - {t}" for t in generated.subtasks))
            state.actions.append(f"Decomposed task into {len(generated.subtasks)} subtasks")

        # Tool Router: Run Terminal Commands
        command_failed = False
        if generated.commands:
            for command in generated.commands:
                yield self._thinking(f"Выполняю команду: `{command}`")
                yield self._log("info", f"Running command: {command}")
                cmd_result = await asyncio.to_thread(run_terminal_command, state.workspace, command)
                state.actions.append(f"Executed: {command} (code {cmd_result.exit_code})")
                state.tools_used.append("terminal")
                if cmd_result.success:
                    yield self._thinking(f"Команда выполнена успешно ✓")
                    yield self._log("success", f"Command completed successfully:\n{cmd_result.output[-4000:]}")
                else:
                    command_failed = True
                    state.last_error = f"Command '{command}' failed with exit code {cmd_result.exit_code}:\n{cmd_result.output[-4000:]}"
                    yield self._thinking(f"Команда завершилась с ошибкой (код {cmd_result.exit_code})")
                    yield self._log("error", state.last_error)

        # If there are no files to change
        if not generated.files:
            state.states.append(generated.rationale)
            if not generated.commands:
                state.actions.append("Answered without file modifications.")
                state.tools_used.append("gemini-rest")
                yield self._thinking("Формулирую развернутый ответ на запрос...")
                try:
                    import os
                    # Read README.md if it exists in the workspace
                    readme_content = ""
                    readme_path = os.path.join(state.workspace, "README.md")
                    if os.path.exists(readme_path):
                        try:
                            with open(readme_path, "r", encoding="utf-8") as rf:
                                readme_content = rf.read(12000)
                        except Exception:
                            pass
                    
                    # Clip AST summary to avoid proxy timeout
                    ws_summary_clipped = state.workspace_summary or ""
                    if len(ws_summary_clipped) > 8000:
                        ws_summary_clipped = ws_summary_clipped[:8000] + "\n... [truncated for brevity] ..."

                    rich_prompt = (
                        f"User request: {state.task}\n\n"
                        f"Workspace README.md:\n{readme_content}\n\n"
                        f"Workspace AST summary (clipped):\n{ws_summary_clipped}\n\n"
                        f"Associative Memory Context (from DSM/RLD):\n{state.memory_context}\n\n"
                        "Please answer the user's request thoroughly and naturally. "
                        "Since the query is informational/read-only, write a comprehensive, high-quality response. "
                        "Do not include any file-change instructions or patch content in the response. "
                        "Write the response in the same language the user asked in (which is usually Russian)."
                    )
                    rich_response = await asyncio.to_thread(
                        self.gemini.generate_text,
                        rich_prompt,
                        "You are Sharrowkin, an expert AI developer agent. "
                        "Provide a professional, friendly, and very detailed response to the user's query about the project or code. "
                        "Structure your reply with clean markdown headers and bullet points. "
                        "Answer in the same language as the user query."
                    )
                    state.last_rationale = rich_response
                except Exception as exc:
                    print(f"[AGENT] Rich response generation failed: {exc}")
                yield self._thinking("Задача решена без изменения файлов.")
                yield self._log("success", "Task answered without code changes.")
            else:
                state.changes_made = True
                yield self._thinking("Команды выполнены. Проверяю результат...")
                yield self._log("success", generated.rationale or "Commands executed successfully.")
            yield self._phase("Reason", "done")
            return

        # Multi-file Reasoning: Apply file edits
        yield self._thinking(f"Применяю изменения в {len(generated.files)} файл(ах)...")
        changes = [ProposedFileChange(path=path, content=content) for path, content in generated.files.items()]
        patch = await asyncio.to_thread(apply_changes, state.workspace, changes)
        state.final_diff = patch.diff or await asyncio.to_thread(git_diff, state.workspace)
        state.changes_made = True
        state.states.append(generated.rationale)
        state.actions.append(f"Applied patch touching {len(patch.changed_files)} files")
        state.tools_used.append("gemini-rest")
        state.tools_used.append("file-writer")
        yield self._thinking(f"Патч применён: изменено {len(patch.changed_files)} файлов")
        yield {"type": "diff", "diff": state.final_diff, "files": patch.changed_files}

        if command_failed:
            yield self._log("error", "Patch applied, but some terminal commands failed.")
        else:
            yield self._log("success", generated.rationale or "Patch generated and applied.")
        yield self._phase("Reason", "done")

    # --- Phase: Stabilize (test) --------------------------------------------
    async def _stabilize(
        self,
        state: AgentRunState,
        iteration: int,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Stabilize", "active")
        yield self._thinking(f"Запускаю тесты для проверки (итерация {iteration})...")
        yield self._log("info", f"Running pytest, iteration {iteration}.")
        test_result = await asyncio.to_thread(run_pytest, state.workspace)
        state.actions.append(f"pytest exited with {test_result.exit_code}")
        state.tools_used.append("pytest")
        if test_result.success:
            state.last_error = ""
            yield self._thinking("Тесты прошли успешно ✓")
            yield self._log("success", test_result.output or "pytest completed successfully.")
            yield self._phase("Stabilize", "done")
            return
        state.last_error = test_result.output
        yield self._thinking(f"Тесты упали. Анализирую ошибку и пробую исправить...")
        yield self._log("error", test_result.output)
        yield self._phase("Stabilize", "error")

    # --- Phase: Commit (learn) ----------------------------------------------
    async def _commit(
        self,
        state: AgentRunState,
        memory: MemoryBridge,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Commit", "active")
        yield self._thinking("Сохраняю успешное решение в память (RLD + DSM)...")
        final_answer = "\n".join(
            [
                "Task completed by Sharrowkin.",
                "Final diff:",
                state.final_diff,
            ]
        )
        await asyncio.to_thread(
            memory.learn_success,
            task=state.task,
            states=state.states,
            actions=state.actions,
            final_answer=final_answer,
            tools_used=state.tools_used,
        )
        yield self._thinking("Решение сохранено в эволюционную память.")
        yield self._log("success", "Saved successful reasoning gene and DSM project memory.")
        yield self._phase("Commit", "done")
