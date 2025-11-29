"""
Node C: Researcher - Main Node Logic

This node orchestrates deep research:
1. Searches market sentiment using Tavily API
2. Analyzes competitive landscape
3. Synthesizes qualitative insights using Gemini
"""

from src.state import AgentState


def researcher_node(state: AgentState) -> dict:
    """
    Researcher node function.
    
    Returns:
        dict: Updated state with qualitative_analysis
    """
    print("\n🔍 [Node C: Researcher] Conducting deep research...")
    
    ticker = state.get("ticker", "UNKNOWN")
    valuation_metrics = state.get("valuation_metrics")
    
    if valuation_metrics:
        print(f"   💡 基於估值指標: {valuation_metrics.valuation_status}")
    
    # Dummy 定性分析
    qualitative_analysis = f"""
    ## 市場分析報告 - {ticker}
    
    ### 市場情緒
    根據最新市場數據，{ticker} 目前處於相對低估狀態。
    
    ### 競爭格局
    行業競爭激烈，但公司具有明顯的競爭優勢。
    
    ### 風險因素
    需要關注宏觀經濟環境變化對公司業績的影響。
    """
    
    return {
        "qualitative_analysis": qualitative_analysis
    }
