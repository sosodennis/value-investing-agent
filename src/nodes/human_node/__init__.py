"""
Human-in-the-Loop Node Module

This module handles human intervention at critical decision points:
- Data injection (manual SEC filing upload)
- Error correction
- Analysis assumption adjustments

Supports state updates through update_state mechanism.
"""

from .node import request_human_help_node

__all__ = ["request_human_help_node"]

