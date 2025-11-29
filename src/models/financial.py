"""
Financial Data Domain Model

This module defines the Pydantic schema for financial statements data.
Originally from Node A (Data Miner), now in the independent models layer.
"""

from pydantic import BaseModel, Field


class FinancialStatements(BaseModel):
    """Financial data structure (Domain Model)"""
    
    fiscal_year: str = Field(description="Fiscal year of the data")
    total_revenue: float = Field(description="Total Revenue in millions")
    net_income: float = Field(description="Net Income in millions")
    source: str = Field(description="Source of data (Auto/User)")

