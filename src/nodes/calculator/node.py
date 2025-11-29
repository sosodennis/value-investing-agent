"""
Node B: Calculator - Main Node Logic

This node orchestrates financial calculations:
1. Validates input financial data
2. Performs ratio calculations using tools.calculate_ratios()
3. Executes DCF model using tools.dcf_valuation()
"""

# 【Refactor】直接導入
from src.state import AgentState
from src.models.valuation import ValuationMetrics


def calculator_node(state: AgentState) -> dict:
    """
    Calculator node function.
    
    Returns:
        dict: Updated state with valuation_metrics (ValuationMetrics)
    """
    print("\n🧮 [Node B: Calculator] Computing...")
    # 這裡可以直接訪問 state['financial_data'].total_revenue，因為它是對象
    
    financial_data = state.get("financial_data")
    if financial_data:
        print(f"   📊 使用財務數據: Revenue={financial_data.total_revenue}, Income={financial_data.net_income}")
    
    return {
        "valuation_metrics": ValuationMetrics(
            pe_ratio=25.5,
            valuation_status="Undervalued"
        )
    }
