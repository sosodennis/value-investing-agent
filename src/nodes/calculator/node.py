"""
Node B: Calculator - Main Node Logic (Refactored Architecture)

Flow:
1. Data Layer (Tools): Fetch Raw Data.
2. Logic Layer (Logic): Determine Growth & Discount Rates & Exit Multiples.
3. Calculation Layer (Tools): Execute DCF Engines with Dual Scenarios.
4. Presentation Layer: Aggregate Metrics.
"""

from src.state import AgentState
from src.models.valuation import ValuationMetrics
from src.nodes.calculator.tools import get_market_data_raw, get_normalized_income_data, calculate_historical_growth, calculate_dcf
from src.nodes.calculator.logic import determine_growth_rate, calculate_discount_rates, determine_exit_multiple

def calculator_node(state: AgentState) -> dict:
    ticker = state["ticker"]
    print(f"\n🧮 [Calculator] Processing {ticker} (Refactored Structure)...")
    
    # 1. 數據獲取 (Data Layer)
    md = get_market_data_raw(ticker)
    if not md: return {"error": "Market Data Failed"}
    
    fin_obj = state.get("financial_data")
    financials = fin_obj.model_dump()
    nri_data = get_normalized_income_data(ticker)
    print(f"📥 [Sector] {md['sector']} | Market Cap: ${md['market_cap']/1e9:.2f}B")
    
    # 2. 核心參數決策 (Logic Layer)
    # A. Growth
    hist_growth = calculate_historical_growth(ticker)
    growth_dec = determine_growth_rate(
        hist_growth, md['peg_ratio'], md['pe_ratio'], md['roe'], md['payout_ratio']
    )
    print(f"📊 [Growth] {growth_dec['rate']:.1%} | Reason: {growth_dec['source']}")
    
    # B. Discount
    disc_dec = calculate_discount_rates(
        md['risk_free_rate'], md['beta'], md['market_cap'], 
        md['ebit'], md['interest_expense'], md['total_debt'], md['market_cap']
    )
    print(f"⚖️ [Discount] WACC: {disc_dec['wacc']:.1%} | Ke: {disc_dec['ke']:.1%}")
    
    # C. Exit Multiple Decision (New)
    exit_mult_dec = determine_exit_multiple(
        md['pe_ratio'], 
        growth_dec['rate'], 
        md['sector']
    )
    print(f"🎯 [Exit Multiple] Target: {exit_mult_dec['multiple']:.1f}x | Reason: {exit_mult_dec['reason']}")
    
    # 3. 準備 DCF 輸入 (Scenario Preparation)
    shares = md['shares_outstanding']
    net_debt = md['total_debt'] - md['cash_and_equivalents']
    
    # Base Values
    # [FIX] Explicitly define raw_ni (GAAP Net Income) first
    raw_ni = financials['net_income'] * 1_000_000
    
    # Use Normalized Income if available for better accuracy, else GAAP Net Income
    earnings_base = 0.0
    is_normalized = False
    if nri_data and nri_data.get('normalized_income'):
        earnings_base = nri_data['normalized_income']
        is_normalized = nri_data.get('use_normalized', False)
    else:
        earnings_base = raw_ni
    
    # FCF (Street): OCF - Capex
    raw_fcf = (fin_obj.operating_cash_flow - abs(fin_obj.capital_expenditures)) * 1_000_000
    if md['fcf_ttm'] > 0:
        raw_fcf = md['fcf_ttm']
        
    sbc = md['sbc']
    
    # Scenario 1: Conservative (SBC is Cost)
    base_eps_cons = earnings_base # Usually Normalized Income is best proxy for owner earnings base
    base_fcf_cons = raw_fcf - sbc
    if base_fcf_cons < 0: base_fcf_cons = 0
    
    # Scenario 2: Street (SBC is ignored)
    base_eps_street = earnings_base + sbc # Add back SBC to mimic Non-GAAP
    base_fcf_street = raw_fcf
    
    print(f"🎭 [Scenario] SBC: ${sbc/1e9:.2f}B")
    
    # 4. 執行計算 (Calculation Layer)
    
    # --- Conservative Scenario ---
    # Track A: FCF Model
    res_fcf = calculate_dcf(
        base_fcf_cons, shares, net_debt, 
        growth_dec['rate'], disc_dec['wacc'], 
        exit_multiple=exit_mult_dec['multiple'],
        method="FCF(Cons)"
    )
    
    # Track B: EPS Model (Net Debt = 0 for Equity Valuation)
    res_eps = calculate_dcf(
        base_eps_cons, shares, 0.0, 
        growth_dec['rate'], disc_dec['ke'], 
        exit_multiple=exit_mult_dec['multiple'],
        method="EPS(Cons)"
    )
    
    # --- Street Scenario (Bull Case) ---
    res_fcf_bull = calculate_dcf(
        base_fcf_street, shares, net_debt,
        growth_dec['rate'], disc_dec['wacc'], 
        exit_multiple=exit_mult_dec['multiple'],
        method="FCF(Street)"
    )
    res_eps_bull = calculate_dcf(
        base_eps_street, shares, 0.0,
        growth_dec['rate'], disc_dec['ke'], 
        exit_multiple=exit_mult_dec['multiple'],
        method="EPS(Street)"
    )
    
    # 5. 結果匯總 & 智能決策
    
    def select_val(v_fcf, v_eps, sect):
        if "Financial" in sect or "Bank" in sect: return v_eps
        if "Real Estate" in sect: return v_fcf
        if v_fcf > 0 and v_eps > 0: return (v_fcf + v_eps) / 2
        return max(v_fcf, v_eps)

    val_cons = select_val(res_fcf['intrinsic_value'], res_eps['intrinsic_value'], md['sector'])
    val_bull = select_val(res_fcf_bull['intrinsic_value'], res_eps_bull['intrinsic_value'], md['sector'])
    
    curr_price = md['price']
    upside = (val_cons - curr_price) / curr_price if curr_price else 0
    
    print(f"💎 [Result] Conservative: ${val_cons:.2f} (Upside: {upside:.1%}) | Bull: ${val_bull:.2f}")
    
    # Populate Metrics
    pe_ttm = md['pe_ratio'] if md['pe_ratio'] else 0
    
    # Calculate FY P/E
    pe_fy = 0
    if earnings_base > 0 and md['market_cap'] > 0:
        pe_fy = md['market_cap'] / earnings_base
        
    # Calculate Margin
    rev_m = financials.get('total_revenue', 0)
    ni_m = financials.get('net_income', 0)
    margin = (ni_m / rev_m * 100) if rev_m > 0 else 0
    
    eps_norm = earnings_base / shares if shares else 0

    # [Polish] Restore Trend Insight
    trend_insight = "Stable"
    if pe_ttm and pe_fy > 0:
        diff_pct = (pe_ttm - pe_fy) / pe_fy
        if diff_pct < -0.05:
            trend_insight = f"Earnings Improving (Forward PE {pe_fy:.1f} < TTM {pe_ttm:.1f})"
        elif diff_pct > 0.05:
            trend_insight = f"Earnings Declining (Forward PE {pe_fy:.1f} > TTM {pe_ttm:.1f})"

    metrics_dict = {
        "market_cap": md['market_cap'] / 1_000_000, 
        "current_price": curr_price,
        "dcf_value": val_cons,
        "dcf_value_bull": val_bull,
        "dcf_upside": round(upside * 100, 2),
        "valuation_status": "Undervalued" if upside > 0.1 else ("Overvalued" if upside < -0.1 else "Fair Value"),
        "pe_ratio": pe_ttm,
        "net_profit_margin": round(margin, 2),
        "pe_ratio_ttm": pe_ttm,
        "pe_ratio_fy": round(pe_fy, 2),
        "pe_trend_insight": trend_insight, 
        "eps_ttm": raw_ni / shares if shares else 0, # GAAP EPS
        "eps_normalized": round(eps_norm, 2),
        "is_normalized": is_normalized
    }
    
    return {
        "valuation_metrics": ValuationMetrics(**metrics_dict),
        "investigation_tasks": [],
        "error": None
    }