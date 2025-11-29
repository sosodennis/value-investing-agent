"""
Human-in-the-Loop Node - Main Node Logic

This node handles human intervention:
1. Displays current state and error information
2. Accepts manual data injection (e.g., local SEC filing)
3. Updates state based on human input
4. Routes back to appropriate node based on correction type
"""

from src.state import AgentState


def request_human_help_node(state: AgentState) -> dict:
    """
    Human-in-the-loop node function.
    
    This node is called when the system needs human intervention.
    It displays the current error and waits for user input.
    
    Returns:
        dict: Empty dict (state updates happen via update_state in main.py)
    """
    print("\n🆘 [Node: Human Help] 等待數據注入...")
    
    error = state.get("error")
    ticker = state.get("ticker", "UNKNOWN")
    
    if error:
        print(f"   ⚠️  錯誤類型: {error}")
        print(f"   📊 股票代碼: {ticker}")
        print("   💡 提示: 請通過 update_state 注入 sec_text_chunk 數據")
    
    return {}
