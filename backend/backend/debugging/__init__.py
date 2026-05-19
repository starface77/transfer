"""Debugging subsystem for Sharrowkin agent.

Provides intelligent debugging capabilities:
- Debugger integration (pdb/ipdb)
- Profiling (cProfile, py-spy)
- Test generation
- Coverage analysis
"""

from .debugger_integration import DebuggerIntegration, BreakpointStrategy
from .profiler import Profiler, ProfileResult, BottleneckReport
from .test_generator import TestGenerator, TestCase, TestSuite
from .coverage_analyzer import CoverageAnalyzer, CoverageReport

__all__ = [
    "DebuggerIntegration",
    "BreakpointStrategy",
    "Profiler",
    "ProfileResult",
    "BottleneckReport",
    "TestGenerator",
    "TestCase",
    "TestSuite",
    "CoverageAnalyzer",
    "CoverageReport",
]
