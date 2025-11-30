"""
Base Strategy Configuration Interface

This module defines the abstract base class for all strategy configurations.
Each strategy configuration encapsulates its definition, data requirements,
and extraction prompts in one place.
"""

from abc import ABC, abstractproperty


class BaseStrategyConfig(ABC):
    """所有估值策略配置的基類"""
    
    @abstractproperty
    def strategy_id(self) -> str:
        """策略的唯一標識符 (對應 Enum)"""
        pass
    
    @abstractproperty
    def name(self) -> str:
        """策略的人類可讀名稱"""
        pass
    
    @abstractproperty
    def description(self) -> str:
        """
        [Profiler 使用]
        
        用於告訴 LLM 這個策略適合什麼樣的公司。
        格式應包含：適用範圍、特徵、例子。
        """
        pass
    
    @abstractproperty
    def data_extraction_prompt(self) -> str:
        """
        [Miner 使用]
        
        用於告訴 Gemini 在讀取 10-K 時應該重點提取什麼特殊數據。
        """
        pass

