"""
Base Valuation Strategy Interface

This module defines the abstract base class for all valuation strategies.
All strategies must implement the `calculate` method.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from src.models.valuation import ValuationMetrics
from src.models.financial import FinancialStatements


class BaseValuationStrategy(ABC):
    """所有估值策略的基類 (Interface)"""

    @abstractmethod
    def calculate(
        self, 
        ticker: str,
        financial_data: FinancialStatements, 
        market_data: Dict[str, Any]
    ) -> ValuationMetrics:
        """
        執行估值計算。
        
        Args:
            ticker: 股票代碼
            financial_data: Node A 提取的財務數據 (Pydantic)
            market_data: Node B Tools 獲取的市場數據 (Dict)
            
        Returns:
            ValuationMetrics: 計算結果
        """
        pass

