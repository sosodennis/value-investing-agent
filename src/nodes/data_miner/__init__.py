"""
Node A: Data Miner Module

This module is responsible for:
1. Downloading SEC 10-K filings from EDGAR
2. Cleaning HTML to Markdown
3. Extracting structured financial data as JSON using Gemini

Exception handling: If download fails, triggers error flag and routes to Human Loop.
"""

# 导出节点函数（延迟导入以避免循环依赖）
# graph.py 直接从 .node 导入，这里只用于文档

__all__ = ["data_miner_node"]

