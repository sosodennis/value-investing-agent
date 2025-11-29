"""
Node A: Data Miner - Main Node Logic

This node orchestrates the data mining process:
1. Downloads SEC filings using tools.download_filing()
2. Cleans HTML to Markdown using tools.clean_html()
3. Extracts structured data using Gemini (leverages long context window)
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState
from src.models.financial import FinancialStatements
from src.nodes.data_miner.tools import fetch_10k_text


def data_miner_node(state: AgentState) -> dict:
    """
    Data Miner node function.
    
    This function:
    1. Checks for manually injected data or cached data
    2. Downloads 10-K from SEC if needed
    3. Uses Gemini to extract structured financial data
    
    Returns:
        dict: Updated state with financial_data (FinancialStatements) or error
    """
    ticker = state['ticker']
    print(f"\n⛏️  [Node A: Miner] 正在處理 {ticker} ...")
    
    # 1. 檢查人工/緩存數據
    if state.get("sec_text_chunk"):
        print("✅ 使用現有文本數據...")
        raw_text = state["sec_text_chunk"]
    else:
        # 2. 自動下載
        print("☁️  正在調用 SEC 下載工具...")
        user_agent = os.getenv("SEC_API_USER_AGENT")
        if not user_agent:
            return {"error": "Missing SEC_API_USER_AGENT in .env"}
        
        try:
            # 調用剛寫好的工具
            raw_text = fetch_10k_text(ticker, user_agent)
            if not raw_text:
                raise ValueError("Downloaded text is empty")
        except Exception as e:
            print(f"❌ 下載失敗: {e}")
            return {"error": "download_failed"}
    
    # 3. Gemini 結構化提取
    print("🤖 調用 Gemini 進行提取...")
    
    try:
        # 初始化模型 (確保 .env 有 GOOGLE_API_KEY)
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            temperature=0
        )
        
        # 綁定 Pydantic (這就是 Data Class 的威力)
        structured_llm = llm.with_structured_output(FinancialStatements)
        
        # 截取文本前 30000 字符（Gemini 可以处理更多，但为了稳定性）
        text_snippet = raw_text[:30000] if len(raw_text) > 30000 else raw_text
        
        prompt = f"""
你是一位專業的財務會計。請閱讀以下 SEC 10-K 財報片段，並提取關鍵財務數據。

要求：
1. 尋找「Consolidated Statements of Operations」或類似的損益表。
2. 提取**最新一個財年** (Current Fiscal Year) 的數據。
3. 金額單位通常為百萬 (Millions)，請直接提取表格中的數值（不需要乘 1000000）。
4. 如果找不到某個字段，請盡力估算或填 0。
5. fiscal_year 請提取財年結束日期（例如 "2023" 或 "2023-09-30"）。
6. source 填寫 "Auto Download"。

財報文本片段:

{text_snippet}

... (內容過長省略)
"""
        
        # 執行推理
        result = structured_llm.invoke(prompt)
        print(f"📊 提取成功: {result}")
        
        return {
            "financial_data": result,  # 返回 Pydantic 對象
            "sec_text_chunk": raw_text,  # 保存文本以備後用
            "error": None
        }
        
    except Exception as e:
        print(f"❌ Gemini 提取失敗: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "extraction_failed"}
