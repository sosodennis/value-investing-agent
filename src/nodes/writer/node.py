"""
Node D: Writer - Main Node Logic

This node generates the final equity research report:
1. Aggregates all structured and unstructured data
2. Structures the report using a professional template
3. Generates comprehensive Markdown report using Gemini
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.state import AgentState


def writer_node(state: AgentState) -> dict:
    """
    Writer node function.
    
    This function:
    1. Collects all analysis results
    2. Generates comprehensive investment report using Gemini
    
    Returns:
        dict: Updated state with final_report or error
    """
    print(f"\n✍️  [Node D: Writer] 正在撰寫 {state['ticker']} 最終報告...")
    
    # 收集所有素材
    ticker = state['ticker']
    fin = state.get('financial_data')
    val = state.get('valuation_metrics')
    analysis = state.get('qualitative_analysis')
    tasks = state.get('investigation_tasks', [])
    
    # 構建 Prompt Context
    # 這裡將 Pydantic 對象轉為字典或字符串
    data_context = f"""
1. Financials: {fin.model_dump() if fin else 'N/A'}
2. Valuation: {val.model_dump() if val else 'N/A'}
3. Qualitative Analysis: {analysis.model_dump() if analysis else 'N/A'}
4. Investigation Tasks: {tasks if tasks else 'None'}
"""
    
    # 檢查是否有數據異常需要解釋
    has_data_discrepancy = len(tasks) > 0 or (val and val.is_normalized and val.eps_normalized)
    discrepancy_context = ""
    if has_data_discrepancy:
        if val and val.is_normalized and val.eps_normalized:
            discrepancy_context = f"""
- 標準化 EPS: {val.eps_normalized:.2f}
- 使用標準化數據的原因: 排除非經常性項目以反映核心價值
"""
        if tasks:
            discrepancy_context += f"""
- 調查任務: {', '.join(tasks)}
- Researcher 已針對這些異常進行定向搜索，請引用其分析結果
"""
    
    try:
        # 寫作建議使用 Gemini Pro (如果可用) 以獲得更好的文筆
        # 如果沒有 Pro 權限，改回 gemini-2.0-flash-lite
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            temperature=0.7  # 增加創造力，讓文章更自然
        )
        
        prompt = f"""
你是一位頂級投資銀行的首席分析師。請根據以下數據為 {ticker} 撰寫一份專業的投資研究報告 (Markdown 格式)。

【數據源】

{data_context}

【報告結構要求】

# Investment Report: {ticker}

## 1. Executive Summary (執行摘要)

- 給出明確的投資評級 (基於估值狀態)。

- 用一句話總結核心論點。

## 2. Financial Highlights (財務亮點)

- 展示營收、淨利潤等關鍵數據。

- 評論 P/E {val.pe_ratio if val else 'N/A'} 倍數的合理性。

## 3. Data Discrepancy Analysis (數據差異分析)

{f"請詳細解釋以下數據異常：{discrepancy_context}引用 Researcher 找到的原因（例如：一次性費用、非經常性項目、網絡攻擊成本等）。如果 Researcher 的分析中提到了具體事件，請詳細說明。" if has_data_discrepancy else "Financials align with GAAP standards. No significant discrepancies detected."}

## 4. Strategic Analysis (戰略分析)

- 市場情緒: {analysis.market_sentiment if analysis else 'N/A'}

- 增長驅動力: (列點說明)

- 關鍵風險: (列點說明)

## 5. Conclusion (結論)

- 總結性建議。

請確保語氣專業、客觀，數據引用準確。使用繁體中文撰寫。
"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        return {
            "final_report": response.content,
            "error": None
        }
        
    except Exception as e:
        print(f"❌ Writer Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "writing_failed"}
