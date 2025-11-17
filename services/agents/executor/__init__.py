"""
Execution Adapter - handles writeback to claims system with guarded permissions.
"""

from .executor_agent import ExecutorAgent, ExecutionResult, ExecutionPermission

__all__ = ["ExecutorAgent", "ExecutionResult", "ExecutionPermission"]
