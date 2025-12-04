"""
Node A: Data Miner - Main Node Logic (Fault Tolerant)

Features:
1. Auto-Rescue / Robust Error Handling.
2. Prioritizes Basic Data extraction.
3. Returns partial data to allow Merger node to fill gaps.
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState
from src.models.financial import FinancialStatements
from src.nodes.data_miner.tools import fetch_10k_text
from src.strategies.registry import StrategyRegistry
from src.consts import ValuationStrategyType

def data_miner_node(state: AgentState) -> dict:
    """
    Data Miner node function.
    """
    ticker = state['ticker']
    print(f"\n⛏️  [Node A: Miner] 正在處理 {ticker} ...")
    
    raw_text = None
    download_error = None

    # 1. 獲取文本數據 (檢查緩存 -> 下載)
    if state.get("sec_text_chunk"):
        print("✅ 使用現有文本數據...")
        raw_text = state["sec_text_chunk"]
    else:
        print("☁️  正在調用 SEC 下載工具...")
        user_agent = os.getenv("SEC_API_USER_AGENT")
        
        try:
            if not user_agent:
                raise ValueError("Missing SEC_API_USER_AGENT")
            
            # 嘗試下載 (無重試，失敗就標記錯誤但繼續流程)
            raw_text = fetch_10k_text(ticker, user_agent)
            
            if not raw_text:
                download_error = "download_failed_empty"
                print(f"❌ 下載失敗: 找不到 {ticker} 的 10-K。")
        except Exception as e:
            download_error = f"download_exception: {str(e)}"
            print(f"❌ 下載異常: {e}")

    # 2. 如果沒有文本，我們仍然創建一個空的 FinancialStatements 對象
    # 這樣 Merger 節點可以接收它，並檢查 User 是否有上傳數據來填補
    if not raw_text:
        print("⚠️ 無法獲取 SEC 文本，將返回空數據結構等待 User Merge。")
        return {
            "sec_data": FinancialStatements(source="Missing (Download Failed)").model_dump(),
            "error": download_error # 標記錯誤，Router 可以決定是否要去 Human Help
        }
    
    # 3. Gemini 結構化提取 (有文本的情況)
    print("🤖 調用 Gemini 進行提取...")
    
    try:
        current_strategy_id = state.get("valuation_strategy", ValuationStrategyType.GENERAL_DCF.value)
        strategy_config = StrategyRegistry.get_strategy(current_strategy_id)
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
        structured_llm = llm.with_structured_output(FinancialStatements)
        
        text_snippet = raw_text[:120000] if len(raw_text) > 120000 else raw_text
        
        prompt = f"""
你是一位專業的財務會計。請閱讀以下 SEC 10-K 財報片段，並提取關鍵財務數據。

【提取優先級】
1. **基礎數據 (必要)**: 請務必提取 'total_revenue' 和 'net_income'。如果找不到，請仔細檢查 Income Statement。
2. **進階數據 (盡力而為)**: 嘗試提取 'operating_cash_flow' 和 'capital_expenditures'。如果真的找不到，該欄位可以留空 (null)。

【提取目標與定義】
{strategy_config.data_extraction_prompt}

【通用規則】
- 單位通常為百萬 (Millions)，請直接提取看到的數字。
- Capital Expenditures 通常為負數，請提取其絕對值。
- Source 填寫 "SEC 10-K (Auto)".

【財報片段】:
{text_snippet}
"""
        
        # 執行提取
        result = structured_llm.invoke(prompt)
        
        # 簡單檢查基礎數據
        if result.has_basic_data:
            print(f"📊 基礎數據提取成功! Rev: {result.total_revenue}, NI: {result.net_income}")
        else:
            print(f"⚠️ 警告: 基礎數據缺失 (Rev: {result.total_revenue}, NI: {result.net_income})")

        return {
            "sec_data": result.model_dump(),
            "sec_text_chunk": raw_text,
            "error": None # 清除之前的錯誤 (如果有)
        }
        
    except Exception as e:
        print(f"❌ Gemini 提取異常: {e}")
        # 發生異常時，返回部分數據或空數據，不要讓程序崩潰
        return {
            "sec_data": FinancialStatements(source="Extraction Failed").model_dump(),
            "error": f"extraction_failed: {str(e)}"
        }