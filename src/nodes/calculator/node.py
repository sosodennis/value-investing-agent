"""
Node B: Calculator - Main Node Logic (Refactored Architecture)

Flow:
1. Data Layer (Tools): Fetch Raw Data.
2. Logic Layer (Logic): Determine Growth & Discount Rates.
3. Calculation Layer (Tools): Execute DCF Engines.
4. Presentation Layer: Aggregate Metrics.
"""

from src.state import AgentState
from src.models.valuation import ValuationMetrics
from src.nodes.calculator.tools import get_market_data_raw, get_normalized_income_data, calculate_historical_growth, calculate_dcf
from src.nodes.calculator.logic import determine_growth_rate, calculate_discount_rates

def calculator_node(state: AgentState) -> dict:
    ticker = state["ticker"]
    print(f"\n🧮 [Calculator] Processing {ticker} (Refactored Structure)...")
    
    # 1. 數據獲取 (Data Layer)
    md = get_market_data_raw(ticker)
    if not md: return {"error": "Market Data Failed"}
    
    fin_obj = state.get("financial_data")
    financials = fin_obj.model_dump()
    nri_data = get_normalized_income_data(ticker)
    
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
    
    # 3. 準備 DCF 輸入 (Scenario Preparation)
    shares = md['shares_outstanding']
    net_debt = md['total_debt'] - md['cash_and_equivalents']
    
    # Base Values
    raw_ni = financials['net_income'] * 1_000_000
    # FCF (Street): OCF - Capex
    raw_fcf = (fin_obj.operating_cash_flow - abs(fin_obj.capital_expenditures)) * 1_000_000
    sbc = md['sbc']
    
    # Scenario 1: Conservative (SBC is Cost)
    base_eps_cons = raw_ni
    base_fcf_cons = raw_fcf - sbc
    
    # Scenario 2: Street (SBC is ignored)
    base_eps_street = raw_ni + sbc
    base_fcf_street = raw_fcf
    
    print(f"🎭 [Scenario] SBC: ${sbc/1e9:.2f}B")
    
    # 4. 執行計算 (Calculation Layer)
    
    # Track A: FCF Model (Using WACC, Enterprise Value approach)
    res_fcf = calculate_dcf(
        base_fcf_cons, shares, net_debt, 
        growth_dec['rate'], disc_dec['wacc'], method="FCF(Cons)"
    )
    
    # Track B: EPS Model (Using Ke, Direct Equity approach)
    # Note: For EPS model, we assume the output is Equity Value directly, so we pass net_debt=0
    res_eps = calculate_dcf(
        base_eps_cons, shares, 0.0, 
        growth_dec['rate'], disc_dec['ke'], method="EPS(Cons)"
    )
    
    # Run Street Scenario for Bull Case
    res_fcf_bull = calculate_dcf(
        base_fcf_street, shares, net_debt,
        growth_dec['rate'], disc_dec['wacc'], method="FCF(Street)"
    )
    res_eps_bull = calculate_dcf(
        base_eps_street, shares, 0.0,
        growth_dec['rate'], disc_dec['ke'], method="EPS(Street)"
    )
    
    # 5. 結果匯總
    # Conservative Value
    val_final = (res_fcf['intrinsic_value'] + res_eps['intrinsic_value']) / 2
    # Bull Value
    val_bull = (res_fcf_bull['intrinsic_value'] + res_eps_bull['intrinsic_value']) / 2
    
    curr_price = md['price']
    upside = (val_final - curr_price) / curr_price if curr_price else 0
    
    print(f"💎 [Result] ${val_final:.2f} (Upside: {upside:.1%}) | Bull: ${val_bull:.2f}")
    
    # Populate Metrics
    pe_ttm = md['pe_ratio'] if md['pe_ratio'] else 0
    
    # Calculate FY P/E
    pe_fy = 0
    if raw_ni > 0 and md['market_cap'] > 0:
        pe_fy = md['market_cap'] / raw_ni
        
    # Calculate Margin
    rev_m = financials.get('total_revenue', 0)
    ni_m = financials.get('net_income', 0)
    margin = (ni_m / rev_m * 100) if rev_m > 0 else 0
    
    # Normalized Info
    is_norm = False
    eps_norm = 0
    if nri_data:
        is_norm = nri_data['use_normalized']
        eps_norm = nri_data['normalized_income'] / shares if shares else 0

    metrics_dict = {
        "market_cap": md['market_cap'] / 1_000_000, # to Millions
        "current_price": curr_price,
        "dcf_value": val_final,
        "dcf_value_bull": val_bull,
        "dcf_upside": round(upside * 100, 2),
        "valuation_status": "Undervalued" if upside > 0.1 else ("Overvalued" if upside < -0.1 else "Fair Value"),
        "pe_ratio": pe_ttm,
        "net_profit_margin": round(margin, 2),
        "pe_ratio_ttm": pe_ttm,
        "pe_ratio_fy": round(pe_fy, 2),
        "pe_trend_insight": "N/A", # Simplified for now
        "eps_ttm": raw_ni / shares if shares else 0,
        "eps_normalized": round(eps_norm, 2),
        "is_normalized": is_norm
    }
    
    return {
        "valuation_metrics": ValuationMetrics(**metrics_dict),
        "investigation_tasks": [],
        "error": None
    }