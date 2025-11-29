"""
Node B: Calculator - Private Tools

This module contains financial calculation utilities:
1. Market data fetching (yfinance)
2. Valuation ratio calculations (P/E, Margins, etc.)
3. Financial data validation
4. Normalized income extraction (NRI handling)

All calculations are pure Python - no LLM involvement to ensure accuracy.
"""

import yfinance as yf
import pandas as pd


def get_market_data(ticker: str):
    """
    獲取實時市場數據：股價、市值、流通股數、PEG、Beta、以及無風險利率。
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        dict: Contains 'price', 'market_cap', 'shares_outstanding', 'peg_ratio', 'beta', 'risk_free_rate', or None if failed
    """
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 基礎數據
        # 獲取最新價格 (history 比 info 更快更穩定)
        hist = stock.history(period="1d")
        if hist.empty:
            raise ValueError(f"無法獲取 {ticker} 的股價數據")
        
        current_price = float(hist["Close"].iloc[-1])
        
        # 獲取市值 (Market Cap)
        # 注意：info 接口有時會慢或失敗，生產環境建議加緩存或重試
        info = stock.info
        market_cap = info.get("marketCap")
        shares = info.get("sharesOutstanding")
        
        if not market_cap:
            # 如果拿不到市值，嘗試用 Price * Shares Outstanding 估算
            if shares:
                market_cap = current_price * shares
            else:
                raise ValueError("無法獲取市值數據")
        
        # 獲取流通股數
        shares_outstanding = shares
        if not shares_outstanding:
            # 如果拿不到，用市值和股價反推
            if market_cap and current_price:
                shares_outstanding = market_cap / current_price
            else:
                shares_outstanding = 0
        
        # 2. [New] 獲取 PEG Ratio (這是計算增長率的關鍵)
        # yfinance 的 info 裡通常有 'pegRatio'
        peg_ratio = info.get("pegRatio")
        
        # 3. [New] 獲取 Beta (用於計算 WACC)
        beta = info.get("beta")
        
        # 4. [New] 獲取 TTM P/E 和 Forward P/E
        trailing_pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        
        # 5. [New] 獲取無風險利率 (^TNX)
        # 這是 CBOE 10-Year Treasury Note Yield Index
        try:
            treasury = yf.Ticker("^TNX")
            tnx_hist = treasury.history(period="1d")
            if not tnx_hist.empty:
                # Yahoo 返回的是 4.25 (代表 4.25%)，我們需要轉為 0.0425
                risk_free_rate = float(tnx_hist["Close"].iloc[-1]) / 100
            else:
                risk_free_rate = 0.042  # 獲取失敗時的默認值 (4.2%)
        except Exception as e:
            print(f"⚠️ [Tool] 無法獲取 ^TNX，使用默認值: {e}")
            risk_free_rate = 0.042
        
        # 6. [New] 獲取 TTM FCF 相關數據
        # yfinance 通常在 info 中提供 'freeCashflow' (TTM)
        # 如果沒有，我們嘗試獲取 'operatingCashflow' (TTM) 和 'capitalExpenditures' (TTM)
        fcf_ttm = info.get("freeCashflow")
        ocf_ttm = info.get("operatingCashflow")
        
        # 注意：yfinance 的 CapEx 通常在 info 裡沒有直接的 TTM 字段
        # 有時需要容錯。如果 fcf_ttm 存在，直接用它最準確。
        
        return {
            "price": current_price,
            "market_cap": float(market_cap),
            "shares_outstanding": float(shares_outstanding),
            "peg_ratio": peg_ratio if peg_ratio else None,
            "beta": beta if beta else None,
            "trailing_pe": trailing_pe if trailing_pe else None,
            "forward_pe": forward_pe if forward_pe else None,
            "risk_free_rate": risk_free_rate,
            # 新增 TTM 數據
            "fcf_ttm": float(fcf_ttm) if fcf_ttm else None,  # 單位：絕對值 (Bytes)
            "ocf_ttm": float(ocf_ttm) if ocf_ttm else None  # 單位：絕對值 (Bytes)
        }
    except Exception as e:
        print(f"❌ [Calculator Tool] yfinance error: {e}")
        return None


