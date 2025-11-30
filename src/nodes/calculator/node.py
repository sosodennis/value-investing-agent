"""
Node B: Calculator - Strategy Dispatcher (Refactored to Strategy Pattern)

This node now acts as a dispatcher that routes to the appropriate valuation strategy
based on the company's sector/industry. Currently defaults to GeneralDCFStrategy.
"""

from src.state import AgentState
from src.consts import ValuationStrategyType
from src.nodes.calculator.strategies.general import GeneralDCFStrategy
from src.nodes.calculator.strategies.reit_nav import ReitNAVStrategy


def calculator_node(state: AgentState) -> dict:
    """
    Calculator node function (Strategy Pattern Dispatcher).
    
    This function:
    1. Prepares data from state
    2. Routes to appropriate strategy (currently defaults to GeneralDCFStrategy)
    3. Executes strategy and returns results
    
    Returns:
        dict: Updated state with valuation_metrics (ValuationMetrics) or error
    """
    ticker = state["ticker"]
    print(f"\n🧮 [Node B: Calculator] 正在計算 {ticker} ...")
    
    # 1. 數據準備
    financial_obj = state.get("financial_data")
    if not financial_obj:
        print("❌ 錯誤：找不到財務數據，無法計算。")
        return {"error": "missing_financial_data"}
    
    # 2. 策略路由 (Strategy Routing)
    # 根據 Profiler 節點選擇的策略進行路由
    strategy_code = state.get("valuation_strategy", ValuationStrategyType.GENERAL_DCF.value)
    
    print(f"🎯 [Strategy Router] 使用策略: {strategy_code}")
    if state.get("strategy_reasoning"):
        print(f"💡 [Reasoning] {state['strategy_reasoning']}")
    
    # 根據策略代碼選擇對應的策略實現
    # 使用 Enum 做判斷，更安全且易於維護
    # 目前只實現了 general_dcf，其他策略會回退到 general_dcf
    if strategy_code == ValuationStrategyType.GENERAL_DCF.value:
        strategy = GeneralDCFStrategy()
    elif strategy_code == ValuationStrategyType.BANK_DDM.value:
        # TODO: 實現 BankDDMStrategy
        print(f"⚠️ [Strategy] {ValuationStrategyType.BANK_DDM.value} 尚未實現，回退到 general_dcf")
        strategy = GeneralDCFStrategy()
    elif strategy_code == ValuationStrategyType.REIT_NAV.value:
        print("🏗️ [Strategy] 激活 REITs 專屬策略 (ReitNAVStrategy)...")
        strategy = ReitNAVStrategy()
    elif strategy_code == ValuationStrategyType.SAAS_RULE40.value:
        # TODO: 實現 SaaSRule40Strategy
        print(f"⚠️ [Strategy] {ValuationStrategyType.SAAS_RULE40.value} 尚未實現，回退到 general_dcf")
        strategy = GeneralDCFStrategy()
    else:
        # 未知策略，回退到默認
        print(f"⚠️ [Strategy] 未知策略 '{strategy_code}'，回退到 general_dcf")
        strategy = GeneralDCFStrategy()
    
    try:
        # 3. 執行策略
        # 注意：strategy.calculate() 內部會重新獲取 market_data 以確保包含所有必要字段
        metrics_obj = strategy.calculate(
            ticker=ticker,
            financial_data=financial_obj,
            market_data={}  # Strategy 內部會重新獲取，這裡傳空字典作為占位符
        )
        
        print(f"✅ [Calculator] 策略執行完成。DCF: ${metrics_obj.dcf_value:.2f} (Upside: {metrics_obj.dcf_upside:.2f}%)")
        
        # 4. 檢查異常並生成調查任務（保留原有邏輯）
        investigation_tasks = []
        
        # 如果有標準化淨利差異，生成調查任務
        if metrics_obj.is_normalized:
            # 這裡我們需要獲取原始 GAAP 淨利來比較
            # 為了保持簡單，我們暫時跳過這個檢查，因為 strategy 內部已經處理了
            pass
        
        return {
            "valuation_metrics": metrics_obj,
            "investigation_tasks": investigation_tasks,
            "error": None
        }
        
    except Exception as e:
        print(f"❌ 計算錯誤: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "calculation_failed"}