"""
Valuation Metrics Domain Model

This module defines the Pydantic schema for valuation metrics.
Originally from Node B (Calculator), now in the independent models layer.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ValuationMetrics(BaseModel):
    """Valuation metrics structure (Domain Model)"""
    
    market_cap: float = Field(description="Market Capitalization in millions")
    current_price: float = Field(description="Current Stock Price")
    
    # --- 獲利能力指標 ---
    net_profit_margin: float = Field(description="Net Profit Margin (%) based on FY data")
    
    # --- [New] 標準化利潤指標 ---
    eps_ttm: Optional[float] = Field(description="Basic EPS (TTM)")
    eps_normalized: Optional[float] = Field(description="EPS excluding Non-Recurring Items (Normalized)")
    
    # 用於標記是否使用了標準化數據
    is_normalized: bool = Field(description="True if valuation is based on Normalized Income", default=False)
    
    # --- [Update] 雙軌 P/E ---
    pe_ratio_ttm: Optional[float] = Field(description="P/E based on Trailing Twelve Months (Real-time from Yahoo)")
    pe_ratio_fy: float = Field(description="P/E based on last Fiscal Year (Calculated from 10-K)")
    
    # 為了兼容舊代碼，pe_ratio 主要指代用於估值判斷的那個（優先 TTM）
    pe_ratio: float = Field(description="Primary P/E used for valuation status (Prioritize TTM)")
    
    pe_trend_insight: str = Field(description="Insight derived from comparing TTM vs FY P/E")
    
    # --- 狀態 ---
    valuation_status: str = Field(description="Undervalued / Fair / Overvalued based on P/E")
    
    # --- DCF 結果 ---
    dcf_value: float = Field(description="Intrinsic Value per share calculated by DCF")
    dcf_upside: float = Field(description="Upside/Downside potential in %")

