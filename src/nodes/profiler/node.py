"""
Node A: Profiler - Strategic Company Profiling (V3 Enhanced)

Features:
1. Auto-Rescue: Automatically retries with LLM fix if yfinance fails.
2. Dual-Listing Handling: Prompts user for ambiguous tickers (ADR vs Local).
3. Context-Aware Resolution: Uses full conversation history to resolve intent.
4. LangGraph v1.0 Compatibility: Returns clear state updates for the driver.
"""

import yfinance as yf
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import List, Optional

from src.state import AgentState
from src.consts import ValuationStrategyType
from src.strategies.registry import StrategyRegistry


# --- Pydantic Models ---

class StrategyDecision(BaseModel):
    """LLM 的決策結果結構 (用於策略路由)"""
    strategy: str = Field(
        description=f"Selected strategy code. Must be one of: {', '.join([s.value for s in ValuationStrategyType])}"
    )
    reasoning: str = Field(description="Brief reason why this strategy fits the company")


class TickerResolution(BaseModel):
    """[V3 New] 用戶澄清意圖的解析結果"""
    resolved_ticker: str = Field(
        description="The extracted valid stock ticker symbol. Return 'AMBIGUOUS' if multiple valid options exist but market is unspecified. Return 'UNKNOWN' if intent is unrecognizable."
    )
    reasoning: str = Field(description="Brief explanation. If AMBIGUOUS, list the available options (e.g., 'US: TSM, TW: 2330.TW').")


# --- Helper Functions ---

def _build_company_context(ticker: str, info: dict) -> str:
    """構建公司上下文信息"""
    context_parts = [f"Ticker: {ticker}"]
    
    if name := info.get("longName"):
        context_parts.append(f"Company: {name}")
    if sector := info.get("sector"):
        context_parts.append(f"Sector: {sector}")
    if industry := info.get("industry"):
        context_parts.append(f"Industry: {industry}")
    if summary := info.get("longBusinessSummary"):
        clean_summary = summary.replace("\n", " ").strip()
        if clean_summary:
            context_parts.append(f"Business Summary: {clean_summary[:500]}...")
    if company_type := info.get("quoteType"):
        context_parts.append(f"Company Type: {company_type}")
    
    return "\n".join(context_parts)


