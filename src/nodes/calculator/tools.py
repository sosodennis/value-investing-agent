"""
Node B: Calculator - Private Tools (Refactored / Enterprise Grade)

Responsibilities:
1. Fetch raw market data (yfinance) without subjective logic.
2. Extract financial data.
3. Perform pure mathematical projections (DCF core).
"""

import yfinance as yf
import pandas as pd
import numpy as np

def get_market_data_raw(ticker: str):
    """
    [Fetcher] 只負責從 yfinance 搬運原始數據，不做主觀判斷。
    """
    try:
        stock = yf.Ticker(ticker)
        # Fetch 5 days to handle weekends/holidays
        hist = stock.history(period="5d")
        if hist.empty: return None
        
        current_price = float(hist["Close"].iloc[-1])
        info = stock.info
        bs = stock.balance_sheet
        is_stmt = stock.financials
        cf = stock.cashflow
        
        # 基礎數據提取
        shares = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")
        if not shares and market_cap: shares = market_cap / current_price
        if not market_cap and shares: market_cap = current_price * shares
        
        # 提取財務報表最新日期
        bs_date = bs.columns[0] if not bs.empty else None
        is_date = is_stmt.columns[0] if not is_stmt.empty else None
        cf_date = cf.columns[0] if not cf.empty else None

        # 提取原始數值 (Raw Values)
        # 1. Debt & Cash
        total_debt = 0.0
        cash_eq = 0.0
        if bs_date:
            total_debt = float(bs.loc['Total Debt', bs_date]) if 'Total Debt' in bs.index else 0.0
            cash_eq = float(bs.loc['Cash And Cash Equivalents', bs_date]) if 'Cash And Cash Equivalents' in bs.index else 0.0
            
        # 2. EBIT & Interest (For Coverage)
        ebit = 0.0
        interest_expense = 0.0
        if is_date:
            if 'EBIT' in is_stmt.index: ebit = float(is_stmt.loc['EBIT', is_date])
            elif 'Operating Income' in is_stmt.index: ebit = float(is_stmt.loc['Operating Income', is_date])
            
            if 'Interest Expense' in is_stmt.index: 
                interest_expense = abs(float(is_stmt.loc['Interest Expense', is_date]))
            elif 'Interest Expense Non Operating' in is_stmt.index:
                interest_expense = abs(float(is_stmt.loc['Interest Expense Non Operating', is_date]))

        # 3. SBC & FCF
        sbc = 0.0
        fcf_ttm = info.get("freeCashflow")
        if cf_date:
            # 嘗試提取 SBC
            for key in ['Stock Based Compensation', 'Share Based Compensation', 'Issuance Of Stock']:
                if key in cf.index:
                    val = cf.loc[key, cf_date]
                    if val is not None: sbc = abs(float(val))
                    break
        
        # 4. Risk Free Rate (Robust)
        rf = 0.042 # Default
        try:
            tnx = yf.Ticker("^TNX").history(period="5d")
            if not tnx.empty: rf = float(tnx["Close"].iloc[-1]) / 100
        except: pass

        # 5. Revenue Growth (for SaaS Rule of 40)
        # yfinance 提供的 revenueGrowth 通常是季度同比增長 (Year-over-Year)
        revenue_growth = info.get("revenueGrowth")

        return {
            "price": current_price,
            "market_cap": float(market_cap) if market_cap else 0.0,
            "shares_outstanding": float(shares) if shares else 0.0,
            "sector": info.get("sector", "Unknown"),
            "beta": info.get("beta", 1.0),
            "pe_ratio": info.get("trailingPE"),
            "peg_ratio": info.get("pegRatio"),
            "risk_free_rate": rf,
            "total_debt": total_debt,
            "cash_and_equivalents": cash_eq,
            "ebit": ebit,
            "interest_expense": interest_expense,
            "sbc": sbc,
            "fcf_ttm": float(fcf_ttm) if fcf_ttm else 0.0,
            "roe": info.get("returnOnEquity"),
            "payout_ratio": info.get("payoutRatio"),
            "revenue_growth": float(revenue_growth) if revenue_growth else None,  # 新增字段
            "fcf_data_source": "yfinance_info" if fcf_ttm else "calculated"
        }
    except Exception as e:
        print(f"❌ [Data Fetcher] Error: {e}")
        return None

