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
    tasks = state.get("investigation_tasks", [])
    
    print(f"\n🔍 [Node C: Researcher] 正在分析 {ticker} 的基本面與情緒...")
    print(f"📋 [Investigation] 待調查的異常點: {len(tasks)} 個")
    
    # 1. 構建搜索查詢
    # 基礎查詢
    queries = [f"{ticker} stock analyst rating and risks 2025"]
    
    # [Fix] 加入來自 Calculator 的定向查詢
    if tasks:
        print(f"🕵️‍♀️ [Deep Dive] 檢測到異常，追加定向搜索: {tasks}")
        queries.extend(tasks)
    
    # 2. 執行搜索 (循環調用 search_market_news)
    news_context = ""
    for q in queries:
        result = search_market_news(q)  # 現在接受任意查詢字符串
        news_context += f"\n=== Search: {q} ===\n{result}\n"
    
    # 2. 獲取內部信息 (SEC Text)
    # 我們利用 State 中已經保存的 10-K 文本 (由 Node A 下載)
    sec_text = state.get("sec_text_chunk", "")[:50000]  # 限制長度以免過長，雖 Gemini 可吃 1M
    
    # 3. 獲取財務指標 (Node B 的產出)
    metrics = state.get("valuation_metrics")
    # 構建更詳細的指標上下文
    if metrics:
        metrics_context = f"""
- 估值策略: {state.get('valuation_strategy', 'N/A')}
- 估值狀態: {metrics.valuation_status}
- 目標價: ${metrics.dcf_value:.2f} (Upside: {metrics.dcf_upside:.2f}%)
- P/E 比率: {metrics.pe_ratio:.2f}x
- 淨利率: {metrics.net_profit_margin:.2f}%
- 市值: ${metrics.market_cap:.2f}M
- 當前股價: ${metrics.current_price:.2f}
- P/E 趨勢: {metrics.pe_trend_insight}
"""
    else:
        metrics_context = "N/A"
    
    # 4. 調用 Gemini 進行綜合分析
    print("🤖 調用 Gemini 綜合分析 (News + SEC + Financials)...")
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.3  # 稍微增加一點創造力以進行總結
        )
        
        structured_llm = llm.with_structured_output(QualitativeAnalysis)
        special_instruction_block = ""
    
        if tasks:
            task_list_str = "\n".join([f"- {task}" for task in tasks])
            special_instruction_block = f"""
    【特別指令 (來自量化分析組)】
    上游計算節點發現了以下數據異常，請務必根據搜索結果給出解釋：
    {task_list_str}

    請重點調查上述問題，請在報告中專門開闢章節說明。
    """
        prompt = f"""
你是一位華爾街頂級對沖基金的投資總監。你需要根據 Quantitative (量化) 和 Qualitative (定性) 數據，構建一個令人信服的投資論點。

【量化數據 (Calculator Output)】

- 策略: {state.get('valuation_strategy', 'general_dcf')}
- 估值狀態: {metrics.valuation_status if metrics else 'Unknown'}
- 核心指標: {metrics_context}
- 數據異常: {chr(10).join(f"- {task}" for task in tasks) if tasks else "無"}

【定性信息 (News & SEC)】

1. 最新市場新聞:
{news_context}

2. SEC 10-K 財報片段 (MD&A):
{sec_text}

{special_instruction_block}

【任務要求】

1. **Investment Thesis (投資論點):** 
   不要只羅列事實。要把點連成線，構建一個完整的投資故事。
   例如："雖然營收放緩，但利潤率因裁員而提升，且 DCF 顯示股價已反映了悲觀預期，因此是反轉機會。"
   或者："儘管 P/E 高達 35 倍，但考慮到 Rule of 40 分數高達 50+，且新聞顯示其 AI 產品留存率極高，我們認為市場給予的高溢價是合理的。"
   
2. **Valuation Commentary (估值解讀):** 
   必須解釋為什麼估值模型得出這個結果，以及這個結果是否合理。
   - 如果 P/E 很高，是因為高增長 (PEG < 1) 嗎？還是因為炒作？
   - 如果是 SaaS，Rule of 40 分數是否支撐了高 EV/Sales？
   - 如果是 REITs，P/FFO 是否反映了利率環境和資產質量？
   - 如果是銀行，低 P/B 是否反映了壞帳風險？
   - 如果 DCF 顯示高估，但市場仍在買入，背後的原因是什麼？

3. **Catalysts (催化劑):** 
   接下來 6-12 個月有什麼大事可能推動股價？(例如：財報發布、產品發布、監管決策、併購傳聞)

4. **Risk Assessment (風險評估):** 
   詳細分析主要下行風險，不僅僅是列舉，要說明這些風險如何影響投資論點。

5. **Market Sentiment, Growth Drivers, Management Tone:** 
   保持原有分析，但要在 Investment Thesis 中整合這些信息。

請生成深度分析結果，確保 Investment Thesis 和 Valuation Commentary 能夠將量化指標與定性因素有機結合。
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
