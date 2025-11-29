"""
Node D: Writer Module

This module aggregates all structured and unstructured data to generate
a comprehensive equity research report in Markdown format.

Uses Gemini 1.5 Pro for high-quality report generation, leveraging its
large context window to incorporate all analysis results.
"""

from .node import writer_node

__all__ = ["writer_node"]

