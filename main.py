"""
AI Equity Analyst - Interactive CLI Entry Point (LangGraph v1.0 Style)

Updates:
1. Uses `Command(resume=...)` for handling interrupts (v1.0 standard).
2. Explicitly handles interrupt values if provided by nodes using `interrupt()`.
3. Maintains backward compatibility with `interrupt_before` via node name checks.
"""

import sys
from typing import Any, Optional, Dict

from dotenv import load_dotenv
from langgraph.types import Command  # v1.0 Feature

from src.graph import build_graph
from src.consts import NodeConsts, FeedbackConsts

# Load environment variables
load_dotenv()

def get_interrupt_value(snapshot: Any) -> Any:
    """
    Helper to extract interrupt value from the snapshot.
    Supports both v1.0 explicit interrupts and legacy interrupt_before.
    """
    # 1. Check for explicit v1.0 interrupt value
    # When using interrupt("Please clarify..."), the value is stored here.
    if hasattr(snapshot, "tasks") and snapshot.tasks:
        for task in snapshot.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                return task.interrupts[0].value
    
    # 2. Fallback: No explicit value (legacy interrupt_before)
    return None

def main():
    print("🚀 啟動 AI Equity Analyst V3 (LangGraph v1.0 Driver)...")
    
    # 1. Initialize Graph
    app = build_graph()
    
    # Configure Thread ID for persistence
    thread_id = "test_run_v3_modern"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 2. Initial Input
    initial_ticker = input(">> 請輸入股票代碼 (例如 MSFT): ") or "MSFT"
    print(f"\n📊 開始分析流程 - Ticker: {initial_ticker}...")
    
    # Start the graph execution
    # For the first run, we pass the input dictionary.
    current_input = {"ticker": initial_ticker}
    
    # 3. Interactive Loop (The Driver)
    while True:
        try:
            # Execute until the next interrupt or end
            # Using stream(None) or Command(...) is handled by current_input variable
            for event in app.stream(current_input, config=config):
                for node_name, node_output in event.items():
                    print(f"   ✓ {node_name} 執行完畢")
                    if node_name == NodeConsts.WRITER and "report_content" in node_output:
                        print(f"     [預覽] 報告片段: {str(node_output['report_content'])[:50]}...")
                        
        except Exception as e:
            print(f"❌ 運行時發生錯誤: {e}")
            break

        # 4. Check State (Snapshot)
        snapshot = app.get_state(config)
        
        # If no next steps, the graph has finished
        if not snapshot.next:
            print("\n🎉 流程圓滿結束！")
            final_report = snapshot.values.get("report_content")
            if final_report:
                print("\n📄 最終報告全文:\n" + "="*40 + "\n" + final_report + "\n" + "="*40)
            break

        # 5. Handle Interrupts
        # Identify where we are paused
        next_node = snapshot.next[0]
        interrupt_val = get_interrupt_value(snapshot)
        
        # Display interrupt context (if node provided one via interrupt("message"))
        print(f"\n🛑 系統暫停，等待人類介入。")
        print(f"   📍 當前節點: [{next_node}]")
        if interrupt_val:
            print(f"   📢 系統訊息: {interrupt_val}")

        # --- Scenario A: Clarification (Phase 1) ---
        if next_node == NodeConsts.CLARIFICATION_REQUEST:
            if not interrupt_val: # Legacy/Fallback message
                print("❓ Agent 對您的指令有疑問 (歧義檢測)。")
                error_msg = snapshot.values.get("error", "")
                if error_msg: print(f"   提示: {error_msg}")

            user_response = input(">> 請澄清您的意圖 (例如 '我是指美股 MSFT'): ")
            
            # v1.0 Style: Resume by updating state via Command (if node supports it) 
            # OR standard update_state + resume.
            # Here we use update_state to be safe with existing nodes, 
            # but prepare for Command style resume.
            app.update_state(config, {"clarification_history": [user_response]})
            
            # Resume execution
            # In v1.0 with explicit interrupt(), we would use: current_input = Command(resume=user_response)
            # Since we assume mixed compatibility, we use None to resume from checkpoint
            current_input = None 
            print("✅ 狀態已更新，繼續執行...")

        # --- Scenario B: Data Conflict (Phase 3) ---
        elif next_node == NodeConsts.DATA_CONFLICT_RESOLVER:
            conflict_info = snapshot.values.get("conflict_details", "未知衝突")
            print(f"⚖️ 發現數據衝突: {conflict_info}")
            print("選項: [1] 使用 SEC 數據  [2] 使用 User 數據  [3] 手動輸入數值")
            choice = input(">> 請輸入選項 (1/2/3): ")
            
            updates = {}
            if choice == "2":
                print("👉 選擇使用 User 數據。")
                updates = {
                    "has_data_conflict": False,
                    "merged_financials": snapshot.values.get("user_data")
                }
            elif choice == "3":
                manual_rev = input(">> 請輸入正確的營收數值: ")
                current_financials = snapshot.values.get("merged_financials", {})
                current_financials['revenue'] = float(manual_rev)
                updates = {
                    "has_data_conflict": False,
                    "merged_financials": current_financials
                }
            else:
                print("👉 預設使用 SEC 數據。")
                updates = {"has_data_conflict": False}
            
            app.update_state(config, updates)
            current_input = None
            print("✅ 衝突已解決，繼續執行...")

        # --- Scenario C: Feedback (Phase 5) ---
        elif next_node == NodeConsts.HUMAN_FEEDBACK_MANAGER:
            print("📝 初稿已生成，請審閱。")
            print("選項: [A] 批准 (Approve)  [P] 修改參數 (Param)  [N] 修改敘事 (Narrative)")
            fb_choice = input(">> 請輸入指令: ").upper()
            
            updates = {}
            if fb_choice == "A":
                updates = {"feedback_type": FeedbackConsts.APPROVE}
                print("🎉 批准通過！")
            elif fb_choice == "P":
                comment = input(">> 參數修改建議: ")
                updates = {
                    "feedback_type": FeedbackConsts.PARAMETER_UPDATE,
                    "human_feedback": [comment]
                }
                print("🔄 準備回滾至 Calculator...")
            elif fb_choice == "N":
                comment = input(">> 敘事修改建議: ")
                updates = {
                    "feedback_type": FeedbackConsts.NARRATIVE_TWEAK,
                    "human_feedback": [comment]
                }
                print("🔄 準備回滾至 Writer...")
            else:
                updates = {"feedback_type": FeedbackConsts.APPROVE}
            
            app.update_state(config, updates)
            
            # v1.0 Modern Resume Pattern (Example for future migration):
            # If the node used `value = interrupt()`, we would do:
            # current_input = Command(resume={"action": fb_choice, "comment": comment})
            # But for now, we rely on state updates.
            current_input = None

        # --- Scenario D: Miner Error ---
        elif next_node == NodeConsts.HUMAN_HELP:
            print("⚠️ Miner 遇到錯誤。")
            retry = input(">> 是否重試? (y/n): ")
            if retry.lower() == 'y':
                app.update_state(config, {"error": None})
            else:
                print("🛑 用戶選擇終止流程。")
                break
            current_input = None

        # --- Unexpected Interrupt ---
        else:
            print(f"⚠️ 停在了未預期的節點: {next_node}")
            # Try to read raw interrupt value if any
            if interrupt_val:
                print(f"   Value: {interrupt_val}")
            
            # Fallback resume
            user_in = input(">> 按 Enter 嘗試繼續 (或輸入 resume value): ")
            if user_in:
                # Experimental: Try to resume with Command if user types something
                current_input = Command(resume=user_in)
            else:
                current_input = None

if __name__ == "__main__":
    main()