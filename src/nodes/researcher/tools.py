"""
Node C: Researcher - Private Tools

This module contains research utilities:
1. Market news search using Tavily API
2. News aggregation and context building
"""

import os
from tavily import TavilyClient


def search_market_news(query: str) -> str:
    """
    使用 Tavily 搜索市場新聞與分析師觀點。
    
    Args:
        query: Search query (可以是 ticker 或具體的調查任務)
        
    Returns:
        str: Aggregated news context, or error message
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: Missing TAVILY_API_KEY"
    
    try:
        tavily = TavilyClient(api_key=api_key)
        print(f"🔍 [Tool] 正在搜索: {query}")
        
        # 搜索最近 3-5 天的高權重內容
        response = tavily.search(
            query=query,
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

