"""
Node B: Calculator - Business Logic Layer

Responsibilities:
1. Determine Growth Rates (Hist vs PEG vs SGR).
2. Calculate Discount Rates (WACC, Ke, Beta Adj).
3. Determine Exit Multiples (Terminal Value Logic).
4. Centralize all subjective decision trees.
"""

import math

def determine_growth_rate(
    hist_growth: float, 
    peg_ratio: float, 
    pe_ratio: float, 
    roe: float, 
    payout_ratio: float) -> dict:
    """
    [Logic] 決定最終使用的增長率。
    策略：PEG (共識) > SGR (內生) > Historical (歷史)。
    """
    # 1. 計算 SGR
    sgr = None
    if roe is not None:
        retention = 1 - (payout_ratio if payout_ratio else 0.0)
        calc_sgr = roe * retention
        # Cap SGR for giants like Apple to avoid infinite growth assumptions
        if calc_sgr > 0.20: calc_sgr = 0.20
        if calc_sgr > 0.02: sgr = calc_sgr

    # 2. 計算 PEG Implied
    peg_growth = None
    if peg_ratio and peg_ratio > 0 and pe_ratio:
        implied = (pe_ratio / peg_ratio) / 100
        if 0.02 < implied < 0.30: peg_growth = implied
        
    # 3. 決策樹
    final_rate = 0.10
    source = "Default"
    
    if peg_growth:
        if sgr and peg_growth > sgr * 1.5:
            final_rate = (peg_growth + sgr) / 2
            source = "Blended (PEG & SGR)"
        else:
            final_rate = peg_growth
            source = "PEG Implied"
    elif sgr:
        if hist_growth and hist_growth < 0.05:
            final_rate = sgr
            source = "SGR (Hist. Data Weak)"
        elif hist_growth:
            final_rate = (sgr + hist_growth) / 2
            source = "Blended (SGR & Hist)"
        else:
            final_rate = sgr
            source = "SGR"
    elif hist_growth:
        final_rate = hist_growth
        source = "Historical CAGR"
        
    # 4. Cap & Floor (GuruFocus Rule)
    final_capped = final_rate
    msg = ""
    if final_rate > 0.20: 
        final_capped = 0.20
        msg = "(Capped 20%)"
    elif final_rate < 0.05:
        final_capped = 0.05
        msg = "(Floored 5%)"
        
    return {
        "rate": final_capped,
        "source": f"{source} {msg}",
        "raw_rate": final_rate
    }

def calculate_discount_rates(
    rf: float, 
    beta: float, 
    market_cap: float, 
    ebit: float, 
    interest_expense: float,
    total_debt: float, 
    market_equity: float) -> dict:
    """
    [Logic] 計算 Ke (Cost of Equity) 和 WACC。包含 Beta Adjustment 和 Spread Logic。
    """
    # 1. Adjusted Beta Logic (Blume's + Mega Cap)
    market_cap_b = market_cap / 1e9
    adj_beta = (0.67 * beta) + 0.33 # Blume's Adjustment
    if market_cap_b > 200: adj_beta = min(adj_beta, 1.50) # Mega Cap Cap
    
    # 2. Cost of Equity (Ke)
    erp = 0.06 # Equity Risk Premium
    ke = rf + (adj_beta * erp)
    ke = max(ke, rf + 0.055) # Hurdle Rate Floor
    
    # 3. Cost of Debt (Kd)
    int_coverage = 100.0
    if interest_expense > 0: int_coverage = ebit / interest_expense
    
    # Dynamic Spread based on coverage
    spread = 0.015
    if int_coverage > 8.5: spread = 0.010
    elif int_coverage < 2.0: spread = 0.040
    
    kd = rf + spread
    tax_rate = 0.21
    
    # 4. WACC
    total_val = market_equity + total_debt
    wacc = ke # Fallback
    if total_val > 0:
        we = market_equity / total_val
        wd = total_debt / total_val
        wacc = (we * ke) + (wd * kd * (1 - tax_rate))
        wacc = max(wacc, rf + 0.02) # Floor
        
    return {
        "wacc": wacc,
        "ke": ke,
        "adj_beta": adj_beta,
        "int_coverage": int_coverage
    }

def determine_exit_multiple(current_pe: float, growth_rate: float, sector: str = "Unknown") -> dict:
    """
    [Logic] 決定 10 年後的退出倍數 (Exit Multiple)。
    策略：
    1. 均值回歸 (Mean Reversion)：假設 10 年後估值會比現在低 (打折)。
    2. 絕對限制 (Caps/Floors)：防止過度樂觀或悲觀。
    """
    # 1. 獲取基準 (Base)
    # 如果當前 PE 無效 (負值或 None)，根據增長率估算一個默認值
    base_pe = 15.0
    if current_pe and current_pe > 0:
        base_pe = current_pe
    else:
        # Fallback Logic: Growth 10% -> PE 20x (粗略估計 PEG=2)
        base_pe = max(10.0, growth_rate * 100 * 2)

    # 2. 安全邊際打折 (Safety Margin)
    # 假設 10 年後不再是當紅炸子雞，估值倍數收縮 25%
    target_multiple = base_pe * 0.75

    # 3. 行業與絕對限制 (Sector Caps & Floors)
    cap = 25.0
    floor = 10.0
    
    sector_lower = str(sector).lower()
    if "bank" in sector_lower or "insurance" in sector_lower or "energy" in sector_lower or "financial" in sector_lower:
        cap = 15.0
        floor = 8.0
    elif "technology" in sector_lower or "semiconductor" in sector_lower:
        cap = 28.0 # 給予科技巨頭稍微高一點的寬容度
        
    # 應用限制
    final_multiple = max(floor, min(target_multiple, cap))
    
    return {
        "multiple": final_multiple,
        "reason": f"Current PE {base_pe:.1f}x -> Discounted 25% -> Capped/Floored ({floor}x-{cap}x)"
    }