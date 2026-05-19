"""Real Sharrowkin cognitive agent loop with live thinking stream."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from llm import GeminiClient, GeminiConfigurationError
from memory import MemoryBridge
from personas import get_persona_manager, inject_persona, format_log
from personas.llm_integration import LogType
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
    read_file,
    list_files,
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
        self.conversation_history: list[dict] = []
        self.persona_manager = get_persona_manager()

    # --- helper emitters ---------------------------------------------------
    def _phase(self, name: str, status: str) -> dict[str, object]:
        return {"type": "phase_change", "phase": name.lower(), "status": status}

    def _log(self, level: str, message: str) -> dict[str, object]:
        return {"type": "log", "level": level, "message": message}

    def _task_update(self, task_id: str, status: str) -> dict[str, object]:
        """Emit task status update for frontend."""
        return {"type": "task_update", "task_id": task_id, "status": status}

    def _status(self, status: str) -> dict[str, object]:
        return {"type": "status", "status": status}

    def _thinking(self, text: str) -> dict[str, object]:
        """Emit a 'thinking' event so the frontend shows live agent reasoning."""
        return {"type": "thinking", "content": text}

    def _format_history(self) -> str:
        """Format recent conversation history for LLM context."""
        if len(self.conversation_history) <= 1:
            return ""
        # Take last 10 messages (excluding the current one which is last)
        recent = self.conversation_history[-11:-1]
        if not recent:
            return ""
        lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Sharrowkin"
            # Truncate long messages
            content = msg["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"{role}: {content}")
        return "CONVERSATION HISTORY:\n" + "\n\n".join(lines)

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

        # Store user message in conversation history
        self.conversation_history.append({"role": "user", "content": task})

        # --- Intent Routing ---
        try:
            intent = await asyncio.to_thread(self.gemini.classify_intent, task)
            print(f"[AGENT] Intent result: {intent}")
            if intent.get("is_conversational"):
                response = intent.get("response")
                if not response:
                    if not self.gemini.configured:
                        # Get agent name from persona
                        from personas import get_agent_name
                        agent_name = get_agent_name()
                        response = f"Привет! Я {agent_name} — автономный агент-разработчик. Чем могу помочь?"
                    else:
                        try:
                            # Build conversation context for LLM
                            history_text = self._format_history()
                            prompt = f"{history_text}\n\nUser: {task}" if history_text else task
                            # Inject persona into system instruction - persona REPLACES base instruction
                            base_instruction = (
                                "You have access to the conversation history above. "
                                "Respond naturally and helpfully to the user's latest message. "
                                "Keep it concise and friendly. Answer in the same language the user writes in."
                            )
                            system_instruction = inject_persona(base_instruction)

                            response = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.gemini.generate_text,
                                    prompt,
                                    system_instruction
                                ),
                                timeout=20,
                            )
                        except Exception as exc:
                            print(f"[AGENT] LLM response generation failed: {exc}")
                            from personas import get_agent_name
                            agent_name = get_agent_name()
                            response = f"Привет! Я {agent_name} — автономный агент-разработчик. Чем могу помочь?"
                # Store assistant response
                self.conversation_history.append({"role": "assistant", "content": response})
                # Keep history manageable (last 20 messages)
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                yield {"type": "content", "content": response}
                yield self._status("done")
                return
        except Exception as exc:
            print(f"[AGENT] Intent classification error: {exc}")

        # --- Informational / Read-Only Flow ---
        if intent.get("is_informational"):
            yield self._log("system", "Informational analysis cycle started.")
            
            try:
                # 1. Observe Phase (AST Scan)
                async for event in self._observe(state, memory):
                    yield event
                
                # 2. Recall Phase (Memory Retrieval)
                async for event in self._recall(state, memory):
                    yield event
                
                # 3. Reason Phase (Rich response generation)
                yield self._phase("Reason", "active")
                yield self._log("info", "Generating response...")
                
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
                        inject_persona(
                            "Provide a professional, friendly, and very detailed response to the user's query about the project or code. "
                            "Structure your reply with clean markdown headers and bullet points. "
                            "Answer in the same language as the user query."
                        )
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
        yield self._log("system", "Cognitive cycle started.")

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
            yield self._thinking(f"API key not configured: {exc}")
            yield {"type": "content", "content": f"⚠️ **API ключ не настроен.**\n\nДобавьте `GEMINI_API_KEY` в файл `backend/backend/.env` для работы с кодом.\n\n```\n{exc}\n```"}
            yield self._status("needs_key")
            yield self._log("error", str(exc))
        except Exception as exc:
            print(f"[AGENT] Cycle error: {exc}")
            yield self._thinking(f"Error: {exc}")
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
        yield self._log("info", f"Scanning workspace: {state.workspace}")
        summaries = await asyncio.to_thread(scan_workspace, state.workspace)
        state.workspace_summary = summarize_workspace(summaries)
        state.states.append(state.workspace_summary)
        state.actions.append(f"Scanned {len(summaries)} source files with AST summaries")
        state.tools_used.append("pathlib")
        state.tools_used.append("ast")
        file_list = [s.path for s in summaries[:15]]
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
        yield self._log("info", "Retrieving memory context.")
        state.memory_context = await asyncio.to_thread(memory.recall, state.task)
        state.states.append(state.memory_context)
        state.actions.append("Loaded RLD active context and DSM active context")
        state.tools_used.append("rld")
        state.tools_used.append("dsm")
        yield self._log("success", f"Memory loaded ({len(state.memory_context)} chars).")
        yield self._phase("Recall", "done")

    # --- Phase: Reason (patch generation) -----------------------------------
    async def _reason(
        self,
        state: AgentRunState,
        iteration: int,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Reason", "active")
        yield self._log("info", f"Generating patch with LLM, iteration {iteration}.")

        # --- HIERARCHICAL PLANNING: Generate task plan on first iteration ---
        if iteration == 1 and self.gemini.configured:
            try:
                from planning import HierarchicalPlanner, PlanningContext

                planner = HierarchicalPlanner()
                context = PlanningContext(
                    workspace_summary=state.workspace_summary,
                    memory_context=state.memory_context,
                    available_tools=["file_reader", "file_writer", "terminal", "pytest"]
                )

                # Generate hierarchical plan
                task_graph = await asyncio.to_thread(planner.plan, state.task, context)

                # Convert to frontend format
                def task_to_dict(task):
                    return {
                        "id": task.id,
                        "title": task.description,
                        "status": "pending",
                        "estimatedTime": f"~{task.estimated_time}min" if task.estimated_time else None,
                        "subtasks": [task_to_dict(st) for st in task.subtasks] if task.subtasks else []
                    }

                plan_data = [task_to_dict(t) for t in task_graph.tasks.values() if not task_graph.get_dependencies(t.id)]

                # Send plan to frontend
                yield {
                    "type": "task_plan",
                    "plan": plan_data
                }

                yield self._log("success", f"Generated execution plan with {len(task_graph.tasks)} tasks")
            except Exception as e:
                print(f"[AGENT] Planning failed (non-fatal): {e}")

        # --- PRE-READ: Ask LLM which files to read first ---
        file_contents: dict[str, str] = {}
        if iteration == 1 and self.gemini.configured:
            try:
                plan_prompt = (
                    f"TASK: {state.task}\n\n"
                    f"WORKSPACE FILES:\n{state.workspace_summary[:6000]}\n\n"
                    "List the file paths (max 8) that need to be READ to complete this task. "
                    "Return ONLY a JSON array of relative file paths, e.g. [\"src/main.py\", \"lib/utils.ts\"]. "
                    "No markdown, no explanation."
                )
                raw_files = await asyncio.to_thread(
                    self.gemini.generate_text, plan_prompt,
                    "You are a code analysis agent. Return only a JSON array of file paths."
                )
                import json, re
                cleaned = raw_files.strip()
                # Extract JSON array
                match = re.search(r'\[.*\]', cleaned, re.DOTALL)
                if match:
                    paths = json.loads(match.group(0))
                    if isinstance(paths, list):
                        for p in paths[:8]:
                            if isinstance(p, str):
                                content = await asyncio.to_thread(read_file, state.workspace, p)
                                if not content.startswith("ERROR:"):
                                    file_contents[p] = content
                        if file_contents:
                            yield self._log("info", f"Pre-read {len(file_contents)} files.")
                        state.actions.append(f"Pre-read {len(file_contents)} files for context")
                        state.tools_used.append("file-reader")
            except Exception as e:
                print(f"[AGENT] Pre-read failed (non-fatal): {e}")

        # --- Generate patch with file contents ---
        generated = await asyncio.to_thread(
            self.gemini.generate_patch,
            task=state.task,
            workspace_summary=state.workspace_summary,
            memory_context=state.memory_context,
            previous_error=state.last_error,
            action_history=state.actions,
            file_contents=file_contents,
        )
        state.last_rationale = generated.rationale

        # Show LLM's actual reasoning as thinking
        if generated.rationale:
            yield self._thinking(generated.rationale)

        # Task Decomposition
        if generated.subtasks:
            yield self._log("info", "Subtasks:\n" + "\n".join(f" - {t}" for t in generated.subtasks))
            state.actions.append(f"Decomposed task into {len(generated.subtasks)} subtasks")

        # Tool Router: Run Terminal Commands
        command_failed = False
        if generated.commands:
            for command in generated.commands:
                yield self._log("info", f"$ {command}")
                cmd_result = await asyncio.to_thread(run_terminal_command, state.workspace, command)
                state.actions.append(f"Executed: {command} (code {cmd_result.exit_code})")
                state.tools_used.append("terminal")
                if cmd_result.success:
                    yield self._log("success", f"Command OK:\n{cmd_result.output[-4000:]}")
                else:
                    command_failed = True
                    state.last_error = f"Command '{command}' failed with exit code {cmd_result.exit_code}:\n{cmd_result.output[-4000:]}"
                    yield self._log("error", state.last_error)

        # If there are no files to change
        if not generated.files:
            state.states.append(generated.rationale)
            if not generated.commands:
                state.actions.append("Answered without file modifications.")
                state.tools_used.append("gemini-rest")

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
                        inject_persona(
                            "Provide a professional, friendly, and very detailed response to the user's query about the project or code. "
                            "Structure your reply with clean markdown headers and bullet points. "
                            "Answer in the same language as the user query."
                        )
                    )
                    state.last_rationale = rich_response
                except Exception as exc:
                    print(f"[AGENT] Rich response generation failed: {exc}")
                yield self._log("success", "Answered without code changes.")
            else:
                state.changes_made = True
                yield self._log("success", generated.rationale or "Commands executed.")
            yield self._phase("Reason", "done")
            return

        # Multi-file Reasoning: Apply file edits
        yield self._log("info", f"Patching {len(generated.files)} file(s)...")
        changes = [ProposedFileChange(path=path, content=content) for path, content in generated.files.items()]
        patch = await asyncio.to_thread(apply_changes, state.workspace, changes)
        state.final_diff = patch.diff or await asyncio.to_thread(git_diff, state.workspace)
        state.changes_made = True
        state.states.append(generated.rationale)
        state.actions.append(f"Applied patch touching {len(patch.changed_files)} files")
        state.tools_used.append("gemini-rest")
        state.tools_used.append("file-writer")
        yield self._log("info", f"Applied patch to {len(patch.changed_files)} files.")
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
        yield self._log("info", f"Running pytest, iteration {iteration}.")
        test_result = await asyncio.to_thread(run_pytest, state.workspace)
        state.actions.append(f"pytest exited with {test_result.exit_code}")
        state.tools_used.append("pytest")

        if test_result.success:
            state.last_error = ""
            yield self._log("success", test_result.output or "pytest passed.")
            yield self._phase("Stabilize", "done")
            return

        # Test failed - analyze with debugger
        state.last_error = test_result.output
        yield self._log("error", test_result.output)

        # Intelligent error analysis
        try:
            from debugging import DebuggerSession

            debugger = DebuggerSession(state.workspace)

            # Parse error from pytest output
            error_info = self._parse_pytest_error(test_result.output)

            if error_info:
                yield self._log("info", "Analyzing error with debugger...")

                # Send debug analysis to frontend
                yield {
                    "type": "debug_analysis",
                    "error_type": error_info.get("type", "Unknown"),
                    "error_message": error_info.get("message", ""),
                    "file_path": error_info.get("file", ""),
                    "line_number": error_info.get("line", 0),
                    "root_cause": error_info.get("root_cause", ""),
                    "suggested_fix": error_info.get("suggested_fix", "")
                }

                yield self._log("info", f"Root cause: {error_info.get('root_cause', 'Unknown')}")
                yield self._log("info", f"Suggested fix: {error_info.get('suggested_fix', 'See error details')}")

        except Exception as e:
            print(f"[AGENT] Debug analysis failed: {e}")

        yield self._phase("Stabilize", "error")

    def _parse_pytest_error(self, output: str) -> dict[str, str] | None:
        """Parse pytest output to extract error information."""
        import re

        # Look for common error patterns
        # Example: "AttributeError: 'NoneType' object has no attribute 'method'"
        error_match = re.search(r'(\w+Error): (.+)', output)
        if not error_match:
            return None

        error_type = error_match.group(1)
        error_message = error_match.group(2)

        # Extract file and line number
        # Example: "test_file.py:42: AttributeError"
        location_match = re.search(r'([^/\s]+\.py):(\d+):', output)
        file_path = location_match.group(1) if location_match else ""
        line_number = int(location_match.group(2)) if location_match else 0

        # Generate root cause and fix based on error type
        root_cause = ""
        suggested_fix = ""

        if error_type == "AttributeError" and "NoneType" in error_message:
            root_cause = "Attempting to access attribute on None object"
            suggested_fix = "Add null check: if obj is not None: obj.attribute"
        elif error_type == "KeyError":
            root_cause = f"Dictionary key not found: {error_message}"
            suggested_fix = "Use safe access: dict.get(key, default_value)"
        elif error_type == "IndexError":
            root_cause = "List index out of range"
            suggested_fix = "Add bounds check: if index < len(list): list[index]"
        elif error_type == "TypeError":
            root_cause = "Type mismatch in operation"
            suggested_fix = "Check operand types and convert if necessary"
        elif error_type == "AssertionError":
            root_cause = "Test assertion failed"
            suggested_fix = "Review test expectations and actual output"
        else:
            root_cause = f"Error of type {error_type}"
            suggested_fix = "Review error message and stack trace"

        return {
            "type": error_type,
            "message": error_message,
            "file": file_path,
            "line": line_number,
            "root_cause": root_cause,
            "suggested_fix": suggested_fix
        }

    # --- Phase: Commit (learn) ----------------------------------------------
    async def _commit(
        self,
        state: AgentRunState,
        memory: MemoryBridge,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Commit", "active")
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
        yield self._log("success", "Solution committed to memory.")
        yield self._phase("Commit", "done")
