"""
Valuation Metrics Domain Model

This module defines the Pydantic schema for valuation metrics.
Originally from Node B (Calculator), now in the independent models layer.
"""

from pydantic import BaseModel, Field


class ValuationMetrics(BaseModel):
    """Valuation metrics structure (Domain Model)"""
    
    market_cap: float = Field(description="Market Capitalization in millions")
    current_price: float = Field(description="Current Stock Price")
    
    # --- 獲利能力指標 ---
    net_profit_margin: float = Field(description="Net Profit Margin (%)")
    
    # --- 估值指標 ---
    pe_ratio: float = Field(description="Price to Earnings Ratio")
    
    # --- 狀態 ---
    valuation_status: str = Field(description="Undervalued / Fair / Overvalued based on P/E")

