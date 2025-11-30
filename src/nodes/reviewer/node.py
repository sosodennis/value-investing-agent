"""
Node D: Insight Reviewer - Sanity Check & Investigation Task Generator

This node:
1. Reviews calculation results from Calculator
2. Performs sanity checks (extreme valuations, data anomalies)
3. Generates investigation tasks for Researcher
"""

from src.state import AgentState


def reviewer_node(state: AgentState) -> dict:
    """
    Reviewer node function.
    
    This function:
    1. Reviews valuation metrics for anomalies
    2. Checks for extreme valuations (Upside > 100% or < -50%)
    3. Checks for normalized income discrepancies
    4. Generates investigation tasks for Researcher
    
    Returns:
        dict: Updated state with investigation_tasks or error
    """
    print(f"\n🧐 [Node D: Reviewer] 正在審查計算結果...")
    
    ticker = state["ticker"]
    metrics = state.get("valuation_metrics")
    financials = state.get("financial_data")
    
    if not metrics:
        print("⚠️ [Reviewer] 未找到估值指標，跳過審查")
        return {
            "investigation_tasks": [],
            "error": None
        }
    
    investigation_tasks = []
    
    # 1. 檢查標準化淨利差異 (NRI Check)
    # 如果使用了標準化數據，我們生成一個提示給 Researcher 去查原因
    if metrics.is_normalized:
        task = f"Investigate why {ticker} has significant Non-Recurring Items in recent earnings. What are the one-time charges or gains?"
        investigation_tasks.append(task)
        print(f"🚩 [Reviewer] 發現 NRI 調整，生成調查任務: {task}")
    
    # 2. 檢查估值 Upside 合理性 (Sanity Check)
    upside = metrics.dcf_upside
    
    if upside > 100:
        task = f"Why is {ticker} valuation upside > 100%? Check for distress signals, model mismatch, or extreme growth assumptions."
        investigation_tasks.append(task)
        print(f"🚩 [Reviewer] 發現超高 Upside ({upside:.1f}%)，生成調查任務: {task}")
    elif upside < -50:
        task = f"Why is {ticker} valuation downside < -50%? Check for declining fundamentals, competitive threats, or overly optimistic historical assumptions."
        investigation_tasks.append(task)
        print(f"🚩 [Reviewer] 發現超低 Downside ({upside:.1f}%)，生成調查任務: {task}")
    
    # 3. 檢查 P/E 極端值 (可選的額外檢查)
    if metrics.pe_ratio > 0:
        if metrics.pe_ratio > 50:
            print(f"💡 [Reviewer] 注意：P/E 比率較高 ({metrics.pe_ratio:.1f}x)，但這可能合理（高成長股）")
        elif metrics.pe_ratio < 5:
            print(f"💡 [Reviewer] 注意：P/E 比率較低 ({metrics.pe_ratio:.1f}x)，可能存在價值陷阱或衰退風險")
    
    # 4. 返回結果
    # 注意：我們不修改 metrics，只增加 tasks
    if investigation_tasks:
        print(f"📋 [Reviewer] 共生成 {len(investigation_tasks)} 個調查任務")
    else:
        print(f"✅ [Reviewer] 未發現異常，計算結果合理")
    
    return {
        "investigation_tasks": investigation_tasks,
        "error": None
    }