def get_normalized_income_data(ticker: str) -> dict:
    """
    從 yfinance 的財務報表中提取標準化淨利 (Normalized Income)。
    如果沒有，回退使用普通 Net Income。
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        dict: Contains 'normalized_income', 'raw_net_income', 'shares_outstanding', 'use_normalized', or None if failed
    """
    try:
        stock = yf.Ticker(ticker)
        
        # 獲取年度損益表 (Financials)
        fin_df = stock.financials
        
        if fin_df.empty:
            print(f"⚠️ [Tool] 無法獲取財務報表數據")
            return None
        
        # yfinance 的 index 可能是 'Normalized Income' 或 'Net Income Continuous Operations'
        # 我們嘗試獲取最新一年的數據 (列是日期，取第一列)
        latest_date = fin_df.columns[0]
        
        # 1. 嘗試獲取標準化淨利
        normalized_income = None
        use_normalized = False
        
        if 'Normalized Income' in fin_df.index:
            normalized_income = fin_df.loc['Normalized Income', latest_date]
            use_normalized = True
            print(f"✅ [Tool] 找到標準化淨利 (Normalized Income): {normalized_income/1_000_000:.2f}M")
        else:
            # 2. 回退到普通淨利
            if 'Net Income' in fin_df.index:
                normalized_income = fin_df.loc['Net Income', latest_date]
                use_normalized = False
                print(f"⚠️ [Tool] 未找到標準化數據，使用普通淨利: {normalized_income/1_000_000:.2f}M")
            else:
                print(f"❌ [Tool] 無法找到淨利數據")
                return None
        
        # 獲取普通淨利作對比
        raw_net_income = None
        if 'Net Income' in fin_df.index:
            raw_net_income = fin_df.loc['Net Income', latest_date]
        
        # 獲取流通股數 (用於計算 EPS)
        info = stock.info
        shares = info.get('sharesOutstanding')
        
        return {
            "normalized_income": float(normalized_income),
            "raw_net_income": float(raw_net_income) if raw_net_income is not None else float(normalized_income),
            "shares_outstanding": float(shares) if shares else None,
            "use_normalized": use_normalized
        }
        
    except Exception as e:
        print(f"❌ [Tool Error] 無法獲取詳細財務數據: {e}")
        import traceback
        traceback.print_exc()
        return None


