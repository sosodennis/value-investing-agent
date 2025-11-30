"""
SaaS Rule of 40 Strategy

This strategy implements the Rule of 40 model for high-growth SaaS companies.
Rule of 40 = Revenue Growth % + FCF Margin %
Valuation = EV / Sales Multiple
"""

from typing import Dict, Any
from src.nodes.calculator.strategies.base import BaseValuationStrategy
from src.models.valuation import ValuationMetrics
from src.models.financial import FinancialStatements
from src.nodes.calculator.tools import get_market_data_raw


class SaaSRule40Strategy(BaseValuationStrategy):
    """
    SaaS 專屬策略 (Rule of 40 + EV/Sales)
    
    Rule of 40 = Revenue Growth % + FCF Margin %
    Valuation = EV / Sales Multiple
    """

    def calculate(
        self, 
        ticker: str,
        financial_data: FinancialStatements, 
        market_data: Dict[str, Any]
    ) -> ValuationMetrics:
        """
        執行 SaaS Rule of 40 估值計算。
        
        Args:
            ticker: 股票代碼
            financial_data: 財務數據
            market_data: 市場數據 (占位符，實際會重新獲取)
            
        Returns:
            ValuationMetrics: 計算結果
        """
        print(f"☁️ [Strategy] 執行 SaaS Rule of 40 模型: {ticker}")
        
        # 1. 獲取完整的市場數據
        md = get_market_data_raw(ticker)
        if not md:
            raise ValueError("無法獲取市場數據")
        
        # 2. 準備數據
        revenue = financial_data.total_revenue
        
        # 獲取增長率
        # TODO: 目前依賴 yfinance 的 'revenueGrowth' 字段 (季度同比)。
        # 未來應優化 Miner 節點，抓取過去 3 年的歷史財報，以計算更穩定的 CAGR (年複合增長率)。
        revenue_growth = md.get('revenue_growth', 0.0) or 0.0
        
        # 計算 FCF Margin
        # FCF = Operating Cash Flow - CapEx
        ocf = financial_data.operating_cash_flow
        capex = abs(financial_data.capital_expenditures)
        fcf = ocf - capex
        
        fcf_margin = 0.0
        if revenue > 0:
            fcf_margin = fcf / revenue
            
        # 3. 計算 Rule of 40 分數
        # Rule of 40 = Growth % + Margin %
        # 例如: 30% (0.30) Growth + 15% (0.15) Margin = 45.0 Score
        rule_of_40_score = (revenue_growth * 100) + (fcf_margin * 100)
        
        print(f"📊 [SaaS Math] Growth: {revenue_growth:.1%} | FCF Margin: {fcf_margin:.1%} | Score: {rule_of_40_score:.1f}")
        
        # 4. 估值狀態判斷 (Rule of 40 基準)
        status = "Fair Value"
        if rule_of_40_score >= 40:
            status = "Elite SaaS (Undervalued likely)"
        elif rule_of_40_score < 20:
            status = "Underperforming (Overvalued likely)"
            
        # 5. EV/Sales 估值 (相對估值)
        # TODO: 當前使用 Market Cap 代替 Enterprise Value (EV)。
        # 未來應從 yfinance 獲取 Total Debt 和 Cash 來計算準確的 EV = Market Cap + Debt - Cash。
        market_cap_millions = md['market_cap'] / 1_000_000
        
        ev_sales = 0.0
        if revenue > 0:
            ev_sales = market_cap_millions / revenue
            
        print(f"💰 [SaaS Metric] EV/Sales: {ev_sales:.2f}x")
        
        # 6. 簡單定價規則 (基於分數給予目標倍數)
        target_multiple = 5.0
        if rule_of_40_score > 50:
            target_multiple = 15.0
        elif rule_of_40_score > 40:
            target_multiple = 10.0
        elif rule_of_40_score > 30:
            target_multiple = 8.0
        
        # 7. 計算目標價
        fair_ev = revenue * target_multiple
        shares = md.get('shares_outstanding', 0)
        
        fair_value_per_share = 0.0
        upside = 0.0
        if shares > 0:
            fair_value_per_share = (fair_ev * 1_000_000) / shares  # 轉回絕對值
            price = md['price']
            if price > 0:
                upside = ((fair_value_per_share - price) / price) * 100

        # 8. 返回結果
        return ValuationMetrics(
            market_cap=market_cap_millions,
            current_price=md['price'],
            net_profit_margin=round(fcf_margin * 100, 2),  # 用 FCF Margin 替代
            pe_ratio=round(ev_sales, 2),  # 借用字段存 EV/Sales
            pe_ratio_ttm=None,
            pe_ratio_fy=round(ev_sales, 2),
            pe_trend_insight=f"Rule of 40 Score: {rule_of_40_score:.1f}",
            eps_ttm=None,
            eps_normalized=None,
            is_normalized=False,
            valuation_status=status,
            dcf_value=round(fair_value_per_share, 2),  # 這裡是基於倍數的目標價
            dcf_upside=round(upside, 2)
        )

