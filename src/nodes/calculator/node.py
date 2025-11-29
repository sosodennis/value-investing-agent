"""
Node B: Calculator - Main Node Logic

This node orchestrates financial calculations:
1. Validates input financial data
2. Fetches market data using yfinance
3. Performs ratio calculations using tools.calculate_metrics()
"""

import math
from src.state import AgentState
from src.models.valuation import ValuationMetrics
from src.nodes.calculator.tools import get_market_data, calculate_metrics, calculate_dcf


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
        
        # [New] 輸出雙軌 P/E 對比
        pe_ttm = metrics_dict.get('pe_ratio_ttm')
        pe_fy = metrics_dict.get('pe_ratio_fy', 0)
        if pe_ttm:
            print(f"📊 [Metrics] FY P/E: {pe_fy:.2f}, TTM P/E: {pe_ttm:.2f}")
        else:
            print(f"📊 [Metrics] FY P/E: {pe_fy:.2f}, TTM P/E: N/A")
        
        trend_insight = metrics_dict.get('pe_trend_insight', '')
        if trend_insight:
            print(f"💡 [Insight] {trend_insight}")
        
        # --- [New] 智能增長率推導邏輯 ---
        # 默認保守值
        estimated_growth_rate = 0.10
        
        # 先算出 P/E (使用主要 P/E，優先 TTM)
        pe_ratio = metrics_dict.get('pe_ratio', 0)
        peg = market_data.get('peg_ratio')
        
        print(f"📊 [Market Data] P/E: {pe_ratio:.2f}, PEG: {peg}")
        
        if peg and peg > 0:
            # 策略 A: 透過 PEG 反推 (Growth = P/E / PEG)
            # 例如 TSLA P/E 200 / PEG 5 = 40% Growth
            # 注意：yfinance 的 pegRatio 通常是比率，所以直接使用
            # 經驗公式：Growth Rate = (P/E) / PEG / 100
            
            implied_growth = (pe_ratio / peg) / 100
            
            # 設置安全邊界 (Sanity Check)：不相信超過 50% 的永續增長
            if 0 < implied_growth < 0.50:
                estimated_growth_rate = implied_growth
                print(f"🚀 [Insight] 根據 PEG ({peg:.2f}) 推導出市場隱含增長率: {estimated_growth_rate:.2%}")
            else:
                print(f"⚠️ [Insight] PEG 推導的增長率 ({implied_growth:.2%}) 過於極端，將使用規則修正。")
        
        # 策略 B: 如果沒有 PEG，或者 PEG 數據異常，使用 P/E 分層規則
        if estimated_growth_rate == 0.10:  # 代表上面沒更新
            if pe_ratio > 50:
                estimated_growth_rate = 0.25  # 高成長股假設
                print("🚀 [Insight] 檢測到高 P/E (>50)，啟用激進增長假設 (25%)")
            elif pe_ratio > 25:
                estimated_growth_rate = 0.15  # 中高成長
                print("📈 [Insight] 檢測到中高 P/E (>25)，啟用適度增長假設 (15%)")
        
        # --- [New] 動態計算 WACC (Discount Rate) with Hurdle Rate Floor ---
        # 1. 獲取參數
        rf = market_data.get('risk_free_rate', 0.042)  # 默認 4.2%
        beta = market_data.get('beta')
        market_premium = 0.05  # 設為 5% (歷史平均水平，Aswath Damodaran 的標準)
        
        # 2. 計算標準 CAPM WACC
        capm_wacc = 0.10  # Fallback
        if beta:
            capm_wacc = rf + beta * market_premium
            print(f"📉 [WACC] CAPM Raw: {capm_wacc:.1%}")
        else:
            print("⚠️ [WACC] 缺失 Beta 數據，使用默認 CAPM (10%)")
        
        # 3. [New] 計算保底折現率 (Hurdle Rate)
        # 邏輯參考：RoundUp(Rf) + 5.5% (Risk Premium Floor)
        # 這裡我們使用 math.ceil 對 Rf 進行向上取整 (例如 4.2% -> 5.0%)
        rf_percent = rf * 100
        rf_rounded = math.ceil(rf_percent) / 100
        hurdle_premium = 0.055  # 設定為 5.5% (折衷方案，介於 5-6% 之間)
        
        hurdle_rate = rf_rounded + hurdle_premium
        print(f"🛡️ [WACC] Hurdle Rate Floor: {hurdle_rate:.1%}")
        
        # 4. 決策：取兩者之大者
        # 這是為了防止低 Beta 導致折現率過低，同時也保留了高 Beta (如 TSLA) 的高折現率
        final_discount_rate = max(capm_wacc, hurdle_rate)
        
        if final_discount_rate == hurdle_rate:
            print(f"⚖️ [WACC Adjustment] CAPM 過低，啟用保底折現率: {final_discount_rate:.1%}")
        else:
            print(f"⚖️ [WACC Adjustment] 使用 CAPM 折現率: {final_discount_rate:.1%}")
        
        estimated_discount_rate = final_discount_rate
        
        # --- 執行 DCF ---
        # 準備數據
        ocf = financial_obj.operating_cash_flow
        capex = abs(financial_obj.capital_expenditures)  # 確保是絕對值
        fcf = ocf - capex
        
        print(f"💰 [Calculator] FCF 計算: {ocf} - {capex} = {fcf} (Millions)")
        
        # 獲取流通股數
        shares_outstanding = market_data.get('shares_outstanding', 0)
        
        if shares_outstanding > 0 and fcf > 0:
            # 調用工具，傳入動態增長率和動態 WACC
            intrinsic_value = calculate_dcf(
                free_cash_flow=fcf,
                shares_outstanding=shares_outstanding,
                growth_rate=estimated_growth_rate,  # <--- 注入動態增長率
                discount_rate=estimated_discount_rate,  # <--- 注入動態 WACC
                terminal_growth=0.03,
                projection_years=5
            )
            
            current_price = market_data['price']
            upside = ((intrinsic_value - current_price) / current_price) * 100
            
            print(f"💎 [Calculator] DCF 估值: ${intrinsic_value:.2f} (Upside: {upside:.2f}%)")
            
            # 更新 Metrics 對象
            metrics_dict['dcf_value'] = round(intrinsic_value, 2)
            metrics_dict['dcf_upside'] = round(upside, 2)
        else:
            print("⚠️ [Calculator] 無法計算 DCF: FCF 或流通股數為 0")
            metrics_dict['dcf_value'] = 0.0
            metrics_dict['dcf_upside'] = 0.0
        
        # 5. 封裝為 Pydantic 對象
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
