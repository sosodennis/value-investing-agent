"""
Node A: Profiler - Strategic Company Profiling

This node:
1. Fetches company basic information from yfinance
2. Uses LLM to intelligently select the best valuation strategy
3. Updates state with company profile and strategy decision
"""

import yfinance as yf
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from src.state import AgentState
from src.consts import ValuationStrategyType
from src.strategies.registry import StrategyRegistry


class StrategyDecision(BaseModel):
    """LLM 的決策結果結構"""
    strategy: str = Field(
        description=f"Selected strategy code. Must be one of: {', '.join([s.value for s in ValuationStrategyType])}"
    )
    reasoning: str = Field(description="Brief reason why this strategy fits the company")


def _build_company_context(ticker: str, info: dict) -> str:
    """
    優雅地構建公司上下文信息。
    
    過濾掉 None 或 空值，只保留有效信息。
    使用條件式構建，避免在 Prompt 中出現 "None" 或空字符串。
    
    Args:
        ticker: Stock ticker symbol
        info: yfinance info dictionary
        
    Returns:
        str: Clean, formatted company context string
    """
    # 使用列表收集有效片段
    context_parts = [f"Ticker: {ticker}"]
    
    # 1. 基礎信息 (使用 Walrus Operator 簡化條件判斷)
    if name := info.get("longName"):
        context_parts.append(f"Company: {name}")
        
    if sector := info.get("sector"):
        context_parts.append(f"Sector: {sector}")
        
    if industry := info.get("industry"):
        context_parts.append(f"Industry: {industry}")
        
    # 2. 業務描述 (截取前 500 字，避免過長)
    if summary := info.get("longBusinessSummary"):
        # 清洗換行符
        clean_summary = summary.replace("\n", " ").strip()
        if clean_summary:  # 確保不是空字符串
            context_parts.append(f"Business Summary: {clean_summary[:500]}...")
    
    # 3. 關鍵財務特徵 (輔助判斷)
    # 例如：如果有 FFO 數據，可能是 REITs；如果有 Tier 1 Capital，可能是銀行
    # 這裡可以根據 yfinance 的 availability 動態添加
    
    # 4. 公司類型標識 (如果有)
    if company_type := info.get("quoteType"):
        context_parts.append(f"Company Type: {company_type}")
    
    return "\n".join(context_parts)


def profiler_node(state: AgentState) -> dict:
    """
    Profiler node function.
    
    This function:
    1. Fetches company basic information from yfinance
    2. Builds clean company context (conditional construction)
    3. Uses LLM to intelligently select valuation strategy
    4. Updates state with profile information
    
    Returns:
        dict: Updated state with company profile and strategy decision
    """
    ticker = state["ticker"]
    print(f"\n🕵️ [Node A: Profiler] 正在分析 {ticker} 的戰略屬性...")
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 1. 優雅構建上下文 (Clean Context Construction)
        company_context = _build_company_context(ticker, info)
        
        print(f"📋 [Profile] Context Constructed:\n{company_context}")
        
        # 2. 調用 LLM 進行語義路由
        print(f"🤖 [Router] 調用 Gemini 判斷最佳估值模型...")
        
        # [Refactor] 動態獲取最新的策略定義
        strategy_definitions_str = StrategyRegistry.get_all_prompts_for_profiler()
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
        structured_llm = llm.with_structured_output(StrategyDecision)
        
        prompt = f"""
你是一位資深的投資架構師。請分析以下目標公司，並從知識庫中選擇最合適的估值策略。

【策略知識庫】

{strategy_definitions_str}

【目標公司信息】

{company_context}

任務：
1. 分析公司的業務模式和行業屬性。
2. 選擇最匹配的策略代碼 (必須是知識庫中定義的代碼)。
3. 如果無法確定或屬於標準行業，請回退選擇 '{ValuationStrategyType.GENERAL_DCF.value}'。
"""
        
        decision = structured_llm.invoke(prompt)
        
        print(f"🎯 [Router] 策略鎖定: {decision.strategy}")
        print(f"💡 [Reasoning] {decision.reasoning}")
        
        return {
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "valuation_strategy": decision.strategy,
            "strategy_reasoning": decision.reasoning,
            "error": None
        }
        
    except Exception as e:
        print(f"❌ Profiler Error: {e}")
        import traceback
        traceback.print_exc()
        # 發生錯誤時的安全回退
        return {
            "company_name": ticker,
            "sector": "Unknown",
            "industry": "Unknown",
            "valuation_strategy": ValuationStrategyType.GENERAL_DCF.value,
            "strategy_reasoning": "Fallback due to profiling error",
            "error": "profiling_failed"  # 標記錯誤但不中斷流程 (Soft Fail)
        }

