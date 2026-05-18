"""RLD and DSM integration for Sharrowkin."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for relative in ("memory/rld/src", "memory/dsm/src"):
    candidate = REPO_ROOT / relative
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from dsm.memory import DynamicSegmentedMemory
    from dsm.models import ActiveContext
    from rld.core import RecursiveLatentDNA
    from rld.models import RLDContext
except ImportError as import_error:
    DynamicSegmentedMemory = None
    ActiveContext = None
    RecursiveLatentDNA = None
    RLDContext = None
    IMPORT_ERROR = import_error
else:
    IMPORT_ERROR = None


class MemoryBridge:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.memory_dir = workspace / ".sharrowkin"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.disabled_reason = ""
        self.rld = None
        self.dsm = None
        if IMPORT_ERROR is not None or DynamicSegmentedMemory is None or RecursiveLatentDNA is None:
            self.disabled_reason = f"Memory modules unavailable: {IMPORT_ERROR}"
            return
        self.dsm = DynamicSegmentedMemory(self.memory_dir / "dsm_memory.json")
        self.rld = RecursiveLatentDNA(
            storage_path=self.memory_dir / "rld_genes.json",
            dsm_memory=self.dsm,
        )

    @property
    def enabled(self) -> bool:
        return self.rld is not None and self.dsm is not None

    def recall(self, task: str) -> str:
        if not self.enabled:
            return self.disabled_reason or "Memory bridge is disabled."
        if self.rld is None or self.dsm is None:
            return "Memory bridge is disabled."
        rld_context: RLDContext = self.rld.active_context(task)
        dsm_context: ActiveContext = self.dsm.active_context(task, k=4)
        return "\n\n".join(
            [
                rld_context.context_text,
                "DSM ACTIVE CONTEXT",
                dsm_context.context_text,
            ]
        )

    def learn_project(self, workspace_summary: str) -> None:
        if not self.enabled or self.dsm is None:
            return
        self.dsm.write(
            workspace_summary,
            description="Workspace AST architecture summary",
            category_path=("Project", "Architecture"),
            importance=0.65,
            metadata={"source": "sharrowkin_observe"},
        )
        self.dsm.save()

    def learn_success(
        self,
        *,
        task: str,
        states: list[str],
        actions: list[str],
        final_answer: str,
        tools_used: list[str],
    ) -> None:
        if not self.enabled or self.rld is None or self.dsm is None:
            return
        self.rld.observe(
            task,
            states=states,
            actions=actions,
            final_answer=final_answer,
            success=True,
            utility=0.9,
            tools_used=tools_used,
            metadata={"workspace": str(self.workspace)},
        )
        self.rld.save()
        self.dsm.update_from_interaction(
            task,
            final_answer,
            importance=0.8,
            metadata={"source": "sharrowkin_success"},
        )
        self.dsm.save()
        if len(self.rld.trajectories) > 0 and len(self.rld.trajectories) % 5 == 0:
            self.rld.sleep(save_after=True)
