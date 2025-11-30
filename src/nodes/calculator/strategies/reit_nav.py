"""
REITs NAV Strategy

This strategy implements the P/FFO (Price to Funds From Operations) model
for Real Estate Investment Trusts (REITs).

Core Logic: FFO = Net Income + Depreciation - Gains on Asset Sales
Valuation: Price / FFO Ratio
"""

from typing import Dict, Any
from src.nodes.calculator.strategies.base import BaseValuationStrategy
from src.models.valuation import ValuationMetrics
from src.models.financial import FinancialStatements
from src.nodes.calculator.tools import get_market_data_raw


class ReitNAVStrategy(BaseValuationStrategy):
    """
    REITs 專屬策略 (Simplified P/FFO Model)
    
    Core Logic: FFO = Net Income + Depreciation - Gains on Asset Sales
    Valuation: Price / FFO Ratio
    """

    def calculate(
        self, 
        ticker: str,
        financial_data: FinancialStatements, 
        market_data: Dict[str, Any]
    ) -> ValuationMetrics:
        """
        執行 REITs 估值計算。
        
        Args:
            ticker: 股票代碼
            financial_data: 財務數據 (包含 REITs 特定字段)
            market_data: 市場數據 (占位符，實際會重新獲取)
            
        Returns:
            ValuationMetrics: 計算結果
        """
        print(f"🏗️ [Strategy] 執行 REITs 估值模型 (FFO): {ticker}")
        
        # 1. 獲取完整的市場數據
        md = get_market_data_raw(ticker)
        if not md:
            raise ValueError("無法獲取市場數據")
        
        # 2. 獲取並清洗數據
        net_income = financial_data.net_income
        # 對於 Optional 字段，提供默認值 0.0 以防計算崩潰
        depreciation = financial_data.depreciation_amortization or 0.0
        gains = financial_data.gain_on_sale or 0.0
        
        # 3. 計算 FFO (Funds From Operations)
        # FFO = 淨利 + 折舊 - 資產出售收益
        ffo = net_income + depreciation - gains
        print(f"📊 [REIT Math] FFO Calculation: {net_income} (NI) + {depreciation} (Depr) - {gains} (Gains) = {ffo} (Millions)")
        
        # 4. 準備市場數據
        price = md['price']
        shares = md.get('shares_outstanding', 0)
        market_cap_millions = md['market_cap'] / 1_000_000  # 轉 million 以匹配 FFO
        
        # 5. 計算 P/FFO 比率
        p_ffo = 0.0
        ffo_per_share = 0.0
        
        if ffo > 0:
            p_ffo = market_cap_millions / ffo
            if shares > 0:
                ffo_per_share = (ffo * 1_000_000) / shares  # 轉回絕對值除以股數
            
        print(f"💰 [REIT Metric] P/FFO: {p_ffo:.2f}x | FFO/Share: ${ffo_per_share:.2f}")
        
        # 6. 估值狀態判斷
        # REITs 的合理 P/FFO 通常在 15x - 20x 之間 (視利率環境而定)
        status = "Fair Value"
        if p_ffo > 0:
            if p_ffo < 12:
                status = "Undervalued"
            elif p_ffo > 22:
                status = "Overvalued"
            
        # 7. 計算 Fair Value (基於 FFO 倍數)
        # 假設行業平均 P/FFO 為 16x (保守估計)
        target_multiple = 16.0
        fair_value = ffo_per_share * target_multiple
        
        upside = 0.0
        if price > 0:
            upside = ((fair_value - price) / price) * 100
            
        # 8. 計算 Net Profit Margin (REITs 通常不看這個，但為了兼容性填 0)
        # 實際上 REITs 更關注 FFO Margin，但為了保持 ValuationMetrics 結構，填 0
        
        # 9. 返回結果
        # 將 P/FFO 填入 pe_ratio 字段，並在 insight 中說明
        return ValuationMetrics(
            market_cap=market_cap_millions,
            current_price=price,
            net_profit_margin=0.0,  # REITs 不看 Margin
            pe_ratio=round(p_ffo, 2),  # 這裡是 P/FFO
            pe_ratio_ttm=None,
            pe_ratio_fy=round(p_ffo, 2),
            pe_trend_insight=f"Valuation based on P/FFO (FFO/Share: ${ffo_per_share:.2f})",
            eps_ttm=None,
            eps_normalized=None,
            is_normalized=False,
            valuation_status=status,
            dcf_value=round(fair_value, 2),  # 這裡是 Fair Value
            dcf_upside=round(upside, 2)
        )

