"""
Global State Definition for AI Equity Analyst Agent

This module defines the TypedDict structure that represents the shared state
across all nodes in the LangGraph workflow.
"""

from typing import TypedDict, Optional, Dict


class AgentState(TypedDict):
    """
    Global state shared across all nodes in the LangGraph workflow.
    
    Attributes:
        ticker: Target stock ticker symbol
        sec_text_chunk: Raw SEC filing text (supports manual injection)
        financial_data: Extracted financial data in JSON format
        valuation_metrics: Calculated valuation metrics
        qualitative_analysis: Qualitative analysis text
        final_report: Final generated report in Markdown format
        error: Error control flag for exception handling
    """
    ticker: str                         # 目標股票代碼
    sec_text_chunk: Optional[str]       # 財報原始文本 (支持人工注入)
    financial_data: Optional[Dict]      # 提取後的財務數據 (JSON)
    valuation_metrics: Optional[Dict]   # 計算後的估值指標
    qualitative_analysis: Optional[str] # 定性分析文本
    final_report: Optional[str]         # 最終報告
    error: Optional[str]                # 錯誤控制標記

