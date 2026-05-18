from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
_SRC_DSM = _SRC / "dsm"
if _SRC.exists():
    sys.path.insert(0, str(_SRC))
if _SRC_DSM.exists() and "__path__" in globals():
    __path__.append(str(_SRC_DSM))

from dsm.embedding import HashEmbeddingModel  # noqa: E402
from dsm.memory import DynamicSegmentedMemory  # noqa: E402
from dsm.models import ActiveContext, MemorySegment, PriorityVector, ReasoningTrace, RouteResult, TiidoTurn  # noqa: E402
from dsm.tiido import PERSONAL_DNA_PATHS, TIIDO_SNAPSHOT_PATH, TIIDO_STORAGE_PATH, TiidoDSMRuntime  # noqa: E402

__all__ = [
    "ActiveContext",
    "DynamicSegmentedMemory",
    "HashEmbeddingModel",
    "MemorySegment",
    "PriorityVector",
    "ReasoningTrace",
    "RouteResult",
    "TiidoDSMRuntime",
    "TiidoTurn",
    "PERSONAL_DNA_PATHS",
    "TIIDO_SNAPSHOT_PATH",
    "TIIDO_STORAGE_PATH",
]
