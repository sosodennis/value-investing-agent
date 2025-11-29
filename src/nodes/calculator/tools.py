"""
Node B: Calculator - Private Tools

This module contains financial calculation utilities:
1. Market data fetching (yfinance)
2. Valuation ratio calculations (P/E, Margins, etc.)
3. Financial data validation

All calculations are pure Python - no LLM involvement to ensure accuracy.
"""

import yfinance as yf


def get_market_data(ticker: str):
    """
    獲取實時市場數據：股價、市值、流通股數。
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        dict: Contains 'price' and 'market_cap', or None if failed
    """
    try:
        stock = yf.Ticker(ticker)
        
        # 獲取最新價格 (history 比 info 更快更穩定)
        hist = stock.history(period="1d")
        if hist.empty:
            raise ValueError(f"無法獲取 {ticker} 的股價數據")
        
        current_price = float(hist["Close"].iloc[-1])
        
        # 獲取市值 (Market Cap)
        # 注意：info 接口有時會慢或失敗，生產環境建議加緩存或重試
        info = stock.info
        market_cap = info.get("marketCap")
        
        if not market_cap:
            # 如果拿不到市值，嘗試用 Price * Shares Outstanding 估算
            shares = info.get("sharesOutstanding")
            if shares:
                market_cap = current_price * shares
            else:
                raise ValueError("無法獲取市值數據")
        
        return {
            "price": current_price,
            "market_cap": float(market_cap)
        }
    except Exception as e:
        print(f"❌ [Calculator Tool] yfinance error: {e}")
        return None


def calculate_metrics(financials: dict, market_data: dict) -> dict:
    """
    執行純數學計算。
    
    Args:
        financials: Dictionary with 'total_revenue' and 'net_income' (in millions)
        market_data: Dictionary with 'price' and 'market_cap' (market_cap in absolute value)
        
    Returns:
        dict: Calculated metrics
    """
    revenue = financials.get("total_revenue", 0)
    net_income = financials.get("net_income", 0)
    market_cap = market_data.get("market_cap", 0)
    
    # 1. Net Profit Margin (淨利率) = Net Income / Revenue
    margin = 0.0
    if revenue > 0:
        margin = (net_income / revenue) * 100
    
    # 2. P/E Ratio (本益比) = Market Cap / Net Income
    # 注意：這裡 Net Income 單位是 million，Market Cap 單位通常是元
    # 所以要統一單位。我們假設 financials 裡的單位是 million (10^6)
    
    pe_ratio = 0.0
    net_income_absolute = net_income * 1_000_000  # 轉為絕對值
    
    if net_income_absolute > 0:
        pe_ratio = market_cap / net_income_absolute
    
    # 3. 簡單估值狀態判斷 (規則引擎)
    # 這只是一個簡單的範例，實際可以寫更複雜
    status = "Fair Value"
    if pe_ratio > 0:
        if pe_ratio < 15:
            status = "Undervalued"
        elif pe_ratio > 35:
            status = "Overvalued"
    
    return {
        "market_cap": market_cap / 1_000_000,  # 轉為 million 方便顯示
        "current_price": market_data["price"],
        "net_profit_margin": round(margin, 2),
        "pe_ratio": round(pe_ratio, 2),
        "valuation_status": status
    }
