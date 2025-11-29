# AI Equity Analyst - Value Investing Agent

一個基於 LangChain 1.1+ 和 LangGraph 1.0+ 的自主式投資分析 Agent，旨在自動化生成專業的權益研究報告（Equity Research Report）。

## 項目狀態

**當前階段：** Phase 0 - 基礎建設與架構定義 ✅

## 快速開始

### 1. 環境設置

```bash
# 創建虛擬環境（推薦）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt
```

### 2. 環境變量配置

創建 `.env` 文件（已包含在 `.gitignore` 中）：

```ini
# Google Gemini API
GOOGLE_API_KEY=AIzaSy......

# Web Search Tool
TAVILY_API_KEY=tvly-......

# SEC Identity (Required by US Gov)
# 格式: Name <email@address.com>
SEC_API_USER_AGENT=MyAIAnalysis <my.email@example.com>
```

### 3. 項目結構（模組化設計）

```
ai_equity_analyst/
├── .env                    # 環境變量文件 (API Keys)
├── .gitignore              # Git 忽略配置
├── requirements.txt        # 項目依賴列表
├── README.md               # 項目說明
├── ARCHITECTURE.md         # 項目架構文檔
├── main.py                 # 應用入口
└── src/
    ├── __init__.py
    ├── state.py            # 全局狀態定義 (TypedDict)
    ├── graph.py            # LangGraph 路由與編排
    ├── tools/              # [Shared] 共享工具庫
    │   ├── __init__.py
    │   └── common.py       # 通用工具（Logging, Date helpers）
    └── nodes/              # 智能體節點（模組化設計）
        ├── __init__.py
        ├── data_miner/     # Node A: 數據礦工
        │   ├── __init__.py # 暴露 node function
        │   ├── node.py     # 節點主邏輯
        │   └── tools.py    # [Private] SEC 下載與清洗工具
        ├── calculator/     # Node B: 財務計算
        │   ├── __init__.py
        │   ├── node.py
        │   └── tools.py    # [Private] DCF, Ratio 計算函數
        ├── researcher/     # Node C: 深度研究
        │   ├── __init__.py
        │   └── node.py
        ├── writer/         # Node D: 報告撰寫
        │   ├── __init__.py
        │   └── node.py
        └── human_node/     # Human Loop
            ├── __init__.py
            └── node.py
└── data/                   # 本地數據存儲
    └── sec_filings/        # 下載的財報緩存目錄
```

## 技術棧

* **Orchestration:** LangGraph (StateGraph)
* **LLM Framework:** LangChain 1.1+
* **LLM Provider:** Google Vertex AI / Gemini API
* **Extraction Model:** Gemini 1.5 Flash (低成本、快速，適合結構化數據提取)
* **Reasoning Model:** Gemini 1.5 Pro (超大上下文窗口 200萬 Token，適合完整 10-K 分析)
* **Data Sources:** SEC EDGAR (10-K), Yahoo Finance (Price), Tavily (News)

### 為什麼選擇 Gemini？

* **超長 Context Window:** 可以將整個 10-K 年報直接輸入，無需複雜的 RAG 或 Chunking
* **成本效益:** Gemini 1.5 Flash 極其便宜，適合數據提取任務
* **全盤分析能力:** 無需切片，可以對整份財報進行全局語義理解

## 開發路線圖

- [x] **Phase 0:** 基礎建設與架構定義
- [ ] **Phase 1:** 狀態定義與 Node A (Data Miner) 實現
- [ ] **Phase 2:** Node B (Calculator) 與 Node C (Researcher) 實現
- [ ] **Phase 3:** Node D (Writer) 與 Human-in-the-Loop 實現
- [ ] **Phase 4:** 測試與優化

## 詳細文檔

請參閱 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解系統架構設計詳情。

## 許可證

請參閱 [LICENSE](./LICENSE) 文件。
