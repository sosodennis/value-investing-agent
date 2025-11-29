"""
Node B: Calculator - Main Node Logic

This node orchestrates financial calculations:
1. Validates input financial data
2. Fetches market data using yfinance
3. Performs ratio calculations using tools.calculate_metrics()
"""

import math
from src.state import AgentState
from src.models.valuation import ValuationMetrics
from src.nodes.calculator.tools import get_market_data, get_normalized_income_data, calculate_metrics, calculate_dcf


def calculator_node(state: AgentState) -> dict:
    """
    Calculator node function.
    
    This function:
    1. Gets financial data from Node A
    2. Fetches market data from yfinance
    3. Calculates valuation metrics
    4. Returns ValuationMetrics Pydantic object
    
    Returns:
        dict: Updated state with valuation_metrics (ValuationMetrics) or error
    """
    print(f"\n🧮 [Node B: Calculator] 正在計算 {state['ticker']} 的估值指標...")
    
    # 1. 從 State 獲取 Node A 的產出
    financial_obj = state.get("financial_data")
    if not financial_obj:
        print("❌ 錯誤：找不到財務數據，無法計算。")
        return {"error": "missing_financial_data"}
    
    # 轉為字典方便處理
    financials = financial_obj.model_dump()
    
    # 2. 調用工具獲取市場數據 (yfinance)
    market_data = get_market_data(state["ticker"])
    if not market_data:
        return {"error": "market_data_fetch_failed"}
    
    print(f"📈 [Calculator] 現價: ${market_data['price']:.2f}")
    
    # 2.5. [New] 獲取標準化財務數據 (EPS w/o NRI)
    nri_data = get_normalized_income_data(state["ticker"])
    
    # 初始化調查任務列表
    investigation_tasks = []
    
    # 決定估值使用的 "E" (Earnings)
    # 如果有標準化數據，我們優先使用它來計算 P/E 和 FCF 起點
    earnings_base = None
    is_normalized = False
    eps_normalized = None
    
    if nri_data:
        earnings_base = nri_data['normalized_income']
        is_normalized = nri_data['use_normalized']
        
        # 檢查是否存在重大差異 (例如 >20%)
        raw_income = nri_data['raw_net_income']
        if raw_income != 0:
            diff_pct = abs(earnings_base - raw_income) / abs(raw_income)
            if diff_pct > 0.2:
                warning_msg = f"標準化淨利與財報淨利差異巨大 ({diff_pct:.1%})，可能存在重大一次性項目！"
                print(f"🚨 [Insight] {warning_msg}")
                
                # [Fix] 將此洞察轉化為具體的搜索任務
                ticker = state['ticker']
                investigation_tasks.append(f"{ticker} net income vs normalized income discrepancy")
        
        # 計算標準化 EPS
        shares = nri_data.get('shares_outstanding') or market_data.get('shares_outstanding', 0)
        if shares and shares > 0:
            eps_normalized = earnings_base / shares
    else:
        # Fallback 到 Node A 提取的數據
        earnings_base = financial_obj.net_income * 1_000_000  # 轉絕對值
        is_normalized = False
    
    if earnings_base:
        print(f"📊 [Metrics] 使用的淨利基準: ${earnings_base/1_000_000:.2f}M (Normalized: {is_normalized})")
    
    # 3. 執行計算
    try:
        metrics_dict = calculate_metrics(financials, market_data)
        
        # [New] 輸出雙軌 P/E 對比
        pe_ttm = metrics_dict.get('pe_ratio_ttm')
        pe_fy = metrics_dict.get('pe_ratio_fy', 0)
        if pe_ttm:
            print(f"📊 [Metrics] FY P/E: {pe_fy:.2f}, TTM P/E: {pe_ttm:.2f}")
        else:
            print(f"📊 [Metrics] FY P/E: {pe_fy:.2f}, TTM P/E: N/A")
        
        trend_insight = metrics_dict.get('pe_trend_insight', '')
        if trend_insight:
            print(f"💡 [Insight] {trend_insight}")
        
        # --- [New] 智能增長率推導邏輯 ---
        # 默認保守值
        estimated_growth_rate = 0.10
        
        # 先算出 P/E (使用主要 P/E，優先 TTM)
        pe_ratio = metrics_dict.get('pe_ratio', 0)
        peg = market_data.get('peg_ratio')
        
        print(f"📊 [Market Data] P/E: {pe_ratio:.2f}, PEG: {peg}")
        
        if peg and peg > 0:
            # 策略 A: 透過 PEG 反推 (Growth = P/E / PEG)
            # 例如 TSLA P/E 200 / PEG 5 = 40% Growth
            # 注意：yfinance 的 pegRatio 通常是比率，所以直接使用
            # 經驗公式：Growth Rate = (P/E) / PEG / 100
            
            implied_growth = (pe_ratio / peg) / 100
            
            # 設置安全邊界 (Sanity Check)：不相信超過 50% 的永續增長
            if 0 < implied_growth < 0.50:
                estimated_growth_rate = implied_growth
                print(f"🚀 [Insight] 根據 PEG ({peg:.2f}) 推導出市場隱含增長率: {estimated_growth_rate:.2%}")
            else:
                print(f"⚠️ [Insight] PEG 推導的增長率 ({implied_growth:.2%}) 過於極端，將使用規則修正。")
        
        # 策略 B: 如果沒有 PEG，或者 PEG 數據異常，使用 P/E 分層規則
        if estimated_growth_rate == 0.10:  # 代表上面沒更新
            if pe_ratio > 50:
                estimated_growth_rate = 0.25  # 高成長股假設
                print("🚀 [Insight] 檢測到高 P/E (>50)，啟用激進增長假設 (25%)")
            elif pe_ratio > 25:
                estimated_growth_rate = 0.15  # 中高成長
                print("📈 [Insight] 檢測到中高 P/E (>25)，啟用適度增長假設 (15%)")
        
        # --- [New] 動態計算 WACC (Discount Rate) with Hurdle Rate Floor ---
        # 1. 獲取參數
        rf = market_data.get('risk_free_rate', 0.042)  # 默認 4.2%
        beta = market_data.get('beta')
        market_premium = 0.05  # 設為 5% (歷史平均水平，Aswath Damodaran 的標準)
        
        # 2. 計算標準 CAPM WACC
        capm_wacc = 0.10  # Fallback
        if beta:
            capm_wacc = rf + beta * market_premium
            print(f"📉 [WACC] CAPM Raw: {capm_wacc:.1%}")
        else:
            print("⚠️ [WACC] 缺失 Beta 數據，使用默認 CAPM (10%)")
        
        # 3. [New] 計算保底折現率 (Hurdle Rate)
        # 邏輯參考：RoundUp(Rf) + 5.5% (Risk Premium Floor)
        # 這裡我們使用 math.ceil 對 Rf 進行向上取整 (例如 4.2% -> 5.0%)
        rf_percent = rf * 100
        rf_rounded = math.ceil(rf_percent) / 100
        hurdle_premium = 0.055  # 設定為 5.5% (折衷方案，介於 5-6% 之間)
        
        hurdle_rate = rf_rounded + hurdle_premium
        print(f"🛡️ [WACC] Hurdle Rate Floor: {hurdle_rate:.1%}")
        
        # 4. 決策：取兩者之大者
        # 這是為了防止低 Beta 導致折現率過低，同時也保留了高 Beta (如 TSLA) 的高折現率
        final_discount_rate = max(capm_wacc, hurdle_rate)
        
        if final_discount_rate == hurdle_rate:
            print(f"⚖️ [WACC Adjustment] CAPM 過低，啟用保底折現率: {final_discount_rate:.1%}")
        else:
            print(f"⚖️ [WACC Adjustment] 使用 CAPM 折現率: {final_discount_rate:.1%}")
        
        estimated_discount_rate = final_discount_rate
        
        # --- [Critical] FCF 數據標準化 (Normalization) ---
        # 強制執行「絕對數值標準」：所有計算邏輯只處理原始數值 (Raw Numbers)
        fcf_absolute = 0.0  # 這是我們唯一傳給 calculate_dcf 的變量（必須是絕對值）
        
        # 1. 嘗試使用 TTM FCF (yfinance info 通常返回絕對值)
        ttm_fcf = market_data.get("fcf_ttm")
        
        if ttm_fcf and ttm_fcf > 0:
            # yfinance 返回的是絕對值 (Bytes)，直接使用
            fcf_absolute = float(ttm_fcf)
            print(f"✅ [Data Source] 使用實時 TTM FCF (Absolute): ${fcf_absolute:,.0f}")
        else:
            # 2. 回退使用財報數據 (SEC 提取的是 Millions)
            # 必須 * 1,000,000 轉為絕對值
            ocf = financial_obj.operating_cash_flow
            capex = abs(financial_obj.capital_expenditures)
            fcf_millions = ocf - capex
            fcf_absolute = fcf_millions * 1_000_000
            print(f"⚠️ [Data Source] 使用財報 FCF (Converted to Absolute): ${fcf_absolute:,.0f}")
        
        # --- [New] 增長率校準機制 ---
        # 如果使用 TTM 數據，且 TTM FCF > FY FCF (說明今年已經長了很多)，
        # 我們可以稍微保守一點設定未來的 Growth Rate，防止雙重計算增長
        adjusted_growth_rate = estimated_growth_rate
        
        if ttm_fcf and ttm_fcf > 0:
            # 計算 FY FCF 作為對比（轉為絕對值）
            ocf_fy = financial_obj.operating_cash_flow
            capex_fy = abs(financial_obj.capital_expenditures)
            fcf_fy_millions = ocf_fy - capex_fy
            fcf_fy_absolute = fcf_fy_millions * 1_000_000
            
            if fcf_fy_absolute > 0:
                # 計算 TTM vs FY 的增長率
                ttm_growth = (ttm_fcf - fcf_fy_absolute) / fcf_fy_absolute
                
                # 如果 TTM 已經比 FY 高很多 (>20%)，說明過去一年已經有顯著增長
                # 我們應該稍微降低未來的增長率預期，避免雙重計算
                if ttm_growth > 0.20:
                    # 保守調整：將未來增長率降低 20-30%
                    adjustment_factor = 0.75  # 降低 25%
                    adjusted_growth_rate = estimated_growth_rate * adjustment_factor
                    print(f"📊 [Growth Calibration] TTM FCF 已比 FY 高 {ttm_growth:.1%}，調整未來增長率: {estimated_growth_rate:.1%} → {adjusted_growth_rate:.1%} (避免雙重計算)")
        
        # --- 獲取流通股數 (確保是絕對值) ---
        shares_outstanding = float(market_data.get('shares_outstanding', 0))
        
        if shares_outstanding > 0 and fcf_absolute > 0:
            # 調用工具，傳入絕對值（已標準化）
            intrinsic_value = calculate_dcf(
                free_cash_flow=fcf_absolute,  # 傳入絕對值
                shares_outstanding=shares_outstanding,  # 傳入絕對值
                growth_rate=adjusted_growth_rate,  # <--- 使用校準後的增長率
                discount_rate=estimated_discount_rate,  # <--- 注入動態 WACC
                terminal_growth=0.04,
                projection_years=10
            )
            
            current_price = market_data['price']
            upside = ((intrinsic_value - current_price) / current_price) * 100
            
            print(f"💎 [Calculator] DCF 估值: ${intrinsic_value:.2f} (Upside: {upside:.2f}%)")
            
            # 更新 Metrics 對象
            metrics_dict['dcf_value'] = round(intrinsic_value, 2)
            metrics_dict['dcf_upside'] = round(upside, 2)
        else:
            print("⚠️ [Calculator] 無法計算 DCF: FCF 或流通股數為 0")
            metrics_dict['dcf_value'] = 0.0
            metrics_dict['dcf_upside'] = 0.0
        
        # 5. 封裝為 Pydantic 對象
        # 添加標準化利潤指標
        metrics_dict['eps_ttm'] = eps_normalized if eps_normalized else None
        metrics_dict['eps_normalized'] = eps_normalized if is_normalized else None
        metrics_dict['is_normalized'] = is_normalized
        
        metrics_obj = ValuationMetrics(**metrics_dict)
        
        print(f"🧮 [Calculator] 計算完成: P/E={metrics_obj.pe_ratio}, Margin={metrics_obj.net_profit_margin}%")
        
        # 如果有調查任務，輸出提示
        if investigation_tasks:
            print(f"📋 [Investigation] 生成 {len(investigation_tasks)} 個調查任務，將傳遞給 Researcher")
        
        return {
            "valuation_metrics": metrics_obj,
            "investigation_tasks": investigation_tasks,  # [Fix] 將任務傳遞給下游
            "error": None
        }
    except Exception as e:
        print(f"❌ 計算錯誤: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "calculation_failed"}
