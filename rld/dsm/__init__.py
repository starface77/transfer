from __future__ import annotations

from pathlib import Path

_SRC_DSM = Path(__file__).resolve().parent.parent / "src" / "dsm"
if _SRC_DSM.exists():
    __path__.append(str(_SRC_DSM))

from dsm.embedding import HashEmbeddingModel  # noqa: E402
from dsm.memory import DynamicSegmentedMemory  # noqa: E402
from dsm.models import ActiveContext, MemorySegment, PriorityVector, ReasoningTrace, RouteResult  # noqa: E402

__all__ = [
    "ActiveContext",
    "DynamicSegmentedMemory",
    "HashEmbeddingModel",
    "MemorySegment",
    "PriorityVector",
    "ReasoningTrace",
    "RouteResult",
]
