"""
Node B: Calculator Module

This module performs pure Python mathematical calculations:
- Three-statement model reconciliation
- Valuation ratios (P/E, P/B, EV/EBITDA, etc.)
- DCF (Discounted Cash Flow) model

Note: This node does NOT use LLM to ensure calculation accuracy.
"""

from .node import calculator_node

__all__ = ["calculator_node"]

