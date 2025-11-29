"""
Node A: Data Miner - Main Node Logic

This node orchestrates the data mining process:
1. Downloads SEC filings using tools.download_filing()
2. Cleans HTML to Markdown using tools.clean_html()
3. Extracts structured data using Gemini 1.5 Flash (leverages long context window)
"""

import random
# 【Refactor】現在可以直接導入 State，不會報錯了
from src.state import AgentState
# 【Refactor】從 models 導入數據類
from src.models.financial import FinancialStatements


def data_miner_node(state: AgentState) -> dict:
    """
    Data Miner node function.
    
    Returns:
        dict: Updated state with financial_data (FinancialStatements) or error
    """
    print(f"\n⛏️  [Node A: Miner] Processing {state['ticker']} ...")
    
    # 1. 回環測試：檢查是否有人工注入的數據
    if state.get("sec_text_chunk"):
        print("✅ 檢測到人工數據，直接封裝對象...")
        # 這裡我們簡單解析一下字符串，實際會用 LLM
        return {
            "financial_data": FinancialStatements(
                fiscal_year="2024",
                total_revenue=99999,
                net_income=50000,
                source="Refactored Clean Code"
            ),
            "error": None
        }
    
    # 2. 模擬自動下載
    print("☁️  嘗試自動下載數據...")
    is_success = random.choice([True, False])  # 50% 失敗率
    
    if is_success:
        print("🎉 自動下載成功！")
        return {
            "sec_text_chunk": "Raw HTML content...",
            # 返回強類型對象
            "financial_data": FinancialStatements(
                fiscal_year="2023",
                total_revenue=10000,
                net_income=2000,
                source="Auto Download"
            ),
            "error": None
        }
    else:
        print("❌ 下載失敗 (模擬)。請求人工支援...")
        # 失敗時：不返回 financial_data，只返回 error
        return {
            "error": "download_failed"
        }
