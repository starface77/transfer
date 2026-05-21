from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from .memory import DynamicSegmentedMemory, summarize
from .models import ActiveContext, MemorySegment, TiidoTurn

TIIDO_SNAPSHOT_PATH = Path("storage") / "personal_ai_v1.json"
TIIDO_STORAGE_PATH = TIIDO_SNAPSHOT_PATH
PERSONAL_DNA_PATHS = (
    ("User", "Danil", "Profile"),
    ("Identity", "Core"),
)


class ModelCallable(Protocol):
    def __call__(self, context: str, message: str) -> str:
        pass


class TiidoDSMRuntime:
    """DSM-first interaction loop for a personal model."""

    def __init__(
        self,
        memory: DynamicSegmentedMemory | None = None,
        *,
        storage_path: str | Path | None = None,
        model: ModelCallable | None = None,
    ):
        self.memory = memory or DynamicSegmentedMemory(storage_path)
        self.model = model
        self.ensure_core_identity()

    def prepare(self, message: str, *, k: int | None = None) -> ActiveContext:
        self.memory.extract_personal_dna(message)
        return self.memory.active_context(message, k=k)

    def respond(
        self,
        message: str,
        model: ModelCallable | None = None,
        *,
        k: int | None = None,
    ) -> TiidoTurn:
        active = self.prepare(message, k=k)
        generator = model or self.model
        if generator is None:
            answer = active.context_text
        else:
            answer = generator(active.context_text, message)
        learned = self.memory.learn_tiido_turn(message, answer, active)
        return TiidoTurn(
            user_message=message,
            active_context=active,
            answer=answer,
            learned_segment_ids=[segment.id for segment in learned],
        )

    def export_snapshot(self, path: str | Path = TIIDO_SNAPSHOT_PATH) -> None:
        self.memory.export_json(path)

    def ensure_core_identity(self) -> None:
        if has_path(self.memory.segments.values(), ("Identity", "Core")):
            return
        self.memory.write(
            "Tiido is a DSM-driven personal AI. Every response must be grounded in "
            "Dynamic Context Injection from memory before generation.",
            category_path=("Identity", "Core"),
            importance=1.0,
            metadata={"tiido_core": True},
            update_existing=False,
        )


def has_path(segments: object, path: tuple[str, ...]) -> bool:
    return any(isinstance(segment, MemorySegment) and segment.category_path == path for segment in segments)


def simple_model(handler: Callable[[str, str], str]) -> ModelCallable:
    return handler


def tiido_summary(message: str) -> str:
    return summarize(message, max_words=18)
