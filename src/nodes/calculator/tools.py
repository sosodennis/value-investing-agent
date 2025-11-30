"""
Node B: Calculator - Private Tools (Enterprise Grade)

This module contains financial calculation utilities:
1. Market data fetching (yfinance) - Enhanced with Sector, Interest Coverage, TBV, Robust Risk-Free Rate, ROE/Payout
2. Valuation ratio calculations
3. Intrinsic Value Calculation (Enterprise DCF with Growth Decay)
4. Historical Growth Calculation (Smart Normalized Logic)

All calculations are pure Python.
"""

import yfinance as yf
import pandas as pd
import numpy as np

def get_market_data(ticker: str):
    """
    獲取全面的市場與財務數據，新增 Sector, Interest Coverage, ROE, Payout Ratio。
    包含針對 Risk Free Rate 的穩健獲取邏輯。
    """
    try:
        stock = yf.Ticker(ticker)
        
        # --- 1. 基礎數據 ---
        hist = stock.history(period="1d")
        if hist.empty:
            raise ValueError(f"無法獲取 {ticker} 的股價數據")
        
        current_price = float(hist["Close"].iloc[-1])
        info = stock.info
        
        shares = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")
        if not shares and market_cap: shares = market_cap / current_price
        if not market_cap and shares: market_cap = current_price * shares

        # [New] 獲取行業資訊
        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "Unknown")

        # --- 2. 財務數據 (BS & IS) ---
        bs = stock.balance_sheet
        income_stmt = stock.financials
        
        total_debt = 0.0
        cash_and_equivalents = 0.0
        tangible_book_value = 0.0
        interest_coverage = None 
        
        latest_date = None
        
        # Balance Sheet Data
        if not bs.empty:
            latest_date = bs.columns[0]
            # 債務與現金
            for key in ['Total Debt', 'Total Liab', 'Long Term Debt']:
                if key in bs.index:
                    total_debt = float(bs.loc[key, latest_date])
                    break
            for key in ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']:
                if key in bs.index:
                    cash_and_equivalents = float(bs.loc[key, latest_date])
                    break
            # TBV
            if 'Tangible Book Value' in bs.index:
                tangible_book_value = float(bs.loc['Tangible Book Value', latest_date])
            elif 'Total Assets' in bs.index and 'Total Liab' in bs.index:
                assets = bs.loc['Total Assets', latest_date]
                liabs = bs.loc['Total Liab', latest_date]
                intangibles = bs.loc['Intangible Assets', latest_date] if 'Intangible Assets' in bs.index else 0
                goodwill = bs.loc['Goodwill', latest_date] if 'Goodwill' in bs.index else 0
                tangible_book_value = float(assets - liabs - intangibles - goodwill)

        # Income Statement Data for Interest Coverage
        if not income_stmt.empty:
            is_date = income_stmt.columns[0]
            try:
                # 獲取 EBIT
                ebit = 0.0
                if 'EBIT' in income_stmt.index:
                    ebit = float(income_stmt.loc['EBIT', is_date])
                elif 'Operating Income' in income_stmt.index:
                    ebit = float(income_stmt.loc['Operating Income', is_date])
                
                # 獲取利息支出 (通常是負數，取絕對值)
                interest_expense = 0.0
                if 'Interest Expense' in income_stmt.index:
                    interest_expense = abs(float(income_stmt.loc['Interest Expense', is_date]))
                elif 'Interest Expense Non Operating' in income_stmt.index:
                    interest_expense = abs(float(income_stmt.loc['Interest Expense Non Operating', is_date]))
                
                # 計算覆蓋率
                if interest_expense > 0:
                    interest_coverage = ebit / interest_expense
                else:
                    interest_coverage = 100.0 # 無債務或無利息，視為極其安全
                    
            except Exception as e:
                print(f"⚠️ [Data Tool] Interest Coverage calc failed: {e}")

        # --- 3. Cash Flow ---
        cf = stock.cashflow
        fcf_ttm = None
        if not cf.empty:
            latest_cf_date = cf.columns[0]
            if 'Free Cash Flow' in cf.index:
                fcf_ttm = float(cf.loc['Free Cash Flow', latest_cf_date])
            elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                ocf = cf.loc['Operating Cash Flow', latest_cf_date]
                capex = cf.loc['Capital Expenditure', latest_cf_date]
                fcf_ttm = float(ocf + capex)

        if fcf_ttm is None: fcf_ttm = info.get("freeCashflow")

        # --- 4. Risk (Robust Fetch) ---
        risk_free_rate = 0.042 # Default fallback (4.2%)
        try:
            treasury = yf.Ticker("^TNX")
            tnx_hist = treasury.history(period="5d")
            if not tnx_hist.empty:
                risk_free_rate = float(tnx_hist["Close"].iloc[-1]) / 100
        except Exception as e:
            print(f"⚠️ [Risk Tool] Failed to fetch ^TNX, using default {risk_free_rate:.1%}: {e}")

        # --- 5. [New] SGR Metrics ---
        roe = info.get("returnOnEquity")
        payout_ratio = info.get("payoutRatio")
        
        # Fallback for Payout Ratio if ROE is positive
        if payout_ratio is None and roe and roe > 0:
            payout_ratio = 0.0 # Assume full retention if unknown

        return {
            "price": current_price,
            "market_cap": float(market_cap) if market_cap else 0.0,
            "shares_outstanding": float(shares) if shares else 0.0,
            "peg_ratio": info.get("pegRatio"),
            "beta": info.get("beta"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "risk_free_rate": risk_free_rate,
            "fcf_ttm": float(fcf_ttm) if fcf_ttm else 0.0,
            "total_debt": total_debt,
            "cash_and_equivalents": cash_and_equivalents,
            "tangible_book_value": tangible_book_value,
            "sector": sector,               
            "industry": industry,           
            "interest_coverage": interest_coverage,
            "roe": roe,                     # [New]
            "payout_ratio": payout_ratio    # [New]
        }
    except Exception as e:
        print(f"❌ [Calculator Tool] yfinance error: {e}")
        return None

def get_normalized_income_data(ticker: str) -> dict:
    """從損益表中提取標準化淨利"""
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
        return {"normalized_income": float(normalized_income), "raw_net_income": float(raw_net_income), "use_normalized": use_normalized}
    except: return None

def calculate_historical_growth(ticker: str) -> float:
    """
    計算 4 年 CAGR，強制優先使用 Normalized Income 以過濾一次性事件。
    """
    try:
        stock = yf.Ticker(ticker)
        fin_df = stock.financials
        
        if fin_df.empty or len(fin_df.columns) < 2: return None
        
        # --- 關鍵修改：嚴格優先使用 Normalized Income ---
        target_row = None
        if 'Normalized Income' in fin_df.index:
            target_row = 'Normalized Income'
        elif 'Net Income Common Stockholders' in fin_df.index:
            target_row = 'Net Income Common Stockholders'
        elif 'Net Income' in fin_df.index:
            target_row = 'Net Income'
            
        if not target_row: return None
            
        # 獲取數據 (從舊到新)
        values = fin_df.loc[target_row].values[::-1]
        values = [v for v in values if v is not None and not np.isnan(v)]
        
        # 至少要有4年數據才準
        if len(values) < 4: return None
            
        start_val = values[0]
        end_val = values[-1]
        
        if start_val <= 0: return None
        if end_val <= 0: return -0.05 
            
        years = len(values) - 1
        cagr = (end_val / start_val) ** (1 / years) - 1
        
        return float(cagr)
    except Exception as e:
        print(f"⚠️ [Growth Tool] Error: {e}")
        return None

def calculate_metrics(financials: dict, market_data: dict) -> dict:
    """基礎比率計算"""
    revenue_m = financials.get("total_revenue", 0)
    net_income_m = financials.get("net_income", 0)
    market_cap = market_data.get("market_cap", 0)
    price = market_data.get("price", 0)
    
    margin = (net_income_m / revenue_m * 100) if revenue_m > 0 else 0
    pe_ratio_fy = market_cap / (net_income_m * 1_000_000) if net_income_m > 0 else 0
    pe_ratio_ttm = market_data.get("trailing_pe")
    primary_pe = pe_ratio_ttm if pe_ratio_ttm else pe_ratio_fy
    
    trend_insight = "Stable"
    if pe_ratio_ttm and pe_ratio_fy > 0:
        diff = (pe_ratio_ttm - pe_ratio_fy) / pe_ratio_fy
        if diff < -0.05: trend_insight = "Earnings Improving"
        elif diff > 0.05: trend_insight = "Earnings Declining"
    
    status = "Fair Value"
    if primary_pe > 0:
        if primary_pe < 15: status = "Undervalued"
        elif primary_pe > 35: status = "Overvalued"
    
    return {
        "market_cap": market_cap / 1_000_000,
        "current_price": price,
        "net_profit_margin": round(margin, 2),
        "pe_ratio": round(primary_pe, 2),
        "pe_ratio_ttm": round(pe_ratio_ttm, 2) if pe_ratio_ttm else None,
        "pe_ratio_fy": round(pe_ratio_fy, 2),
        "pe_trend_insight": trend_insight,
        "valuation_status": status
    }

def calculate_dcf(
    start_value: float,
    shares_outstanding: float,
    total_debt: float,
    cash_and_equivalents: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float = 0.025, 
    projection_years: int = 10,
    fade_start_year: int = 5,       
    method: str = "FCF"
) -> dict:
    """
    Enterprise Grade DCF:
    1. Supports Linear Growth Decay (Fade).
    2. Calculates TV Concentration (Risk Metric).
    """
    if shares_outstanding == 0 or start_value is None:
        return {"intrinsic_value": 0.0, "details": "Invalid Data"}
    
    print(f"🧮 [DCF-{method}] Base:${start_value/1e9:.2f}B, Initial Growth:{growth_rate:.1%}, Discount:{discount_rate:.1%}")
    
    # 1. 預測現金流 (含 Fade 邏輯)
    future_flows = []
    current_val = start_value
    current_growth = growth_rate
    
    # 計算每年的衰減量
    decay_step = 0.0
    if projection_years > fade_start_year:
        # 目標：在第 10 年結束時，增長率接近 terminal_growth
        decay_step = (growth_rate - terminal_growth) / (projection_years - fade_start_year + 1)

    for year in range(1, projection_years + 1):
        if year > fade_start_year:
            # 確保不會低於 terminal_growth
            current_growth = max(terminal_growth, current_growth - decay_step)
        
        current_val = current_val * (1 + current_growth)
        
        # 折現因子
        discount_factor = (1 + discount_rate) ** year
        pv = current_val / discount_factor
        
        future_flows.append({
            "year": year,
            "val": current_val,
            "growth_used": current_growth,
            "pv": pv
        })
    
    pv_explicit = sum(f["pv"] for f in future_flows)
    
    # 2. 終值計算 (Terminal Value)
    last_val = future_flows[-1]["val"]
    
    # 安全檢查：WACC 必須 > Terminal Growth
    final_discount_rate = discount_rate
    if final_discount_rate <= terminal_growth:
        final_discount_rate = terminal_growth + 0.02
        print(f"⚠️ [DCF Adj] Discount rate too low, adjusted to {final_discount_rate:.1%} for TV calc")
        
    terminal_value = (last_val * (1 + terminal_growth)) / (final_discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** projection_years)
    
    # 3. 匯總
    discounted_sum = pv_explicit + pv_terminal
    
    # 4. 根據方法處理債務
    equity_value = 0.0
    if method.upper() == "FCF":
        equity_value = discounted_sum - total_debt + cash_and_equivalents
        note = "Adjusted for Net Debt"
    else:
        equity_value = discounted_sum 
        note = "Direct Equity Value"
    
    intrinsic_value = max(0.0, equity_value / shares_outstanding)
    
    # 計算終值集中度
    tv_concentration = 0.0
    if discounted_sum > 0:
        tv_concentration = pv_terminal / discounted_sum
        
    return {
        "intrinsic_value": round(intrinsic_value, 2),
        "discounted_sum": discounted_sum,
        "equity_value": equity_value,
        "tv_concentration": round(tv_concentration, 2),
        "method": method,
        "note": note
    }