"""
Node B: Calculator - Main Node Logic

This node orchestrates financial calculations:
1. Validates input financial data
2. Fetches market data using yfinance
3. Performs ratio calculations
4. Executes Dual-Track DCF Logic (Based on EPS w/o NRI and FCF)
"""

import math
from src.state import AgentState
from src.models.valuation import ValuationMetrics
from src.nodes.calculator.tools import get_market_data, get_normalized_income_data, calculate_metrics, calculate_dcf, calculate_historical_growth


def calculator_node(state: AgentState) -> dict:
    """
    Calculator node function.
    
    Features:
    - Dual DCF: Calculates value based on both FCF and EPS w/o NRI.
    - Tangible Book Value display.
    - Growth Rate Capping: Implements GuruFocus-style 5%-20% growth boundaries.
    - Uses Historical Growth (4Y CAGR) as primary growth input.
    - Optimized Discount Rates: Distinguishes between WACC (for FCF) and Cost of Equity (for EPS).
    """
    print(f"\n🧮 [Node B: Calculator] 正在計算 {state['ticker']} 的估值指標...")
    
    # 1. 獲取數據
    financial_obj = state.get("financial_data")
    if not financial_obj:
        return {"error": "missing_financial_data"}
    financials = financial_obj.model_dump()
    
    market_data = get_market_data(state["ticker"])
    if not market_data:
        return {"error": "market_data_fetch_failed"}
    
    print(f"📈 [Calculator] 現價: ${market_data['price']:.2f}")
    
    # 獲取標準化收益 (EPS w/o NRI source)
    nri_data = get_normalized_income_data(state["ticker"])
    
    # 2. 基礎計算
    metrics_dict = calculate_metrics(financials, market_data)
    pe_ttm = metrics_dict.get('pe_ratio_ttm')
    print(f"📊 [Metrics] P/E (TTM): {pe_ttm if pe_ttm else 'N/A'}")

    # 3. 準備 DCF 參數
    
    # (A) 增長率推導
    raw_growth_rate = 0.10 # Default fallback
    growth_source = "Default"
    
    hist_growth = calculate_historical_growth(state["ticker"])
    
    if hist_growth is not None:
        raw_growth_rate = hist_growth
        growth_source = "Historical CAGR (4Y)"
    else:
        pe_ratio = metrics_dict.get('pe_ratio', 0)
        peg = market_data.get('peg_ratio')
        
        if peg and peg > 0:
            implied_growth = (pe_ratio / peg) / 100
            if 0 < implied_growth < 1.0: 
                raw_growth_rate = implied_growth
                growth_source = f"PEG ({peg:.2f})"
        elif pe_ratio > 0:
            if pe_ratio > 50: raw_growth_rate = 0.25
            elif pe_ratio > 25: raw_growth_rate = 0.15
            else: raw_growth_rate = 0.10
            growth_source = f"P/E ({pe_ratio:.1f})"

    print(f"📊 [Growth Raw] 初始增長率: {raw_growth_rate:.2%} (Source: {growth_source})")

    # 增長率限制 (GuruFocus Rule)
    final_growth_rate = raw_growth_rate
    cap_msg = ""
    if raw_growth_rate > 0.20:
        final_growth_rate = 0.20
        cap_msg = "(Capped at 20%)"
    elif raw_growth_rate < 0.05:
        final_growth_rate = 0.05
        cap_msg = "(Floored at 5%)"
    print(f"🛡️ [Growth Final] 修正後增長率: {final_growth_rate:.2%} {cap_msg}")

    # (B) [Optimized] 折現率計算 (Dual-Track Discount Rate)
    # 我們將區分 WACC (用於 FCF) 和 Cost of Equity (用於 EPS)
    
    rf = market_data.get('risk_free_rate', 0.042)
    beta = market_data.get('beta') if market_data.get('beta') else 1.0
    
    # 1. Cost of Equity (Ke) - 用於 Earnings Model (Equity Only)
    # CAPM: Ke = Rf + Beta * ERP (Equity Risk Premium, assumed 5.5%)
    market_premium = 0.055
    cost_of_equity = rf + (beta * market_premium)
    
    # 為 EPS Model 設定一個較保守的 Hurdle Rate (保底)
    # 邏輯：Rf 向上取整 + 5.5% (GuruFocus style conservative floor)
    ke_floor = (math.ceil(rf * 100) / 100) + 0.055
    final_cost_of_equity = max(cost_of_equity, ke_floor)
    
    # 2. WACC - 用於 FCF Model (Firm Wide)
    # WACC = E/V * Ke + D/V * Kd * (1 - t)
    # 估算 Kd (Cost of Debt) = Rf + Spread (假設 1.5% spread for investment grade)
    cost_of_debt = rf + 0.015 
    tax_rate = 0.21 # 標準美國稅率假設
    
    market_cap = market_data.get('market_cap', 0)
    total_debt = market_data.get('total_debt', 0)
    total_value = market_cap + total_debt
    
    final_wacc = final_cost_of_equity # Default fallback
    
    if total_value > 0:
        weight_equity = market_cap / total_value
        weight_debt = total_debt / total_value
        raw_wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
        
        # WACC 通常比 Ke 低，但我們也要設一個絕對安全底線 (e.g., 6% or Rf+2%)
        # 防止對於超高槓桿或超低 Beta 公司算出過低的折現率
        wacc_floor = rf + 0.02 
        final_wacc = max(raw_wacc, wacc_floor)

    print(f"⚖️ [Discount Rate] WACC (FCF): {final_wacc:.1%} | Cost of Equity (EPS): {final_cost_of_equity:.1%}")

    # (C) 準備兩個 Base Value
    shares_outstanding = float(market_data.get('shares_outstanding', 0))
    cash_eq = market_data.get('cash_and_equivalents', 0.0)
    
    # Base 1: FCF
    fcf_base = 0.0
    ttm_fcf = market_data.get("fcf_ttm")
    if ttm_fcf and ttm_fcf > 0:
        fcf_base = float(ttm_fcf)
    else:
        fcf_base = (financial_obj.operating_cash_flow - abs(financial_obj.capital_expenditures)) * 1_000_000
    
    # Base 2: Earnings
    earnings_base = 0.0
    is_normalized = False
    if nri_data and nri_data.get('normalized_income'):
        earnings_base = nri_data['normalized_income']
        is_normalized = nri_data.get('use_normalized', False)
    else:
        earnings_base = financial_obj.net_income * 1_000_000

    # 4. 執行雙軌 DCF 計算
    
    # --- Track A: Based on FCF (Uses WACC) ---
    dcf_fcf = calculate_dcf(
        start_value=fcf_base,
        shares_outstanding=shares_outstanding,
        total_debt=total_debt,
        cash_and_equivalents=cash_eq,
        growth_rate=final_growth_rate,
        discount_rate=final_wacc,    # <--- 使用 WACC
        method="FCF"
    )
    
    # --- Track B: Based on EPS w/o NRI (Uses Cost of Equity) ---
    dcf_eps = calculate_dcf(
        start_value=earnings_base,
        shares_outstanding=shares_outstanding,
        total_debt=0, 
        cash_and_equivalents=0,
        growth_rate=final_growth_rate,
        discount_rate=final_cost_of_equity, # <--- 使用 Ke
        method="EPS"
    )
    
    # 5. 結果呈現與選擇
    val_fcf = dcf_fcf['intrinsic_value']
    val_eps = dcf_eps['intrinsic_value']
    curr_price = market_data['price']
    
    print(f"\n🆚 [Dual-Track Valuation Comparison]")
    print(f"   1. Based on FCF (WACC {final_wacc:.1%}):     ${val_fcf:.2f} (Upside: {((val_fcf-curr_price)/curr_price)*100:.1f}%)")
    print(f"      - FCF Base: ${fcf_base/1e9:.2f}B")
    print(f"   2. Based on EPS (Ke {final_cost_of_equity:.1%}):       ${val_eps:.2f} (Upside: {((val_eps-curr_price)/curr_price)*100:.1f}%)")
    print(f"      - Earnings Base: ${earnings_base/1e9:.2f}B")
    
    tbv = market_data.get('tangible_book_value', 0)
    tbv_per_share = tbv / shares_outstanding if shares_outstanding else 0
    print(f"   ℹ️ Tangible Book Value:   ${tbv_per_share:.2f} / share")

    # 選擇邏輯
    final_intrinsic_value = 0.0
    selection_reason = ""
    
    if fcf_base > 0 and earnings_base > 0:
        final_intrinsic_value = (val_fcf + val_eps) / 2
        selection_reason = "Average of FCF & Earnings Models"
    elif earnings_base > 0:
        final_intrinsic_value = val_eps
        selection_reason = "Earnings Model (FCF negative/invalid)"
    elif fcf_base > 0:
        final_intrinsic_value = val_fcf
        selection_reason = "FCF Model (Earnings negative/invalid)"
    
    upside = ((final_intrinsic_value - curr_price) / curr_price) * 100
    
    print(f"💎 [Final Decision] 選定估值: ${final_intrinsic_value:.2f} ({selection_reason})")

    # 6. 更新 Metrics
    metrics_dict['dcf_value'] = round(final_intrinsic_value, 2)
    metrics_dict['dcf_upside'] = round(upside, 2)
    
    eps_val = earnings_base / shares_outstanding if shares_outstanding > 0 else 0.0
    metrics_dict['eps_ttm'] = round(eps_val, 2)
    metrics_dict['eps_normalized'] = round(eps_val, 2) if is_normalized else None
    metrics_dict['is_normalized'] = is_normalized
    
    metrics_obj = ValuationMetrics(**metrics_dict)
    
    return {
        "valuation_metrics": metrics_obj,
        "investigation_tasks": [], 
        "error": None
    }