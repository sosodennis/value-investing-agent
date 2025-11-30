"""
Qualitative Analysis Domain Model

This module defines the Pydantic schema for qualitative analysis results.
Used by Node C (Researcher) to structure its output.
"""

from pydantic import BaseModel, Field
from typing import List


class QualitativeAnalysis(BaseModel):
    """Researcher 節點產出的定性分析結果（深度洞察版本）"""
    
    # --- 基礎字段 (保留) ---
    market_sentiment: str = Field(description="Current market sentiment (Bullish/Bearish/Neutral)")
    key_growth_drivers: List[str] = Field(description="List of key drivers for future growth (e.g., AI, Services)")
    top_risks: List[str] = Field(description="List of major risks mentioned in 10-K or News")
    management_tone: str = Field(description="Analysis of management's tone in the report")
    summary: str = Field(description="A comprehensive summary paragraph combining news and financials")
    
    # --- [New] 核心論點結構 ---
    investment_thesis: str = Field(
        description="The main argument for buying/selling (bull case vs bear case). Should connect quantitative metrics with qualitative factors to tell a compelling investment story."
    )
    catalysts: List[str] = Field(
        description="Upcoming events that could move the stock in the next 6-12 months (e.g., earnings, product launch, regulatory decision)"
    )
    
    # --- [New] 估值與故事的結合 ---
    valuation_commentary: str = Field(
        description="Explanation of why the valuation (DCF/PE/P/FFO/EV-Sales) is high/low based on qualitative factors. Should reconcile quantitative metrics with market narrative."
    )
    
    risk_assessment: str = Field(
        description="Detailed risk analysis beyond generic terms. Should identify specific threats and their potential impact on the investment thesis."
    )

