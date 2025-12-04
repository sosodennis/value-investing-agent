"""
Node: Clarification Request - Intent Clarification

This node acts as a checkpoint/anchor for Human-in-the-Loop interaction.
"""

from src.state import AgentState

def clarification_request_node(state: AgentState) -> dict:
    """
    Clarification Request node function.
    
    In the V3 architecture (Driver Pattern), the interaction happens OUTSIDE 
    the graph (in main.py). The driver updates the 'clarification_history' 
    directly before resuming.
    
    Therefore, when this node runs, its job is simply to:
    1. Acknowledge the new input found in the history.
    2. Pass control back to the Profiler to re-evaluate the intent.
    """
    print("--- CLARIFICATION REQUEST (HIL) ---")
    
    # [FIX] 正確讀取 AgentState 中定義的 clarification_history
    history = state.get("clarification_history", [])
    
    if history:
        latest_input = history[-1]
        print(f"✅ 用戶已提供澄清: '{latest_input}'")
        print("🔄 正在返回 Profiler 進行意圖解析...")
    else:
        print("⚠️ 警告: 恢復執行但未發現澄清輸入 (可能是狀態更新失敗)")
    
    # [Critical] 不要在此處返回 needs_clarification=False
    # 原因：Profiler 節點擁有 Context-Aware 解析邏輯。
    # 流程會流回 Profiler，由 Profiler 讀取 history -> 解析 -> 決定是否還有歧義。
    # 如果我們在這裡強制設為 False，可能會繞過 Profiler 的檢查。
    return {}