"""
Strategy Configuration Definitions

This module contains all strategy configuration classes.
Each class encapsulates:
- Strategy definition (for Profiler)
- Data extraction requirements (for Miner)
"""

from src.strategies.base import BaseStrategyConfig
from src.consts import ValuationStrategyType


class GeneralDCFConfig(BaseStrategyConfig):
    """通用 2-Stage DCF 策略配置"""

    @property
    def strategy_id(self) -> str:
        return ValuationStrategyType.GENERAL_DCF.value

    @property
    def name(self) -> str:
        return "General 2-Stage DCF"

    @property
    def description(self) -> str:
        return """
- 適用範圍: 大多數製造業、服務業、科技公司、消費品公司。
- 特徵: 具有穩定的經營現金流，資本結構標準。
- 例子: Apple, Tesla, Coca-Cola, Walmart.
"""

    @property
    def data_extraction_prompt(self) -> str:
        return """
【提取重點：通用 DCF】
1. 請重點關注 'Consolidated Statements of Operations' 和 'Cash Flows'。
2. 必須提取：Net Income, Revenue, Operating Cash Flow, Capital Expenditures.
3. 若有 R&D 費用，也請單獨提取。
"""


class BankDDMConfig(BaseStrategyConfig):
    """銀行 DDM 策略配置"""

    @property
    def strategy_id(self) -> str:
        return ValuationStrategyType.BANK_DDM.value

    @property
    def name(self) -> str:
        return "Bank DDM (Dividend Discount Model)"

    @property
    def description(self) -> str:
        return """
- 適用範圍: 銀行、保險公司、傳統金融機構。
- 特徵: 資產負債表是核心業務，現金流定義與普通公司不同（利息收入），通常使用股利折現模型 (DDM) 或 P/B 估值。
- 例子: JPMorgan, Bank of America, HSBC.
"""

    @property
    def data_extraction_prompt(self) -> str:
        return """
【提取重點：金融機構專屬】
這是一家金融機構，現金流定義與普通公司不同。請務必提取：
1. **Dividends Paid** (已支付股利 - 用於 DDM 模型)。
2. **Book Value per Share** (每股淨資產 - 用於 P/B 估值)。
3. **Tier 1 Capital Ratio** (一級資本比率 - 衡量資本充足率)。
4. **Net Interest Income** (淨利息收入 - 核心業務指標)。
5. Net Income (作為輔助指標)。
"""


class ReitNAVConfig(BaseStrategyConfig):
    """REITs NAV 策略配置"""

    @property
    def strategy_id(self) -> str:
        return ValuationStrategyType.REIT_NAV.value

    @property
    def name(self) -> str:
        return "REITs NAV/FFO Model"

    @property
    def description(self) -> str:
        return """
- 適用範圍: 房地產投資信託 (REITs)、收租型地產公司。
- 特徵: 淨利潤無法反映真實價值（因為鉅額折舊），需使用 FFO (Funds From Operations) 或 NAV (淨資產價值)。
- 例子: Realty Income (O), Simon Property Group.
"""

    @property
    def data_extraction_prompt(self) -> str:
        return """
【提取重點：REITs 專屬】
這是一家房地產信託公司，Net Income 不具備參考價值。請務必提取：
1. **Depreciation and Amortization** (折舊與攤銷 - 這是計算 FFO 的關鍵加回項)。
2. **Gains/Losses on sale of real estate** (資產出售損益 - 這是扣除項)。
3. Net Income (作為計算起點)。
4. 嘗試尋找文中是否直接披露了 'FFO' 或 'AFFO' 數值。
"""


class SaaSRule40Config(BaseStrategyConfig):
    """SaaS Rule of 40 策略配置"""

    @property
    def strategy_id(self) -> str:
        return ValuationStrategyType.SAAS_RULE40.value

    @property
    def name(self) -> str:
        return "SaaS Rule of 40"

    @property
    def description(self) -> str:
        return """
- 適用範圍: 高增長、尚未盈利的軟體/SaaS 公司。
- 特徵: 淨利潤為負，但營收增長極快。關注 ARR、留存率和 Rule of 40。
- 例子: Snowflake, Datadog, Cloudflare.
"""

    @property
    def data_extraction_prompt(self) -> str:
        return """
【提取重點：SaaS 專屬】
這是一家高增長 SaaS 公司，傳統估值指標不適用。請務必提取：
1. **Revenue Growth Rate** (營收增長率 - 用於 Rule of 40 計算)。
2. **Operating Margin** (或 Operating Loss) - 用於 Rule of 40 計算。
3. **ARR (Annual Recurring Revenue)** - 如果財報中有披露。
4. **Customer Retention Rate** (客戶留存率) - 如果財報中有披露。
5. Revenue 和 Net Income (作為基礎指標)。
"""