def calculate_metrics(financials: dict, market_data: dict) -> dict:
    """
    執行純數學計算（雙軌 P/E 驗證）。
    
    Args:
        financials: Dictionary with 'total_revenue' and 'net_income' (in millions)
        market_data: Dictionary with 'price', 'market_cap', 'trailing_pe' (market_cap in absolute value)
        
    Returns:
        dict: Calculated metrics with dual-track P/E analysis
    """
    revenue = financials.get("total_revenue", 0)
    net_income = financials.get("net_income", 0)
    market_cap = market_data.get("market_cap", 0)
    
    # 1. 淨利率 (保持不變)
    margin = 0.0
    if revenue > 0:
        margin = (net_income / revenue) * 100
    
    # 2. [Dual Track] 計算 P/E
    
    # Track A: FY P/E (基於財報)
    pe_ratio_fy = 0.0
    net_income_absolute = net_income * 1_000_000
    if net_income_absolute > 0:
        pe_ratio_fy = market_cap / net_income_absolute
    
    # Track B: TTM P/E (基於 Yahoo 實時數據)
    pe_ratio_ttm = market_data.get("trailing_pe")
    
    # 3. [Insight] 趨勢分析
    # 如果 TTM P/E 存在，優先用它做主要指標
    primary_pe = pe_ratio_ttm if pe_ratio_ttm else pe_ratio_fy
    
    trend_insight = "Stable"
    if pe_ratio_ttm and pe_ratio_fy > 0:
        # 設置 5% 的誤差緩衝區
        diff_pct = (pe_ratio_ttm - pe_ratio_fy) / pe_ratio_fy
        
        if diff_pct < -0.05:
            # TTM P/E 更低 -> 分母(獲利)變大了 -> 成長信號
            trend_insight = f"Earnings Improving (TTM P/E {pe_ratio_ttm:.1f} < FY P/E {pe_ratio_fy:.1f})"
        elif diff_pct > 0.05:
            # TTM P/E 更高 -> 分母(獲利)變小了 -> 衰退信號
            trend_insight = f"Earnings Declining (TTM P/E {pe_ratio_ttm:.1f} > FY P/E {pe_ratio_fy:.1f})"
        else:
            trend_insight = "Earnings Stable (TTM approx. equal to FY)"
    elif not pe_ratio_ttm:
        trend_insight = "TTM P/E unavailable, using FY P/E only"
    
    # 4. 估值狀態判斷 (使用 Primary P/E)
    status = "Fair Value"
    if primary_pe > 0:
        if primary_pe < 15:
            status = "Undervalued"
        elif primary_pe > 35:
            status = "Overvalued"
    
    return {
        "market_cap": market_cap / 1_000_000,  # 轉為 million 方便顯示
        "current_price": market_data["price"],
        "net_profit_margin": round(margin, 2),
        
        # 返回所有 P/E 數據
        "pe_ratio": round(primary_pe, 2),
        "pe_ratio_ttm": round(pe_ratio_ttm, 2) if pe_ratio_ttm else None,
        "pe_ratio_fy": round(pe_ratio_fy, 2),
        "pe_trend_insight": trend_insight,
        
        "valuation_status": status
    }


def calculate_dcf(
    free_cash_flow: float,
    shares_outstanding: float,
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth: float = 0.03,
    projection_years: int = 5
) -> float:
    """
    Core DCF Math Function.
    
    Input constraints: All currency/share values MUST be absolute numbers.
    
    Args:
        free_cash_flow: 初始 FCF (OCF - CapEx) - 必須是絕對值 (e.g., 17,000,000,000)
        shares_outstanding: 流通股數 - 必須是絕對值 (e.g., 900,000,000)
        growth_rate: 前N年的預期增長率 (默認 10%，可動態調整)
        discount_rate: 折現率 WACC (默認 10%)
        terminal_growth: 永續增長率 (默認 3%)
        projection_years: 預測年數 (默認 5年)
    
    Returns:
        float: Intrinsic Value per Share (絕對值)
    """
    if shares_outstanding == 0:
        return 0.0
    
    # 增加日誌，讓我們看到 Agent 到底用了多少增長率
    print(f"🧮 [DCF Config] Growth Rate: {growth_rate:.1%}, Discount Rate: {discount_rate:.1%}")
    
    # 1. 預測未來現金流 (Stage 1)
    future_fcfs = []
    for i in range(1, projection_years + 1):
        fcf = free_cash_flow * ((1 + growth_rate) ** i)
        future_fcfs.append(fcf)
    
    # 2. 計算終值 (Terminal Value, Stage 2)
    last_fcf = future_fcfs[-1]
    terminal_value = (last_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
    
    # 3. 折現回今天 (Present Value)
    pv_fcfs = 0.0
    for i, fcf in enumerate(future_fcfs):
        pv_fcfs += fcf / ((1 + discount_rate) ** (i + 1))
    
    pv_terminal = terminal_value / ((1 + discount_rate) ** projection_years)
    
    # 4. 總公司價值 (Enterprise Value 簡化版)
    # [FIX] 這已經是絕對值了，不需要轉換
    total_enterprise_value = pv_fcfs + pv_terminal
    
    # 5. 每股價值 (絕對值 / 絕對值 = 股價)
    # [FIX] 移除了 * 1,000,000，因為輸入已經是絕對值
    intrinsic_value = total_enterprise_value / shares_outstanding
    
    return intrinsic_value
