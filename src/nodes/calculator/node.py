"""
Node B: Calculator - Main Node Logic (Enterprise Grade)

Features:
- Sector-Aware Valuation (e.g., Banks use Earnings Model).
- Dual-Track DCF with Linear Growth Decay.
- Dynamic Risk Assessment (TV Concentration).
- GuruFocus-style Growth Capping.
- Smart Hybrid Growth Strategy with SGR (Sustainable Growth Rate) backup.
- Adjusted Beta (Blume's + Mega-Cap Cap) for realistic discount rates.
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
    # 策略優先級: 1. Analyst Consensus (PEG) -> 2. Internal Engine (SGR) -> 3. Historical Data
    
    raw_growth_rate = 0.10 # Default
    growth_source = "Default"
    
    # 3.1 準備所有數據源
    hist_growth = calculate_historical_growth(state["ticker"])
    
    # 計算 SGR (Sustainable Growth Rate)
    sgr_growth = None
    roe = market_data.get("roe")
    payout = market_data.get("payout_ratio")
    
    if roe is not None:
        # 如果 payout 缺失，保守假設不發股息 (Retention = 1.0) 或者使用 0.0
        retention = 1 - (payout if payout else 0.0)
        calculated_sgr = roe * retention
        # SGR 範圍限制 (避免 ROE 極高導致數據爆炸，例如 AAPL 回購導致 Equity 很小)
        if 0.02 < calculated_sgr < 0.25: 
            sgr_growth = calculated_sgr
    
    # 計算 PEG Implied Growth
    pe_ratio = metrics_dict.get('pe_ratio', 0)
    peg = market_data.get('peg_ratio')
    peg_growth = None
    
    if peg and peg > 0 and pe_ratio > 0:
        implied = (pe_ratio / peg) / 100
        if 0.02 < implied < 0.30: 
            peg_growth = implied
            
    print(f"🔍 [Debug] Sources -> Hist: {hist_growth if hist_growth else 'N/A'} | PEG: {peg_growth if peg_growth else 'N/A'} | SGR: {sgr_growth if sgr_growth else 'N/A'}")

    # 3.2 決策樹 (Decision Tree)
    
    # 情境 1: 有 PEG 數據 (最理想，代表市場共識)
    if peg_growth is not None:
        # 檢查是否過度樂觀 (與 SGR 嚴重衝突)
        if sgr_growth and peg_growth > sgr_growth * 1.5:
             raw_growth_rate = (peg_growth + sgr_growth) / 2
             growth_source = "Blended (PEG & SGR - PEG too optimistic)"
        else:
             raw_growth_rate = peg_growth
             growth_source = "Analyst Consensus (PEG)"
    
    # 情境 2: PEG 缺失，但有 SGR (UNH 救星，內生增長)
    elif sgr_growth is not None:
        # 如果歷史數據很差 (UNH case) 或缺失，SGR 是最佳估計
        if hist_growth is None or hist_growth < 0.05:
            raw_growth_rate = sgr_growth
            growth_source = f"Sustainable Growth (ROE {roe:.1%} * Retention)"
        else:
            # 歷史數據不錯，SGR 也不錯 -> 取平均以平滑
            raw_growth_rate = (sgr_growth + hist_growth) / 2
            growth_source = "Blended (SGR & Hist)"
            
    # 情境 3: 只有歷史數據 (Fallback)
    elif hist_growth is not None:
        # High P/E check
        if pe_ratio > 25 and hist_growth < 0.08:
             raw_growth_rate = 0.12 # High PE implies higher future growth
             growth_source = "Market Implied (High P/E Fix)"
        else:
            raw_growth_rate = hist_growth
            growth_source = "Historical CAGR"
    
    # 5-20% Cap (GuruFocus Rule)
    final_growth_rate = raw_growth_rate
    cap_msg = ""
    if raw_growth_rate > 0.20:
        final_growth_rate = 0.20
        cap_msg = "(Capped at 20%)"
    elif raw_growth_rate < 0.05:
        final_growth_rate = 0.05
        cap_msg = "(Floored at 5%)"
    
    print(f"📊 [Growth] {final_growth_rate:.2%} {cap_msg} based on {growth_source}")

    # (B) 折現率 (含 Beta 調整與 Spread 邏輯)
    rf = market_data.get('risk_free_rate', 0.042)
    raw_beta = market_data.get('beta') if market_data.get('beta') else 1.0
    
    # [Enterprise Grade Fix] Beta 收斂調整 (Blume's Adjustment + Mega-Cap Cap)
    # 針對 NVDA 等超大市值高波動成長股，原始 Beta 會導致極其嚴苛的折現率
    market_cap_b = market_data.get('market_cap', 0) / 1_000_000_000 # Billion
    
    # 1. Blume's Adjustment: 將 Beta 向 1.0 拉近 (長期均值回歸)
    # Adjusted Beta = (0.67 * Raw Beta) + (0.33 * 1.0)
    adj_beta = (0.67 * raw_beta) + 0.33
    
    # 2. Mega-Cap Capping: 3兆美元俱樂部的公司，系統性風險不應被視為市場的2倍以上
    beta_note = "Blume's Adj"
    if market_cap_b > 200: # 定義 Mega Cap 為 >200B
        if adj_beta > 1.50:
            adj_beta = 1.50
            beta_note += " + Mega-Cap Cap(1.5)"
    
    print(f"⚖️ [Risk Adj] Raw Beta: {raw_beta:.2f} -> Adj Beta: {adj_beta:.2f} ({beta_note})")
    
    # Cost of Equity (Earnings Model)
    market_premium = 0.06 
    # 使用調整後的 Beta 計算 CAPM
    cost_of_equity = rf + (adj_beta * market_premium)
    
    # Hurdle Rate Floor (GuruFocus Logic)
    ke_floor = (math.ceil(rf * 100) / 100) + 0.055
    final_ke = max(cost_of_equity, ke_floor)
    
    # WACC (FCF Model)
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
        # WACC 通常低於 Ke，但也設一個絕對地板
        final_wacc = max(raw_wacc, rf + 0.02)

    print(f"⚖️ [Discount] WACC: {final_wacc:.1%} | Ke: {final_ke:.1%} (Floor: {ke_floor:.1%})")

    # (C) Base Values
    shares = float(market_data.get('shares_outstanding', 0))
    
    # FCF Base
    fcf_base = 0.0
    ttm_fcf = market_data.get("fcf_ttm")
    if ttm_fcf and ttm_fcf > 0: fcf_base = float(ttm_fcf)
    else: fcf_base = (financial_obj.operating_cash_flow - abs(financial_obj.capital_expenditures)) * 1_000_000
    
    # Earnings Base
    earnings_base = 0.0
    is_normalized = False
    if nri_data and nri_data.get('normalized_income'):
        earnings_base = nri_data['normalized_income']
        is_normalized = nri_data.get('use_normalized', False)
    else:
        earnings_base = financial_obj.net_income * 1_000_000

    # 4. 執行計算 (含 Linear Fade)
    dcf_fcf = calculate_dcf(fcf_base, shares, mv_debt, market_data.get('cash_and_equivalents',0), final_growth_rate, final_wacc, method="FCF")
    dcf_eps = calculate_dcf(earnings_base, shares, 0, 0, final_growth_rate, final_ke, method="EPS")
    
    val_fcf = dcf_fcf['intrinsic_value']
    val_eps = dcf_eps['intrinsic_value']
    curr_price = market_data['price']
    
    # 5. 智能決策邏輯 (Sector-Aware)
    print(f"\n🆚 [Valuation Logic]")
    print(f"   1. FCF Model (${val_fcf:.2f}): TV Concentration {dcf_fcf['tv_concentration']:.0%}")
    print(f"   2. EPS Model (${val_eps:.2f}): TV Concentration {dcf_eps['tv_concentration']:.0%}")
    
    final_val = 0.0
    reason = ""
    
    # 行業特殊規則
    if "Financial" in sector or "Bank" in sector or "Insurance" in sector:
        final_val = val_eps
        reason = f"Sector ({sector}) requires Earnings Model"
    elif "Real Estate" in sector:
        final_val = val_fcf
        reason = f"Sector ({sector}) prefers Cash Flow Model"
    else:
        # 通用邏輯：保守原則
        if fcf_base > 0 and earnings_base > 0:
            if val_fcf > 2 * val_eps:
                final_val = val_eps
                reason = "Conservative (FCF > 2x EPS)"
            elif val_eps > 2 * val_fcf:
                final_val = val_fcf
                reason = "Conservative (EPS > 2x FCF)"
            else:
                final_val = (val_fcf + val_eps) / 2
                reason = "Average of Dual Tracks"
        elif earnings_base > 0:
            final_val = val_eps
            reason = "Earnings Model (FCF Invalid)"
        else:
            final_val = val_fcf
            reason = "FCF Model (Earnings Invalid)"
            
    # Sanity Check on TV Concentration
    selected_dcf_res = dcf_eps if final_val == val_eps else dcf_fcf
    if selected_dcf_res['tv_concentration'] > 0.75:
        reason += " [⚠️ High Risk: >75% Value from TV]"

    upside = ((final_val - curr_price) / curr_price) * 100
    print(f"💎 [Final Decision] ${final_val:.2f} ({reason})")

    metrics_dict['dcf_value'] = round(final_val, 2)
    metrics_dict['dcf_upside'] = round(upside, 2)
    
    eps_val = earnings_base / shares if shares > 0 else 0.0
    metrics_dict['eps_ttm'] = round(eps_val, 2)
    metrics_dict['eps_normalized'] = round(eps_val, 2) if is_normalized else None
    metrics_dict['is_normalized'] = is_normalized
    
    return {
        "valuation_metrics": ValuationMetrics(**metrics_dict),
        "investigation_tasks": [],
        "error": None
    }