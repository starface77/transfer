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
                yield self._status("done")
                yield self._log("success", "Task stabilized and stored in local memory.")
            else:
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
        if not generated.files:
            state.states.append(generated.rationale)
            state.actions.append("Answered without file modifications.")
            state.tools_used.append("gemini-rest")
            yield self._log("success", generated.rationale or "Task answered without code changes.")
            yield self._phase("Reason", "done")
            return

        changes = [ProposedFileChange(path=path, content=content) for path, content in generated.files.items()]
        patch = await asyncio.to_thread(apply_changes, state.workspace, changes)
        state.final_diff = patch.diff or await asyncio.to_thread(git_diff, state.workspace)
        state.changes_made = True
        state.states.append(generated.rationale)
        state.actions.append(f"Applied patch touching {len(patch.changed_files)} files")
        state.tools_used.append("gemini-rest")
        state.tools_used.append("file-writer")
        yield {"type": "diff", "diff": state.final_diff, "files": patch.changed_files}
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
        return {"type": "phase", "phase": name, "status": status}

    def _log(self, level: str, message: str) -> dict[str, object]:
        return {"type": "log", "level": level, "message": message}

    def _status(self, status: str) -> dict[str, object]:
        return {"type": "status", "status": status}
