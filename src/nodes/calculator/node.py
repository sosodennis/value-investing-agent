"""
Node B: Calculator - Main Node Logic

This node orchestrates financial calculations:
1. Validates input financial data
2. Fetches market data using yfinance
3. Performs ratio calculations using tools.calculate_metrics()
"""

from src.state import AgentState
from src.models.valuation import ValuationMetrics
from src.nodes.calculator.tools import get_market_data, calculate_metrics


def calculator_node(state: AgentState) -> dict:
    """
    Calculator node function.
    
    This function:
    1. Gets financial data from Node A
    2. Fetches market data from yfinance
    3. Calculates valuation metrics
    4. Returns ValuationMetrics Pydantic object
    
    Returns:
        dict: Updated state with valuation_metrics (ValuationMetrics) or error
    """
    print(f"\n🧮 [Node B: Calculator] 正在計算 {state['ticker']} 的估值指標...")
    
    # 1. 從 State 獲取 Node A 的產出
    financial_obj = state.get("financial_data")
    if not financial_obj:
        print("❌ 錯誤：找不到財務數據，無法計算。")
        return {"error": "missing_financial_data"}
    
    # 轉為字典方便處理
    financials = financial_obj.model_dump()
    
    # 2. 調用工具獲取市場數據 (yfinance)
    market_data = get_market_data(state["ticker"])
    if not market_data:
        return {"error": "market_data_fetch_failed"}
    
    print(f"📈 [Calculator] 現價: ${market_data['price']:.2f}")
    
    # 3. 執行計算
    try:
        metrics_dict = calculate_metrics(financials, market_data)
        
        # 4. 封裝為 Pydantic 對象
        metrics_obj = ValuationMetrics(**metrics_dict)
        
        print(f"🧮 [Calculator] 計算完成: P/E={metrics_obj.pe_ratio}, Margin={metrics_obj.net_profit_margin}%")
        
        return {
            "valuation_metrics": metrics_obj,
            "error": None
        }
    except Exception as e:
        print(f"❌ 計算錯誤: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "calculation_failed"}
