"""
Node B: Calculator - Private Tools (Enhanced Version)

This module contains financial calculation utilities:
1. Market data fetching (yfinance) - Enhanced with Debt/Cash extraction
2. Valuation ratio calculations (P/E, Margins, etc.)
3. Financial data validation
4. Intrinsic Value Calculation (Dual-Track DCF: FCF & Earnings)
5. Historical Growth Calculation (CAGR based on 4-year financials)

All calculations are pure Python - no LLM involvement to ensure accuracy.
"""

import yfinance as yf
import pandas as pd
import numpy as np

def get_market_data(ticker: str):
    """
    獲取全面的市場與財務數據，包括資產負債表數據以支持精確估值。
    """
    try:
        stock = yf.Ticker(ticker)
        
        # --- 1. 基礎市場數據 (Price & Market Cap) ---
        hist = stock.history(period="1d")
        if hist.empty:
            raise ValueError(f"無法獲取 {ticker} 的股價數據")
        
        current_price = float(hist["Close"].iloc[-1])
        info = stock.info
        
        # 優先使用 info 獲取流通股數，失敗則用市值反推 (單位：絕對值)
        shares = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")
        
        if not shares and market_cap:
            shares = market_cap / current_price
        
        if not market_cap and shares:
            market_cap = current_price * shares

        # --- 2. 關鍵財務數據 (從報表獲取，比 info 更可靠) ---
        # 獲取 Balance Sheet (用於計算 Net Debt 和 TBV)
        bs = stock.balance_sheet
        total_debt = 0.0
        cash_and_equivalents = 0.0
        tangible_book_value = 0.0
        
        if not bs.empty:
            latest_bs_date = bs.columns[0] # 取最近一期
            
            # (A) 債務與現金
            for key in ['Total Debt', 'Total Liab', 'Long Term Debt']:
                if key in bs.index:
                    total_debt = float(bs.loc[key, latest_bs_date])
                    break
            
            for key in ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']:
                if key in bs.index:
                    cash_and_equivalents = float(bs.loc[key, latest_bs_date])
                    break
            
            # (B) Tangible Book Value
            if 'Tangible Book Value' in bs.index:
                tangible_book_value = float(bs.loc['Tangible Book Value', latest_bs_date])
            elif 'Total Assets' in bs.index and 'Total Liab' in bs.index:
                assets = bs.loc['Total Assets', latest_bs_date]
                liabs = bs.loc['Total Liab', latest_bs_date]
                intangibles = bs.loc['Intangible Assets', latest_bs_date] if 'Intangible Assets' in bs.index else 0
                goodwill = bs.loc['Goodwill', latest_bs_date] if 'Goodwill' in bs.index else 0
                tangible_book_value = float(assets - liabs - intangibles - goodwill)
        
        # 獲取 Cash Flow (用於計算真實 FCF)
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

        if fcf_ttm is None:
            fcf_ttm = info.get("freeCashflow")

        # --- 3. 風險指標 ---
        risk_free_rate = 0.042
        try:
            treasury = yf.Ticker("^TNX")
            tnx_hist = treasury.history(period="1d")
            if not tnx_hist.empty:
                risk_free_rate = float(tnx_hist["Close"].iloc[-1]) / 100
        except:
            pass

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
            "tangible_book_value": tangible_book_value
        }
    except Exception as e:
        print(f"❌ [Calculator Tool] yfinance error: {e}")
        return None


def get_normalized_income_data(ticker: str) -> dict:
    """
    從 yfinance 的財務報表中提取標準化淨利 (Normalized Income)。
    """
    try:
        stock = yf.Ticker(ticker)
        fin_df = stock.financials
        
        if fin_df.empty:
            return None
        
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
            "raw_net_income": float(raw_net_income),
            "use_normalized": use_normalized
        }
    except Exception as e:
        print(f"❌ [Tool Error] Financial data error: {e}")
        return None

