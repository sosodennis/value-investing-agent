"""
Strategy Registry

This module provides a centralized registry for all strategy configurations.
It implements the Registry Pattern to enable dynamic strategy discovery and access.
"""

from typing import Dict
from src.strategies.base import BaseStrategyConfig
from src.strategies.definitions import (
    GeneralDCFConfig,
    BankDDMConfig,
    ReitNAVConfig,
    SaaSRule40Config
)
from src.consts import ValuationStrategyType


class StrategyRegistry:
    """策略註冊中心 (Singleton Pattern)"""
    
    _strategies: Dict[str, BaseStrategyConfig] = {
        cfg().strategy_id: cfg()
        for cfg in [
            GeneralDCFConfig,
            BankDDMConfig,
            ReitNAVConfig,
            SaaSRule40Config
        ]
    }
    
    @classmethod
    def get_strategy(cls, strategy_id: str) -> BaseStrategyConfig:
        """
        根據 ID 獲取策略配置。
        
        Args:
            strategy_id: 策略標識符 (對應 ValuationStrategyType 的值)
            
        Returns:
            BaseStrategyConfig: 策略配置對象，如果未找到則返回 GeneralDCFConfig
        """
        return cls._strategies.get(
            strategy_id, 
            cls._strategies[ValuationStrategyType.GENERAL_DCF.value]
        )
    
    @classmethod
    def get_all_prompts_for_profiler(cls) -> str:
        """
        [Profiler 使用] 動態生成所有策略的定義 Prompt。
        
        這樣以後新增策略只需加 Class，不用改 Prompt String。
        
        Returns:
            str: 格式化的策略定義字符串，用於 Profiler 的 LLM Prompt
        """
        prompt_text = ""
        for idx, strategy in enumerate(cls._strategies.values(), 1):
            prompt_text += f"{idx}. **{strategy.strategy_id}** ({strategy.name}):\n{strategy.description}\n\n"
        return prompt_text.strip()
    
    @classmethod
    def list_all_strategies(cls) -> list:
        """
        獲取所有已註冊的策略 ID 列表。
        
        Returns:
            list: 所有策略 ID 的列表
        """
        return list(cls._strategies.keys())

