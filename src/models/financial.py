"""
Financial Data Domain Model

This module defines the Pydantic schema for financial statements data.
Originally from Node A (Data Miner), now in the independent models layer.
"""

from pydantic import BaseModel, Field
from typing import Optional


class FinancialStatements(BaseModel):
    """擴充後的財務數據模型 (Domain Model)"""
    
    fiscal_year: str = Field(description="Fiscal year")
    total_revenue: float = Field(description="Total Revenue in millions")
    net_income: float = Field(description="Net Income in millions")
    
    # --- DCF 所需數據 ---
    operating_cash_flow: float = Field(description="Net Cash provided by Operating Activities in millions")
    capital_expenditures: float = Field(description="Capital Expenditures (Capex) in millions (usually negative or positive, please take absolute value for calculation logic)")
    
    source: str = Field(description="Source of data")

