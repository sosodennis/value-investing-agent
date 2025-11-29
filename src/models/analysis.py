"""
Qualitative Analysis Domain Model

This module defines the Pydantic schema for qualitative analysis results.
Used by Node C (Researcher) to structure its output.
"""

from pydantic import BaseModel, Field
from typing import List


class QualitativeAnalysis(BaseModel):
    """Researcher 節點產出的定性分析結果"""
    
    market_sentiment: str = Field(description="Current market sentiment (Bullish/Bearish/Neutral)")
    key_growth_drivers: List[str] = Field(description="List of key drivers for future growth (e.g., AI, Services)")
    top_risks: List[str] = Field(description="List of major risks mentioned in 10-K or News")
    management_tone: str = Field(description="Analysis of management's tone in the report")
    summary: str = Field(description="A comprehensive summary paragraph combining news and financials")

