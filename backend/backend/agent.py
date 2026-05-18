"""Real Sharrowkin cognitive agent loop."""

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

    async def run(self, task: str, workspace_path: str) -> AsyncIterator[dict[str, object]]:
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

        # Intent Routing: intercept conversational messages early
        try:
            intent = await asyncio.to_thread(self.gemini.classify_intent, task)
            if intent.get("is_conversational"):
                response = intent.get("response")
                if not response:
                    # Heuristic matched but no LLM response yet — generate one
                    try:
                        response = await asyncio.to_thread(
                            self.gemini.generate_text,
                            task,
                            "You are Sharrowkin, a friendly AI coding assistant. "
                            "Respond naturally and helpfully to the user's message. "
                            "Keep it concise and friendly. Answer in the same language the user writes in."
                        )
                    except Exception:
                        response = "Привет! Я Sharrowkin — автономный агент-разработчик. Чем могу помочь?"
                yield {"type": "content", "content": response}
                yield self._status("done")
                return
        except Exception as exc:
            print(f"[AGENT] Intent classification error: {exc}")

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
            yield self._status("needs_key")
            yield self._log("error", str(exc))
        except Exception as exc:
            yield self._status("error")
            yield self._log("error", f"Agent cycle failed: {exc}")

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
        await asyncio.to_thread(memory.learn_project, state.workspace_summary)
        yield self._log("success", f"Observed {len(summaries)} source files.")
        yield self._phase("Observe", "done")

    async def _recall(
        self,
        state: AgentRunState,
        memory: MemoryBridge,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Recall", "active")
        yield self._log("info", "Retrieving RLD and DSM context.")
        state.memory_context = await asyncio.to_thread(memory.recall, state.task)
        state.states.append(state.memory_context)
        state.actions.append("Loaded RLD active context and DSM active context")
        state.tools_used.append("rld")
        state.tools_used.append("dsm")
        yield self._log("success", "Memory context is ready.")
        yield self._phase("Recall", "done")

    async def _reason(
        self,
        state: AgentRunState,
        iteration: int,
    ) -> AsyncIterator[dict[str, object]]:
        yield self._phase("Reason", "active")
        yield self._log("info", f"Generating patch with Gemini, iteration {iteration}.")
        generated = await asyncio.to_thread(
            self.gemini.generate_patch,
            task=state.task,
            workspace_summary=state.workspace_summary,
            memory_context=state.memory_context,
            previous_error=state.last_error,
        )
        state.last_rationale = generated.rationale

        # 1. Task Decomposition
        if generated.subtasks:
            yield self._log("info", "Plan decomposed into subtasks:\n" + "\n".join(f" - {t}" for t in generated.subtasks))
            state.actions.append(f"Decomposed task into {len(generated.subtasks)} subtasks")

        # 2. Tool Router: Run Terminal Commands
        command_failed = False
        if generated.commands:
            for command in generated.commands:
                yield self._log("info", f"Running command: {command}")
                cmd_result = await asyncio.to_thread(run_terminal_command, state.workspace, command)
                state.actions.append(f"Executed: {command} (code {cmd_result.exit_code})")
                state.tools_used.append("terminal")
                if cmd_result.success:
                    yield self._log("success", f"Command completed successfully:\n{cmd_result.output[-4000:]}")
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
                yield self._log("success", generated.rationale or "Task answered without code changes.")
            else:
                state.changes_made = True  # We ran terminal commands, so state did change
                yield self._log("success", generated.rationale or "Commands executed successfully.")
            yield self._phase("Reason", "done")
            return

        # 3. Multi-file Reasoning: Apply file edits
        changes = [ProposedFileChange(path=path, content=content) for path, content in generated.files.items()]
        patch = await asyncio.to_thread(apply_changes, state.workspace, changes)
        state.final_diff = patch.diff or await asyncio.to_thread(git_diff, state.workspace)
        state.changes_made = True
        state.states.append(generated.rationale)
        state.actions.append(f"Applied patch touching {len(patch.changed_files)} files")
        state.tools_used.append("gemini-rest")
        state.tools_used.append("file-writer")
        yield {"type": "diff", "diff": state.final_diff, "files": patch.changed_files}
        
        if command_failed:
            yield self._log("error", "Patch applied, but some terminal commands failed.")
        else:
            yield self._log("success", generated.rationale or "Patch generated and applied.")
        yield self._phase("Reason", "done")

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
            yield self._log("success", test_result.output or "pytest completed successfully.")
            yield self._phase("Stabilize", "done")
            return
        state.last_error = test_result.output
        yield self._log("error", test_result.output)
        yield self._phase("Stabilize", "error")

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
        yield self._log("success", "Saved successful reasoning gene and DSM project memory.")
        yield self._phase("Commit", "done")

    def _phase(self, name: str, status: str) -> dict[str, object]:
        return {"type": "phase_change", "phase": name.lower(), "status": status}

    def _log(self, level: str, message: str) -> dict[str, object]:
        return {"type": "log", "level": level, "message": message}

    def _status(self, status: str) -> dict[str, object]:
        return {"type": "status", "status": status}

