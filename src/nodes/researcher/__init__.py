"""
Node C: Researcher Module

This node performs deep research using:
- Tavily API for market sentiment analysis
- Competitive landscape research
- Industry trend analysis

Uses Gemini for data extraction and qualitative analysis.
"""

from .node import researcher_node

__all__ = ["researcher_node"]

