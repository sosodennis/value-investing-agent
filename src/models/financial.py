"""
Financial Data Domain Model

This module defines the Pydantic schema for financial statements data.
"""

from pydantic import BaseModel, Field
from typing import Optional

class FinancialStatements(BaseModel):
    """
    財務數據模型 (Domain Model)
    所有欄位默認為 Optional，以支持「部分提取」和「後續補全」。
    """
    
    # --- 1. 基礎數據 (Basic Data) ---
    # 如果這些缺失，估值模型通常無法啟動。但我們允許 Miner 暫時返回 None，
    # 留給 Merger 查看 User 是否有手動上傳。
    fiscal_year: Optional[str] = Field(
        default=None, 
        description="Fiscal year end date (e.g., '2023' or '2023-09-30')"
    )
    total_revenue: Optional[float] = Field(
        default=None, 
        description="Total Revenue in millions. Essential for almost all valuations."
    )
    net_income: Optional[float] = Field(
        default=None, 
        description="Net Income in millions. Essential for PE/EPS based valuations."
    )
    
    # --- 2. 進階數據 (Advanced Data: DCF/Cash Flow) ---
    operating_cash_flow: Optional[float] = Field(
        default=None, 
        description="Net Cash provided by Operating Activities in millions. Key for DCF."
    )
    capital_expenditures: Optional[float] = Field(
        default=None, 
        description="Capital Expenditures (Capex) in millions. Key for Free Cash Flow."
    )
    
    # --- 3. 策略特定數據 (REITs/Banks etc.) ---
    depreciation_amortization: Optional[float] = Field(
        default=None,
        description="Depreciation and Amortization in millions (REIT specific for FFO)."
    )
    gain_on_sale: Optional[float] = Field(
        default=None,
        description="Gain on sale of real estate in millions (REIT specific for FFO)."
    )
    
    # --- Metadata ---
    source: str = Field(
        default="Unknown", 
        description="Source of data (e.g., 'SEC 10-K', 'User Upload', 'Yahoo Finance')"
    )

    @property
    def has_basic_data(self) -> bool:
        """檢查是否擁有最基礎的數據"""
        return all([self.total_revenue is not None, self.net_income is not None])