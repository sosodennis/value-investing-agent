"""
Valuation Metrics Domain Model

This module defines the Pydantic schema for valuation metrics.
Originally from Node B (Calculator), now in the independent models layer.
"""

from pydantic import BaseModel, Field


class ValuationMetrics(BaseModel):
    """Valuation metrics structure (Domain Model)"""
    
    pe_ratio: float = Field(description="Price to Earnings Ratio")
    valuation_status: str = Field(description="Undervalued / Fair / Overvalued")

