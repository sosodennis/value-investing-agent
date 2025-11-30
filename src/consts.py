"""
Global Constants and Enums

This module contains system-wide constants and enumerations.
"""

from enum import Enum


class ValuationStrategyType(str, Enum):
    """
    估值策略枚舉。
    
    繼承 str 類，以便可以直接用於 Pydantic 和 JSON 序列化。
    這樣可以直接使用 Enum 成員作為字符串值，同時享受類型檢查的好處。
    """
    GENERAL_DCF = "general_dcf"
    BANK_DDM = "bank_ddm"
    REIT_NAV = "reit_nav"
    SAAS_RULE40 = "saas_rule40"

