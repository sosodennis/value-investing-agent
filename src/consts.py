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


class NodeConsts(str, Enum):
    """
    [V3 Architecture] 所有的 Graph 節點名稱定義。

    使用 Enum 繼承 str，這樣在 graph.py / main.py 中可以直接當作字串使用，
    同時保留型別安全與 IDE 自動補全。
    """

    # Phase 1: Profiling & Intent
    PROFILER = "profiler"
    CLARIFICATION_REQUEST = "clarification_request"

    # Phase 2: Data Collection
    MINER = "miner"
    USER_INJECTION = "user_injection"
    HUMAN_HELP = "human_help"  # For Miner error handling

    # Phase 3: Reconciliation
    MERGER = "merger"
    DATA_CONFLICT_RESOLVER = "data_conflict_resolver"  # The Judge

    # Phase 4: Analysis
    CALCULATOR = "calculator"
    VALUATION_AUDITOR = "valuation_auditor"

    # Phase 5: Reporting & Refinement
    WRITER = "writer"
    HUMAN_FEEDBACK_MANAGER = "human_feedback_manager"  # The Coach


class FeedbackConsts(str, Enum):
    """
    [Phase 5] 人類反饋類型定義。
    """

    APPROVE = "approve"
    PARAMETER_UPDATE = "parameter_update"  # 修改參數 (回滾至 Calculator)
    NARRATIVE_TWEAK = "narrative_tweak"  # 修改敘事 (回滾至 Writer)
