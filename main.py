"""
AI Equity Analyst - Main Entry Point

This is the application entry point for the AI Equity Analyst Agent.
The main function will initialize the LangGraph workflow and execute the analysis pipeline.
"""

from dotenv import load_dotenv
from src.graph import build_graph

load_dotenv()


def main():
    """Main execution function."""
    print("🚀 啟動 AI Equity Analyst (Sprint 2 - Real Data Miner)...")
    app = build_graph()
    config = {"configurable": {"thread_id": "test_sprint2"}}
    
    # 使用真實股票代碼進行測試（確保有 10-K 的大公司）
    ticker = "NET"  # 可以改為 TSLA, MSFT, GOOGL 等
    print(f"\n📊 開始分析流程 - Ticker: {ticker}...")
    for event in app.stream({"ticker": ticker}, config=config):
        for node_name, node_output in event.items():
            print(f"   ✓ {node_name} 完成")
    
    # 檢查暫停
    snapshot = app.get_state(config)
    if snapshot.next and snapshot.next[0] == "human_help":
        print("\n🛑 需要人工介入！")
        choice = input(">> 輸入 'y' 模擬上傳數據: ")
        
        if choice == 'y':
            print("📤 注入數據...")
            app.update_state(config, {
                "sec_text_chunk": "User Provided Data",
                "error": None
            })
            
            print("▶️ 恢復運行...")
            for event in app.stream(None, config=config):
                for node_name, node_output in event.items():
                    print(f"   ✓ {node_name} 完成")
                    if "writer" in event:
                        print(f"\n📄 最終報告:\n{event['writer']['final_report']}")
        else:
            print("❌ 未提供數據，流程終止")
    else:
        # 如果沒有中斷，直接顯示最終報告
        final_state = app.get_state(config)
        if final_state.values.get("final_report"):
            print(f"\n📄 最終報告:\n{final_state.values['final_report']}")


if __name__ == "__main__":
    main()
