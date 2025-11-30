"""
Strategy Knowledge Base for Profiler Node

This module contains the definitions of all available valuation strategies.
Used by the Profiler to help LLM make intelligent routing decisions.
"""

from src.consts import ValuationStrategyType

STRATEGY_DEFINITIONS = f"""
1. **{ValuationStrategyType.GENERAL_DCF.value}**:
   - 適用範圍: 大多數製造業、服務業、科技公司、消費品公司。
   - 特徵: 具有穩定的經營現金流，資本結構標準。
   - 例子: Apple, Tesla, Coca-Cola, Walmart.

2. **{ValuationStrategyType.BANK_DDM.value}**:
   - 適用範圍: 銀行、保險公司、傳統金融機構。
   - 特徵: 資產負債表是核心業務，現金流定義與普通公司不同（利息收入），通常使用股利折現模型 (DDM) 或 P/B 估值。
   - 例子: JPMorgan, Bank of America, HSBC.

3. **{ValuationStrategyType.REIT_NAV.value}**:
   - 適用範圍: 房地產投資信託 (REITs)、收租型地產公司。
   - 特徵: 淨利潤無法反映真實價值（因為鉅額折舊），需使用 FFO (Funds From Operations) 或 NAV (淨資產價值)。
   - 例子: Realty Income (O), Simon Property Group.

4. **{ValuationStrategyType.SAAS_RULE40.value}**:
   - 適用範圍: 高增長、尚未盈利的軟體/SaaS 公司。
   - 特徵: 淨利潤為負，但營收增長極快。關注 ARR、留存率和 Rule of 40。
   - 例子: Snowflake, Datadog, Cloudflare.
"""

