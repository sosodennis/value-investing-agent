"""
Node C: Researcher Module

This node performs deep research using:
- Tavily API for market sentiment analysis
- Competitive landscape research
- Industry trend analysis

Uses Gemini 1.5 Flash for data extraction and Gemini 1.5 Pro for qualitative analysis.
"""

from .node import researcher_node

__all__ = ["researcher_node"]