def get_normalized_income_data(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        fin_df = stock.financials
        if fin_df.empty: return None
        latest_date = fin_df.columns[0]
        
        normalized_income = 0.0
        use_normalized = False
        if 'Normalized Income' in fin_df.index:
            normalized_income = fin_df.loc['Normalized Income', latest_date]
            use_normalized = True
        elif 'Net Income' in fin_df.index:
            normalized_income = fin_df.loc['Net Income', latest_date]
        
        raw_net_income = fin_df.loc['Net Income', latest_date] if 'Net Income' in fin_df.index else normalized_income
        
        return {
            "normalized_income": float(normalized_income), 
            "use_normalized": use_normalized,
            "raw_net_income": float(raw_net_income)
        }
    except: return None

def calculate_historical_growth(ticker: str) -> float:
    try:
        stock = yf.Ticker(ticker)
        fin_df = stock.financials
        if fin_df.empty or len(fin_df.columns) < 2: return None
        
        target_row = None
        if 'Normalized Income' in fin_df.index: target_row = 'Normalized Income'
        elif 'Net Income' in fin_df.index: target_row = 'Net Income'
        if not target_row: return None
            
        values = fin_df.loc[target_row].values[::-1]
        values = [v for v in values if v is not None and not np.isnan(v)]
        if len(values) < 4 or values[0] <= 0: return None
        if values[-1] <= 0: return -0.05
            
        return float((values[-1] / values[0]) ** (1 / (len(values) - 1)) - 1)
    except: return None

def calculate_dcf(
    start_value: float,
    shares_outstanding: float,
    net_debt: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float = 0.025,
    projection_years: int = 10,
    fade_start_year: int = 5,
    exit_multiple: float = None, # [New] 接收退出倍數
    method: str = "FCF") -> dict:
    """
    純數學引擎：計算 DCF，包含 Linear Fade Growth 和 Dual Terminal Value。
    """
    if shares_outstanding == 0 or start_value is None:
        return {"intrinsic_value": 0.0}
    
    # 1. Cash Flow Projection with Fade
    future_flows = []
    current_val = start_value
    current_growth = growth_rate
    decay_step = 0.0
    
    if projection_years > fade_start_year:
        decay_step = (growth_rate - terminal_growth) / (projection_years - fade_start_year + 1)

    for year in range(1, projection_years + 1):
        if year > fade_start_year:
            current_growth = max(terminal_growth, current_growth - decay_step)
        
        current_val = current_val * (1 + current_growth)
        pv = current_val / ((1 + discount_rate) ** year)
        future_flows.append({"val": current_val, "pv": pv})
    
    pv_explicit = sum(f["pv"] for f in future_flows)
    
    # 2. Terminal Value (Dual Method)
    last_val = future_flows[-1]["val"]
    
    # Method A: Gordon Growth
    final_disc = max(discount_rate, terminal_growth + 0.01) # Math safety
    tv_gordon = (last_val * (1 + terminal_growth)) / (final_disc - terminal_growth)
    
    # Method B: Exit Multiple
    tv_exit = tv_gordon # Default fallback
    use_dual = False
    
    if exit_multiple is not None:
        tv_exit = last_val * exit_multiple
        use_dual = True
        
    # 取平均 (Blended TV)
    terminal_value_raw = (tv_gordon + tv_exit) / 2 if use_dual else tv_gordon
    
    pv_terminal = terminal_value_raw / ((1 + discount_rate) ** projection_years)
    
    # 3. Sum & Equity Value
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value - net_debt # Net Debt 可為正或負
    intrinsic_value = max(0, equity_value / shares_outstanding)
    
    # Debug note
    tv_note = f"Gordon=${tv_gordon/1e9:.1f}B"
    if use_dual:
        tv_note = f"Avg(Gordon=${tv_gordon/1e9:.1f}B, Exit={exit_multiple:.1f}x=${tv_exit/1e9:.1f}B)"
    
    tv_conc = pv_terminal / (pv_explicit + pv_terminal) if (pv_explicit + pv_terminal) > 0 else 0
    
    return {
        "intrinsic_value": round(intrinsic_value, 2),
        "tv_concentration": round(tv_conc, 2),
        "note": f"{method} | TV: {tv_note}"
    }