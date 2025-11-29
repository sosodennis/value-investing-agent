"""
Node A: Data Miner - Private Tools

This module contains SEC-specific tools for the Data Miner node:
1. SEC EDGAR download utilities
2. HTML to Markdown conversion
3. Basic text cleaning (removes HTML tags, preserves structure)

Note: With Gemini's large context window, we can pass large
10-K sections directly to the LLM without complex chunking logic.
"""

import os
import glob
import re
from sec_edgar_downloader import Downloader
from bs4 import BeautifulSoup
from markdownify import markdownify

# 定義數據緩存目錄 (專案根目錄/data)
# 確保路徑相對於當前文件是正確的
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))


def get_sec_downloader(user_agent: str) -> Downloader:
    """
    Create and return a SEC EDGAR Downloader instance.
    
    Args:
        user_agent: User agent string in format "Name <email@domain.com>"
        
    Returns:
        Downloader instance
    """
    return Downloader("MyAIOrg", user_agent, BASE_DIR)


def fetch_10k_text(ticker: str, user_agent: str) -> str:
    """
    Download the latest 10-K filing and extract financial statements text.
    
    Steps:
    1. Download latest 10-K from SEC EDGAR
    2. Extract financial statements section (Markdown format)
    3. Return cleaned text for LLM processing
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        user_agent: User agent string for SEC API
        
    Returns:
        str: Markdown-formatted text containing financial statements
        
    Raises:
        ValueError: If download fails or file not found
        FileNotFoundError: If downloaded file cannot be located
    """
    try:
        print(f"📥 [Tool] 正在從 SEC 下載 {ticker} 的 10-K (User-Agent: {user_agent})...")
        dl = get_sec_downloader(user_agent)
        
        # 下載 1 份最新的 10-K
        # download_details=False 只下載主文檔
        num_downloaded = dl.get("10-K", ticker, limit=1, download_details=False)
        
        if num_downloaded == 0:
            raise ValueError("SEC 下載器未找到任何文件")
        
        # --- [Fix] 修改文件查找邏輯：支持 HTML 和 TXT 格式 ---
        
        # 定義基礎搜索路徑: data/sec-edgar-filings/{ticker}/10-K/{accession}/
        base_search_path = os.path.join(BASE_DIR, "sec-edgar-filings", ticker, "10-K", "*")
        
        # 策略 A: 先找 HTML (Primary Document)
        html_files = glob.glob(os.path.join(base_search_path, "*.html"))
        
        # 策略 B: 再找 TXT (Full Submission) - 新版本 sec-edgar-downloader 可能下載此格式
        txt_files = glob.glob(os.path.join(base_search_path, "*.txt"))
        
        target_file = None
        
        if html_files:
            target_file = html_files[0]
            print("📄 [Tool] 找到 HTML 格式文件")
        elif txt_files:
            target_file = txt_files[0]
            print("📄 [Tool] 找到 TXT (Full Submission) 格式文件")
        else:
            raise FileNotFoundError(f"無法在 {base_search_path} 找到 HTML 或 TXT 文件")
        
        print(f"📄 [Tool] 讀取文件路徑: {target_file}")
        with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
        
        print(f"🧹 [Tool] 正在清洗內容 (原始大小: {len(html_content)} chars)...")
        
        # --- 智能截取策略 ---
        # 即使是 .txt 的 full-submission，BeautifulSoup 也能解析其中的 HTML 標籤
        # BeautifulSoup 會自動忽略 SEC-HEADER 這種非 HTML 標籤，只保留表格
        soup = BeautifulSoup(html_content, 'lxml')
        text_content = soup.get_text(" ", strip=True)  # 先粗略轉文本用於定位
        
        # 定位關鍵詞 (大小寫不敏感)
        # 10-K Item 8 通常包含 Financial Statements
        targets = [
            "Consolidated Statements of Operations",
            "CONSOLIDATED STATEMENTS OF OPERATIONS",
            "Consolidated Statements of Income",
            "CONSOLIDATED STATEMENTS OF INCOME"
        ]
        
        start_idx = -1
        for t in targets:
            idx = text_content.find(t)
            if idx != -1:
                start_idx = idx
                print(f"📍 [Tool] 定位到關鍵詞: {t}")
                break
        
        # 如果找不到，就取文檔後半部分 (通常財報在後面)
        if start_idx == -1:
            print("⚠️ [Tool] 未找到關鍵詞，使用文檔後半部分...")
            start_idx = len(html_content) // 2
        
        # --- 轉換為 Markdown ---
        print("🔄 [Tool] 正在轉換為 Markdown (這可能需要幾秒鐘)...")
        # markdownify 會自動忽略 SEC-HEADER 這種非 HTML 標籤，只保留表格
        # 即使是 full-submission.txt，其中的 HTML 標籤也能被正確轉換
        full_markdown = markdownify(html_content)
        
        # 在 Markdown 中再找一次
        md_start_idx = -1
        for t in targets:
            idx = full_markdown.find(t)
            if idx != -1:
                md_start_idx = idx
                break
        
        if md_start_idx != -1:
            # 截取關鍵詞後面的 50,000 個字符 (足夠包含損益表、資產負債表)
            # Gemini Context 很長，我們可以大方一點
            return full_markdown[md_start_idx : md_start_idx + 50000]
        else:
            # 實在找不到，返回中間到結尾的 50,000 字符
            mid = len(full_markdown) // 2
            return full_markdown[mid : mid + 50000]
            
    except Exception as e:
        print(f"❌ [Tool Error] {str(e)}")
        # 拋出異常，讓 Node 捕獲並轉為 error 狀態
        raise e
