from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
_SRC_RLD = _SRC / "rld"
if _SRC.exists():
    sys.path.insert(0, str(_SRC))
if _SRC_RLD.exists() and "__path__" in globals():
    __path__.append(str(_SRC_RLD))

from dsm.embedding import HashEmbeddingModel  # noqa: E402
from dsm.memory import DynamicSegmentedMemory  # noqa: E402
from dsm.models import ActiveContext, MemorySegment, PriorityVector, ReasoningTrace, RouteResult  # noqa: E402

from rld.core import (  # noqa: E402
    DSMPolicy,
    GeneExtractor,
    HashLatentEncoder,
    LatentEncoder,
    RecursiveLatentDNA,
    TrajectoryGeneExtractor,
    WeightedDSMPolicy,
)
from rld.models import (  # noqa: E402
    GENE_SCHEMA,
    ActivatedGene,
    ActivationTrace,
    LatentDelta,
    LatentState,
    RLDContext,
    ReasoningGene,
    ReasoningTrajectory,
)

__all__ = [
    "ActiveContext",
    "DynamicSegmentedMemory",
    "HashEmbeddingModel",
    "MemorySegment",
    "PriorityVector",
    "ReasoningTrace",
    "RouteResult",
    "ActivatedGene",
    "ActivationTrace",
    "DSMPolicy",
    "GENE_SCHEMA",
    "GeneExtractor",
    "HashLatentEncoder",
    "LatentDelta",
    "LatentEncoder",
    "LatentState",
    "RLDContext",
    "ReasoningGene",
    "ReasoningTrajectory",
    "RecursiveLatentDNA",
    "TrajectoryGeneExtractor",
    "WeightedDSMPolicy",
]
