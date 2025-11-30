"""
Global State Definition for AI Equity Analyst Agent

This module defines the TypedDict structure that represents the shared state
across all nodes in the LangGraph workflow.
"""

from __future__ import annotations

from typing import TypedDict, Optional, List

# 【Refactor】從底層 models 包導入
from src.models.financial import FinancialStatements
from src.models.valuation import ValuationMetrics
from src.models.analysis import QualitativeAnalysis


class AgentState(TypedDict):
    """
    Global state shared across all nodes in the LangGraph workflow.
    
    Attributes:
        ticker: Target stock ticker symbol
        sec_text_chunk: Raw SEC filing text (supports manual injection)
        financial_data: Extracted financial data (Pydantic object)
        valuation_metrics: Calculated valuation metrics (Pydantic object)
        qualitative_analysis: Qualitative analysis text
        final_report: Final generated report in Markdown format
        error: Error control flag for exception handling
    """
    ticker: str
    
    # --- [New] 公司戰略畫像 ---
    company_name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    valuation_strategy: str  # e.g., "general_dcf", "bank_ddm", "reit_nav", "saas_rule40"
    strategy_reasoning: Optional[str]  # LLM 選擇該策略的理由
    
    # --- 原始數據 ---
    sec_text_chunk: Optional[str]
    
    # --- 結構化業務數據 (使用 Pydantic Object) ---
    financial_data: Optional[FinancialStatements]
    valuation_metrics: Optional[ValuationMetrics]
    
    # 其他節點暫時用簡單類型
    qualitative_analysis: Optional[QualitativeAnalysis]  # [Update] 使用強類型
    final_report: Optional[str]
    
    # --- [New] 調查任務隊列 ---
    # 用於存儲上游節點發現的異常，指導 Researcher 進行定向搜索
    # 例如: ["UNH non-recurring charges 2024 analysis", "UNH normalized income discrepancy"]
    investigation_tasks: Optional[List[str]]
    
    # --- 控制信號 ---
    # 簡單字符串，與業務數據分離
    error: Optional[str]

