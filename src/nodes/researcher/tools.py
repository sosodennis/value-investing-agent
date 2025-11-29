"""
Node C: Researcher - Private Tools

This module contains research utilities:
1. Market news search using Tavily API
2. News aggregation and context building
"""

import os
from tavily import TavilyClient


def search_market_news(ticker: str) -> str:
    """
    使用 Tavily 搜索最近的市場新聞與分析師觀點。
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        str: Aggregated news context, or error message
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: Missing TAVILY_API_KEY"
    
    try:
        tavily = TavilyClient(api_key=api_key)
        print(f"🔍 [Tool] 正在搜索 {ticker} 的最新市場新聞...")
        
        # 搜索最近 3-5 天的高權重內容
        response = tavily.search(
            query=f"{ticker} stock analyst rating price target future growth risks",
            search_depth="advanced",
            max_results=5
        )
        
        # 拼接搜索結果
        context = ""
        for result in response.get("results", []):
            context += f"- {result['content']}\n"
        
        return context
    except Exception as e:
        print(f"❌ Tavily Search Error: {e}")
        return "No news found due to error."

