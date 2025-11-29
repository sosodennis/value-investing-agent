"""
Node C: Researcher - Main Node Logic

This node orchestrates deep research:
1. Searches market sentiment using Tavily API
2. Analyzes competitive landscape
3. Synthesizes qualitative insights using Gemini
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState
from src.models.analysis import QualitativeAnalysis
from src.nodes.researcher.tools import search_market_news


def researcher_node(state: AgentState) -> dict:
    """
    Researcher node function.
    
    This function:
    1. Searches market news using Tavily
    2. Analyzes SEC 10-K text (MD&A section)
    3. Synthesizes qualitative insights using Gemini
    
    Returns:
        dict: Updated state with qualitative_analysis (QualitativeAnalysis) or error
    """
    ticker = state['ticker']
    print(f"\n🔍 [Node C: Researcher] 正在分析 {ticker} 的基本面與情緒...")
    
    # 1. 獲取外部信息 (News)
    news_context = search_market_news(ticker)
    
    # 2. 獲取內部信息 (SEC Text)
    # 我們利用 State 中已經保存的 10-K 文本 (由 Node A 下載)
    sec_text = state.get("sec_text_chunk", "")[:50000]  # 限制長度以免過長，雖 Gemini 可吃 1M
    
    # 3. 獲取財務指標 (Node B 的產出)
    metrics = state.get("valuation_metrics")
    metrics_context = f"P/E: {metrics.pe_ratio}, Status: {metrics.valuation_status}" if metrics else "N/A"
    
    # 4. 調用 Gemini 進行綜合分析
    print("🤖 調用 Gemini 綜合分析 (News + SEC + Financials)...")
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            temperature=0.3  # 稍微增加一點創造力以進行總結
        )
        
        structured_llm = llm.with_structured_output(QualitativeAnalysis)
        
        prompt = f"""
你是一位華爾街資深權益分析師。請根據提供的數據，對 {ticker} 進行深度定性分析。

【輸入數據】

1. 估值指標: {metrics_context}

2. 最新市場新聞:

{news_context}

3. SEC 10-K 財報片段 (MD&A):

{sec_text}

【任務】

請綜合以上信息，生成一份分析報告。特別要注意：

- 解釋為什麼該公司處於 {metrics.valuation_status if metrics else 'Unknown'} 狀態？(例如：是因為高增長預期導致的高 P/E 嗎？)

- 從新聞中提取分析師觀點。

- 從財報中提取管理層對未來的展望。

- 識別關鍵增長驅動力和主要風險。
"""
        
        result = structured_llm.invoke(prompt)
        print(f"💡 分析完成: Sentiment={result.market_sentiment}")
        
        return {
            "qualitative_analysis": result,
            "error": None
        }
        
    except Exception as e:
        print(f"❌ Researcher Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "research_failed"}
