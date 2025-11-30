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
            model="gemini-2.5-flash-lite",
            temperature=0.7  # 增加創造力，讓文章更自然
        )
        
        prompt = f"""
你是一位頂級投資銀行的首席分析師。請根據以下數據為 {ticker} 撰寫一份專業的投資研究報告 (Markdown 格式)。

【數據源】

{data_context}

【報告結構要求】

# Investment Research Report: {ticker}

## 1. Investment Thesis (核心論點)

*這裡放置 researcher 的 investment_thesis，用粗體標出最核心的邏輯。*

**核心論點：** {analysis.investment_thesis if analysis and hasattr(analysis, 'investment_thesis') else (analysis.summary if analysis else 'N/A')}

---

## 2. Valuation & Financials (估值與財務)

### 2.1 估值模型 ({state.get('valuation_strategy', 'general_dcf')})

- **目標價:** ${val.dcf_value:.2f} (Upside: {val.dcf_upside:.2f}%)
- **評級:** **{val.valuation_status}**
- **解讀:** {analysis.valuation_commentary if analysis and hasattr(analysis, 'valuation_commentary') else 'N/A'}

*這裡是關鍵，解釋為什麼模型算出這個數字，以及這個數字是否合理。*

### 2.2 關鍵財務指標

- 當前股價: ${val.current_price:.2f}
- 市值: ${val.market_cap:.2f}M
- P/E 比率: {val.pe_ratio:.2f}x
- 淨利率: {val.net_profit_margin:.2f}%

{f"### 2.3 數據差異分析\n\n{discrepancy_context}\n\n引用 Researcher 找到的原因（例如：一次性費用、非經常性項目、網絡攻擊成本等）。如果 Researcher 的分析中提到了具體事件，請詳細說明。" if has_data_discrepancy else ""}

---

## 3. Key Catalysts & Risks (催化劑與風險)

### 3.1 即將到來的催化劑

{chr(10).join(f"- {catalyst}" for catalyst in (analysis.catalysts if analysis and hasattr(analysis, 'catalysts') else [])) if analysis and hasattr(analysis, 'catalysts') and analysis.catalysts else "- 無重大催化劑識別"}

### 3.2 主要下行風險

{analysis.risk_assessment if analysis and hasattr(analysis, 'risk_assessment') else (chr(10).join(f"- {risk}" for risk in (analysis.top_risks if analysis else [])) if analysis and analysis.top_risks else "- 無重大風險識別")}

---

## 4. Strategic Analysis (戰略分析)

- **市場情緒:** {analysis.market_sentiment if analysis else 'N/A'}
- **增長驅動力:** {chr(10).join(f"  - {driver}" for driver in (analysis.key_growth_drivers if analysis else [])) if analysis and analysis.key_growth_drivers else "  - N/A"}
- **管理層語調:** {analysis.management_tone if analysis else 'N/A'}

---

## 5. Conclusion (結論)

基於以上分析，總結投資建議和核心邏輯。確保與 Investment Thesis 保持一致。

請確保語氣專業、客觀，數據引用準確。使用繁體中文撰寫。報告應該有觀點、有故事、有靈魂，而不僅僅是數據堆砌。
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