def calculate_historical_growth(ticker: str) -> float:
    """
    [New] 計算過去 4 年的歷史增長率 (CAGR)。
    優先使用 'Normalized Income'，其次使用 'Net Income'。
    
    Returns:
        float: CAGR (e.g., 0.15 for 15%), or None if calculation not possible.
    """
    try:
        stock = yf.Ticker(ticker)
        fin_df = stock.financials
        
        if fin_df.empty or len(fin_df.columns) < 2:
            return None
        
        # 確定使用的數據行
        target_row = 'Net Income'
        if 'Normalized Income' in fin_df.index:
            target_row = 'Normalized Income'
        elif 'Net Income' not in fin_df.index:
            return None
            
        # 獲取數據序列 (從新到舊 -> 轉為從舊到新)
        # yfinance columns are dates [2023, 2022, 2021, 2020]
        values = fin_df.loc[target_row].values
        values = values[::-1] # Reverse to [Oldest, ..., Newest]
        
        # 過濾掉 None/NaN
        values = [v for v in values if v is not None and not np.isnan(v)]
        
        if len(values) < 2:
            return None
            
        start_val = values[0]
        end_val = values[-1]
        years = len(values) - 1
        
        # CAGR 公式: (End / Start)^(1/n) - 1
        # 注意：如果 Start 值為負數，CAGR 數學上無意義，返回 None
        if start_val <= 0:
            return None
            
        if end_val <= 0:
            # 如果變為負數，說明大幅衰退，給一個負的增長率
            return -0.20 # 假設衰退
            
        cagr = (end_val / start_val) ** (1 / years) - 1
        return float(cagr)
        
    except Exception as e:
        print(f"⚠️ [Growth Tool] CAGR Calculation failed: {e}")
        return None

def calculate_metrics(financials: dict, market_data: dict) -> dict:
    """
    執行純數學計算（雙軌 P/E 驗證）。
    """
    revenue_m = financials.get("total_revenue", 0)
    net_income_m = financials.get("net_income", 0)
    market_cap = market_data.get("market_cap", 0)
    price = market_data.get("price", 0)
    
    margin = 0.0
    if revenue_m > 0:
        margin = (net_income_m / revenue_m) * 100
    
    pe_ratio_fy = 0.0
    net_income_absolute = net_income_m * 1_000_000
    if net_income_absolute > 0:
        pe_ratio_fy = market_cap / net_income_absolute
    
    pe_ratio_ttm = market_data.get("trailing_pe")
    
    primary_pe = pe_ratio_ttm if pe_ratio_ttm else pe_ratio_fy
    
    trend_insight = "Stable"
    if pe_ratio_ttm and pe_ratio_fy > 0:
        diff_pct = (pe_ratio_ttm - pe_ratio_fy) / pe_ratio_fy
        if diff_pct < -0.05:
            trend_insight = f"Earnings Improving (TTM P/E {pe_ratio_ttm:.1f} < FY P/E {pe_ratio_fy:.1f})"
        elif diff_pct > 0.05:
            trend_insight = f"Earnings Declining (TTM P/E {pe_ratio_ttm:.1f} > FY P/E {pe_ratio_fy:.1f})"
    
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
    start_value: float,           # FCF 或 Net Income (絕對值)
    shares_outstanding: float,
    total_debt: float,            # 絕對值
    cash_and_equivalents: float,  # 絕對值
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth: float = 0.03,
    projection_years: int = 10,
    method: str = "FCF"           # "FCF" 或 "EPS"
) -> dict:
    """
    通用 DCF 模型 (支持 FCF-based 和 Earnings-based)。
    """
    if shares_outstanding == 0 or start_value is None:
        return {"intrinsic_value": 0.0, "details": "Invalid Data"}
    
    print(f"🧮 [DCF-{method}] Base: ${start_value/1e9:.2f}B, Growth: {growth_rate:.1%}, Discount: {discount_rate:.1%}")
    
    # 1. 預測未來現金流 (Stage 1)
    future_flows = []
    current_val = start_value
    for i in range(1, projection_years + 1):
        current_val = current_val * (1 + growth_rate)
        future_flows.append(current_val)
    
    # 2. 計算終值 (Terminal Value)
    last_val = future_flows[-1]
    terminal_value = (last_val * (1 + terminal_growth)) / (discount_rate - terminal_growth)
    
    # 3. 折現 (PV)
    pv_flows = 0.0
    for i, val in enumerate(future_flows):
        pv_flows += val / ((1 + discount_rate) ** (i + 1))
    
    pv_terminal = terminal_value / ((1 + discount_rate) ** projection_years)
    
    # 4. 計算折現總和 (Discounted Sum)
    discounted_sum = pv_flows + pv_terminal
    
    # 5. 根據方法處理債務
    equity_value = 0.0
    
    if method.upper() == "FCF":
        equity_value = discounted_sum - total_debt + cash_and_equivalents
        note = "Adjusted for Net Debt"
    else:
        equity_value = discounted_sum 
        note = "Direct Equity Value"
    
    # 6. 計算每股內在價值
    intrinsic_value = equity_value / shares_outstanding
    intrinsic_value = max(0.0, intrinsic_value)
    
    return {
        "intrinsic_value": round(intrinsic_value, 2),
        "discounted_sum": discounted_sum,
        "equity_value": equity_value,
        "method": method,
        "note": note
    }