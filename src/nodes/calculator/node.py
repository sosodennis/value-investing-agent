"""
Node B: Calculator - Main Node Logic (Enterprise Grade)

Features:
- Sector-Aware Valuation (e.g., Banks use Earnings Model).
- Dual-Track DCF with Linear Growth Decay.
- Dynamic Risk Assessment (TV Concentration).
- GuruFocus-style Growth Capping.
- Smart Hybrid Growth Strategy with SGR (Sustainable Growth Rate) backup.
- Adjusted Beta (Blume's + Mega-Cap Cap) for realistic discount rates.
- Dual-Scenario Analysis (Conservative vs. Street) handling SBC.
"""

import math
from src.state import AgentState
from src.models.valuation import ValuationMetrics
from src.nodes.calculator.tools import get_market_data, get_normalized_income_data, calculate_metrics, calculate_dcf, calculate_historical_growth


def calculator_node(state: AgentState) -> dict:
    print(f"\n🧮 [Node B: Calculator] 正在計算 {state['ticker']} 的估值指標 (Enterprise Grade)...")
    
    # 1. 獲取數據
    financial_obj = state.get("financial_data")
    if not financial_obj: return {"error": "missing_financial_data"}
    financials = financial_obj.model_dump()
    
    market_data = get_market_data(state["ticker"])
    if not market_data: return {"error": "market_data_fetch_failed"}
    
    sector = market_data.get("sector", "Unknown")
    print(f"📈 [Market Data] Price: ${market_data['price']:.2f} | Sector: {sector}")
    
    nri_data = get_normalized_income_data(state["ticker"])
    
    # 2. 基礎計算
    metrics_dict = calculate_metrics(financials, market_data)
    pe_ttm = metrics_dict.get('pe_ratio_ttm')

    # 3. 準備 DCF 參數
    
    # (A) 增長率 (Smart Hybrid Logic with SGR Backup)
    raw_growth_rate = 0.10 # Default
    growth_source = "Default"
    
    hist_growth = calculate_historical_growth(state["ticker"])
    
    sgr_growth = None
    roe = market_data.get("roe")
    payout = market_data.get("payout_ratio")
    
    if roe is not None:
        retention = 1 - (payout if payout else 0.0)
        calculated_sgr = roe * retention
        if 0.02 < calculated_sgr < 0.25: 
            sgr_growth = calculated_sgr
    
    pe_ratio = metrics_dict.get('pe_ratio', 0)
    peg = market_data.get('peg_ratio')
    peg_growth = None
    
    if peg and peg > 0 and pe_ratio > 0:
        implied = (pe_ratio / peg) / 100
        if 0.02 < implied < 0.30: 
            peg_growth = implied
            
    print(f"🔍 [Debug] Sources -> Hist: {hist_growth if hist_growth else 'N/A'} | PEG: {peg_growth if peg_growth else 'N/A'} | SGR: {sgr_growth if sgr_growth else 'N/A'}")

    if peg_growth is not None:
        if sgr_growth and peg_growth > sgr_growth * 1.5:
             raw_growth_rate = (peg_growth + sgr_growth) / 2
             growth_source = "Blended (PEG & SGR - PEG too optimistic)"
        else:
             raw_growth_rate = peg_growth
             growth_source = "Analyst Consensus (PEG)"
    elif sgr_growth is not None:
        if hist_growth is None or hist_growth < 0.05:
            raw_growth_rate = sgr_growth
            growth_source = f"Sustainable Growth (ROE {roe:.1%} * Retention)"
        else:
            raw_growth_rate = (sgr_growth + hist_growth) / 2
            growth_source = "Blended (SGR & Hist)"
    elif hist_growth is not None:
        if pe_ratio > 25 and hist_growth < 0.08:
             raw_growth_rate = 0.12 
             growth_source = "Market Implied (High P/E Fix)"
        else:
            raw_growth_rate = hist_growth
            growth_source = "Historical CAGR"
    
    final_growth_rate = raw_growth_rate
    cap_msg = ""
    if raw_growth_rate > 0.20:
        final_growth_rate = 0.20
        cap_msg = "(Capped at 20%)"
    elif raw_growth_rate < 0.05:
        final_growth_rate = 0.05
        cap_msg = "(Floored at 5%)"
    
    print(f"📊 [Growth] {final_growth_rate:.2%} {cap_msg} based on {growth_source}")

    # (B) 折現率 (含 Adjusted Beta)
    rf = market_data.get('risk_free_rate', 0.042)
    raw_beta = market_data.get('beta') if market_data.get('beta') else 1.0
    
    market_cap_b = market_data.get('market_cap', 0) / 1_000_000_000 
    adj_beta = (0.67 * raw_beta) + 0.33
    beta_note = "Blume's Adj"
    if market_cap_b > 200: 
        if adj_beta > 1.50:
            adj_beta = 1.50
            beta_note += " + Mega-Cap Cap(1.5)"
    
    print(f"⚖️ [Risk Adj] Raw Beta: {raw_beta:.2f} -> Adj Beta: {adj_beta:.2f} ({beta_note})")
    
    market_premium = 0.06 
    cost_of_equity = rf + (adj_beta * market_premium)
    ke_floor = (math.ceil(rf * 100) / 100) + 0.055
    final_ke = max(cost_of_equity, ke_floor)
    
    int_cov = market_data.get('interest_coverage')
    base_spread = 0.015
    if int_cov is not None:
        if int_cov > 8.5: base_spread = 0.010 
        elif int_cov < 2.0: base_spread = 0.040 
        print(f"⚖️ [Credit Risk] Interest Coverage: {int_cov:.1f}x -> Spread: {base_spread:.1%}")
    
    cost_of_debt = rf + base_spread
    tax_rate = 0.21
    
    mv_equity = market_data.get('market_cap', 0)
    mv_debt = market_data.get('total_debt', 0)
    total_val = mv_equity + mv_debt
    
    final_wacc = final_ke
    if total_val > 0:
        we = mv_equity / total_val
        wd = mv_debt / total_val
        raw_wacc = (we * final_ke) + (wd * cost_of_debt * (1 - tax_rate))
        final_wacc = max(raw_wacc, rf + 0.02)

    print(f"⚖️ [Discount] WACC: {final_wacc:.1%} | Ke: {final_ke:.1%} (Floor: {ke_floor:.1%})")

    # (C) Base Values & Scenario Analysis
    shares = float(market_data.get('shares_outstanding', 0))
    cash_eq = market_data.get('cash_and_equivalents', 0.0)
    sbc = market_data.get('stock_based_compensation', 0.0)
    
    # 原始數據
    # Note: financial_obj.net_income is usually GAAP.
    raw_net_income = financial_obj.net_income * 1_000_000
    
    # 獲取 TTM FCF (這是 "Street" FCF, 因為 OCF 已經加回了 SBC)
    ttm_fcf_street = 0.0
    y_fcf = market_data.get("fcf_ttm")
    if y_fcf and y_fcf > 0:
        ttm_fcf_street = float(y_fcf)
    else:
        # Fallback to FY data (OCF - Capex)
        # OCF 裡通常包含了加回的 SBC
        ttm_fcf_street = (financial_obj.operating_cash_flow - abs(financial_obj.capital_expenditures)) * 1_000_000

    # --- 定義兩種情境 ---
    
    # Scenario A: Conservative (GAAP / Realist)
    # 觀點：SBC 是真實成本。如果要防止股權稀釋，公司必須花現金回購股票。
    # 因此，從 FCF 中扣除 SBC。EPS 使用 GAAP Net Income。
    base_eps_cons = raw_net_income
    base_fcf_cons = ttm_fcf_street - sbc 
    if base_fcf_cons < 0: base_fcf_cons = 0 # 避免負值導致模型崩潰，或保留負值表示風險
    
    # Scenario B: Street / Aggressive (Non-GAAP)
    # 觀點：SBC 是非現金支出。分析師通常使用 Non-GAAP EPS (Net Income + SBC + Amortization etc)。
    # FCF 使用標準定義 (OCF - Capex)。
    base_eps_street = raw_net_income + sbc
    base_fcf_street = ttm_fcf_street 

    print(f"\n🎭 [Scenario Analysis] SBC Impact: ${sbc/1e9:.2f}B")
    print(f"   • Conservative Base (GAAP): EPS=${base_eps_cons/1e9:.2f}B | FCF=${base_fcf_cons/1e9:.2f}B (FCF - SBC)")
    print(f"   • Street Base (Add-back SBC):  EPS=${base_eps_street/1e9:.2f}B | FCF=${base_fcf_street/1e9:.2f}B")

    # 4. 執行雙軌計算 (Dual Track x 2 Scenarios)
    
    # --- Run Conservative ---
    dcf_fcf_cons = calculate_dcf(base_fcf_cons, shares, mv_debt, cash_eq, final_growth_rate, final_wacc, method="FCF (Cons)")
    dcf_eps_cons = calculate_dcf(base_eps_cons, shares, 0, 0, final_growth_rate, final_ke, method="EPS (Cons)")
    val_cons = 0.0
    
    # --- Run Street ---
    dcf_fcf_street = calculate_dcf(base_fcf_street, shares, mv_debt, cash_eq, final_growth_rate, final_wacc, method="FCF (Street)")
    dcf_eps_street = calculate_dcf(base_eps_street, shares, 0, 0, final_growth_rate, final_ke, method="EPS (Street)")
    val_street = 0.0

    # 5. 智能決策邏輯 (Sector-Aware + Scenario)
    # 先決定每個 Scenario 內部的取值 (FCF vs EPS)
    
    def select_val_in_scenario(v_fcf, v_eps, sect):
        if "Financial" in sect or "Bank" in sect or "Insurance" in sect:
            return v_eps
        elif "Real Estate" in sect:
            return v_fcf
        else:
            # 通用邏輯：平均或保守
            if v_fcf > 0 and v_eps > 0:
                return (v_fcf + v_eps) / 2
            elif v_eps > 0: return v_eps
            elif v_fcf > 0: return v_fcf
            return 0.0

    val_cons = select_val_in_scenario(dcf_fcf_cons['intrinsic_value'], dcf_eps_cons['intrinsic_value'], sector)
    val_street = select_val_in_scenario(dcf_fcf_street['intrinsic_value'], dcf_eps_street['intrinsic_value'], sector)
    
    curr_price = market_data['price']
    
    print(f"\n🆚 [Valuation Range]")
    print(f"   🛡️ Conservative Value (SBC Expensed): ${val_cons:.2f} (Upside: {((val_cons-curr_price)/curr_price)*100:.1f}%)")
    print(f"   🚀 Street Value (SBC Ignored):        ${val_street:.2f} (Upside: {((val_street-curr_price)/curr_price)*100:.1f}%)")
    
    # 最終決策：依然以保守值為主要輸出 (Enterprise Grade 的堅持)，但在 Metrics 中記錄樂觀值
    final_val = val_cons 
    reason = "Conservative (GAAP based)"
    
    # 如果保守值太低，但市場價格接近 Street Value，可以在 Reason 中備註
    if final_val < curr_price and val_street > curr_price:
        reason += " [Market pricing in Street/Non-GAAP Scenario]"

    upside = ((final_val - curr_price) / curr_price) * 100
    print(f"💎 [Final Decision] ${final_val:.2f} ({reason})")

    metrics_dict['dcf_value'] = round(final_val, 2)
    metrics_dict['dcf_value_bull'] = round(val_street, 2) # [New] 存入樂觀估值
    metrics_dict['dcf_upside'] = round(upside, 2)
    
    # [Restored Logic] Calculate Earnings Base for Metrics population
    earnings_base = 0.0
    is_normalized = False
    if nri_data and nri_data.get('normalized_income'):
        earnings_base = nri_data['normalized_income']
        is_normalized = nri_data.get('use_normalized', False)
    else:
        earnings_base = financial_obj.net_income * 1_000_000

    eps_val = earnings_base / shares if shares > 0 else 0.0
    metrics_dict['eps_ttm'] = round(eps_val, 2)
    metrics_dict['eps_normalized'] = round(eps_val, 2) if is_normalized else None
    metrics_dict['is_normalized'] = is_normalized
    
    return {
        "valuation_metrics": ValuationMetrics(**metrics_dict),
        "investigation_tasks": [],
        "error": None
    }