def _resolve_user_intent(original_ticker: str, clarification_history: List[str]) -> TickerResolution:
    """
    使用 LLM 解析用戶的自然語言澄清 (Context-Aware).
    接收完整的對話歷史，以解決 "US" 這種缺乏上下文的輸入。
    """
    # 構建對話歷史字串
    history_str = ""
    for i, msg in enumerate(clarification_history):
        history_str += f"User Step {i+1}: {msg}\n"

    print(f"🤖 [Resolver] 調用 LLM 解析完整對話歷史:\n{history_str.strip()}")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
    structured_llm = llm.with_structured_output(TickerResolution)
    
    prompt = f"""
    You are a financial data assistant engaged in a clarification dialogue with a user.
    
    Initial Context: 
    - The system originally tried to identify the ticker: '{original_ticker}'.
    - This failed or was ambiguous (e.g., dual-listed).
    
    Conversation History (Chronological):
    {history_str}
    
    Your Task:
    Analyze the ENTIRE conversation history to determine the user's intended stock ticker.
    The user's latest input (last step) is the most critical clarification, but it must be interpreted in the context of previous inputs and the original ticker.
    
    Examples:
    - Context: "台積電"
      History: User Step 1: "US"
      -> Result: "TSM" (User means TSMC's US listing)
      
    - Context: "Toyota"
      History: User Step 1: "Japan"
      -> Result: "7203.T"
      
    - Context: "BABA"
      History: User Step 1: "Hong Kong"
      -> Result: "9988.HK"

    Rules:
    1. If the history implies a market (e.g. "US", "USA", "NYSE", "ADR"), apply it to the original ticker '{original_ticker}'.
    2. If the history implies a local market (e.g. "TW", "Taiwan", "HK", "Japan"), apply it to '{original_ticker}'.
    3. If the history contains a new ticker symbol (e.g. "2330"), use that.
    4. DUAL-LISTING AMBIGUITY: If the user intent is still ambiguous (e.g. dual-listed company and NO market specified in history), return 'AMBIGUOUS'.
       - IMPORTANT: If returning AMBIGUOUS, list BOTH the US ADR and Local ticker in the 'reasoning' field so the user knows what to choose.
    5. If input is gibberish, return 'UNKNOWN'.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        print(f"   ✓ 解析結果: {result.resolved_ticker} ({result.reasoning})")
        return result
    except Exception as e:
        print(f"   ❌ 解析失敗: {e}")
        return TickerResolution(resolved_ticker="UNKNOWN", reasoning=str(e))


def _fetch_valid_info(ticker: str) -> dict | None:
    """
    嘗試從 yfinance 獲取數據並驗證有效性。
    如果失敗或無效，返回 None。
    """
    try:
        stock = yf.Ticker(ticker)
        # yfinance 的 info 屬性在失敗時可能會報錯，也可能返回空字典
        info = stock.info
        
        # 嚴謹檢查：必須包含 longName 且資料長度足夠
        is_valid = info and len(info) > 5 and 'longName' in info
        
        if is_valid:
            return info
        return None
    except Exception as e:
        # 這裡捕獲 404 或其他 HTTP 錯誤
        print(f"   ⚠️ yfinance error for '{ticker}': {e}")
        return None


# --- Main Node Function ---

def profiler_node(state: AgentState) -> dict:
    """
    Profiler node with V3 Ambiguity Detection & LLM Intent Resolution.
    Includes Auto-Rescue mechanism for initial failures.
    """
    current_ticker = state.get("ticker", "").strip()
    clarification_history = state.get("clarification_history", [])
    
    # 標記是否已經進行過 LLM 解析，避免重複調用
    has_attempted_resolution = False

    # 1. [V3 Logic] 處理澄清歷史 (如果有)
    # 這是用戶已經介入後的情況，我們優先信任用戶的澄清
    if clarification_history:
        # [FIX] 傳入整個 history 列表
        resolution = _resolve_user_intent(current_ticker, clarification_history)
        has_attempted_resolution = True # 標記已嘗試解析
        
        # [UX 改進] 如果 LLM 認為有歧義，直接再次觸發澄清迴圈
        if resolution.resolved_ticker == "AMBIGUOUS":
            print(f"⚖️ [Profiler] 發現雙重上市歧義: {resolution.reasoning}")
            return {
                "needs_clarification": True,
                "ticker": current_ticker,
                "error": f"請明確指定市場。{resolution.reasoning}"
            }
        
        elif resolution.resolved_ticker != "UNKNOWN":
            print(f"🔄 [Profiler] Ticker 已根據用戶澄清更新: {current_ticker} -> {resolution.resolved_ticker}")
            current_ticker = resolution.resolved_ticker
        else:
            print(f"⚠️ [Profiler] LLM 無法解析明確 Ticker，將嘗試原始輸入")
            # 如果是歷史對話解析失敗，通常取最後一個輸入作為嘗試
            current_ticker = clarification_history[-1].strip().upper()

    print(f"\n🕵️ [Node A: Profiler] 分析目標: {current_ticker}")
    
    try:
        # 2. [V3 Logic] 嘗試獲取數據
        info = _fetch_valid_info(current_ticker)
        
        # [NEW FEATURE] 自動搶救機制 (Auto-Rescue)
        # 條件：第一次抓取失敗，且之前沒有用 LLM 解析過（代表這是用戶第一次輸入的 Raw Input）
        if not info and not has_attempted_resolution:
            print(f"⚠️ [Profiler] 初次抓取失敗 ('{current_ticker}')。啟動 LLM 自動修復...")
            
            # 將當前的錯誤 Ticker 當作「澄清輸入」傳給 LLM 看看能不能修好
            # [FIX] Auto-Rescue 時，將原始 ticker 放入列表作為唯一的歷史
            resolution = _resolve_user_intent(current_ticker, [current_ticker])
            
            if resolution.resolved_ticker == "AMBIGUOUS":
                 print(f"⚖️ [Profiler] 自動修復發現歧義: {resolution.reasoning}")
                 return {
                    "needs_clarification": True,
                    "ticker": current_ticker,
                    "error": f"找到多個可能的公司，請明確指定市場。\n{resolution.reasoning}"
                }
            elif resolution.resolved_ticker != "UNKNOWN":
                print(f"✅ [Profiler] LLM 自動修復 Ticker: {current_ticker} -> {resolution.resolved_ticker}")
                current_ticker = resolution.resolved_ticker
                # 重試抓取
                info = _fetch_valid_info(current_ticker)
            else:
                print("❌ [Profiler] LLM 也無法識別此輸入。")

        # 3. 最終驗證：經過搶救後是否還有數據？
        if not info:
            print(f"⚠️ [Profiler] 無法識別 Ticker '{current_ticker}' 或資訊不足。")
            return {
                "needs_clarification": True,
                "ticker": current_ticker, # 保留當前嘗試失敗的 ticker
                "error": f"無法獲取 '{current_ticker}' 的數據。請確認代碼 (例如: 美股 TSM, 台股 2330.TW)。" 
            }

        # 4. 策略路由邏輯 (拿到數據後的正常流程)
        company_context = _build_company_context(current_ticker, info)
        print(f"📋 [Profile] Context Validated: {info.get('longName')}")
        
        print(f"🤖 [Router] 調用 Gemini 判斷最佳估值模型...")
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
2. 選擇最匹配的策略代碼。
3. 如果無法確定，回退選擇 '{ValuationStrategyType.GENERAL_DCF.value}'。
"""
        decision = structured_llm.invoke(prompt)
        
        print(f"🎯 [Router] 策略鎖定: {decision.strategy}")

        # 5. 返回成功狀態
        return {
            "ticker": current_ticker, # 更新 State 中的 Ticker (可能是修復後的)
            "needs_clarification": False,
            "company_name": info.get("longName", current_ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "valuation_strategy": decision.strategy,
            "strategy_reasoning": decision.reasoning,
            "error": None
        }
        
    except Exception as e:
        print(f"❌ Profiler System Error: {e}")
        return {
            "needs_clarification": True,
            "error": f"System error processing {current_ticker}: {str(e)}"
        }