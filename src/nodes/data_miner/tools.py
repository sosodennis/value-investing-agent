"""
Node A: Data Miner - Private Tools

This module contains SEC-specific tools for the Data Miner node:
1. SEC EDGAR download utilities
2. HTML to Markdown conversion
3. Basic text cleaning (removes HTML tags, preserves structure)

Note: With Gemini 1.5's 2M token context window, we can pass entire
10-K sections (e.g., entire Item 7 MD&A) directly to the LLM without
complex chunking logic. This significantly simplifies the extraction process.
"""

# TODO: Implement SEC tools in Phase 1
# Key functions:
# - download_sec_filing(ticker: str, filing_type: str = "10-K") -> str
# - clean_html_to_markdown(html_content: str) -> str
# - extract_section(text: str, section_name: str) -> str

