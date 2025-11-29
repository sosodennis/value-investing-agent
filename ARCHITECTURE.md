# AI Equity Analyst - System Architecture

## 1. 系統概述 (Overview)

本項目是一個自主式投資分析 Agent，旨在自動化生成專業的權益研究報告（Equity Research Report）。

系統採用 **LangGraph 1.0** 構建，通過定義明確的狀態機（State Machine）來協調數據獲取、數學計算、定性分析與報告撰寫。

## 2. 技術棧 (Tech Stack)

* **Orchestration:** LangGraph (StateGraph)
* **LLM Framework:** LangChain 1.1+
* **LLM Provider:** Google Vertex AI / Gemini API
* **Extraction Model:** Gemini (低成本、快速，適合結構化數據提取)
* **Reasoning Model:** Gemini (超大上下文窗口，適合完整 10-K 分析)
* **Data Sources:** SEC EDGAR (10-K), Yahoo Finance (Price), Tavily (News)

### 2.1 為什麼選擇 Gemini？

* **超長 Context Window:** Gemini 擁有 **超大 Token** 的上下文窗口，可以將整個 10-K 年報（50K-100K tokens）直接輸入，無需複雜的 RAG 或 Chunking 邏輯
* **成本效益:** Gemini 極其便宜，適合數據提取任務
* **全盤分析能力:** 無需切片，可以對整份財報進行全局語義理解

## 3. 數據流架構 (Data Flow)

系統採用**混合循環圖 (Hybrid Cyclic Graph)** 設計：

1. **Node A: Data Miner** ✅ (Sprint 2 已實現)
   * 職責：從 SEC 下載財報，清洗為 Markdown，提取結構化數據。
   * **技術實現：**
     * 使用 `sec-edgar-downloader` 從 SEC EDGAR 下載最新 10-K 文件
     * **雙格式支持：** 自動識別 HTML (Primary Document) 和 TXT (Full Submission) 格式
     * 使用 `beautifulsoup4` 解析混合格式（BeautifulSoup 可處理包含 XML/SGML 標頭的內容）
     * 使用 `markdownify` 將內容轉換為 Markdown（自動忽略非 HTML 標籤如 SEC-HEADER）
     * 智能定位財務報表章節（如 "Consolidated Statements of Operations"）
     * 使用 Gemini 的 `with_structured_output()` 直接提取為 Pydantic 對象
   * **技術優勢：** 利用 Gemini 的長上下文窗口，可以將整個財務報表章節直接傳遞給 LLM，無需複雜的切片邏輯。
   * **異常處理：** 若下載失敗或提取失敗，觸發錯誤標記，路由至 Human Loop。
   * **數據輸出：** 返回 `FinancialStatements` Pydantic 對象，包含 fiscal_year, total_revenue, net_income, source

2. **Node B: Calculator** ✅ (Sprint 3 已實現)
   * 職責：執行純 Python 數學運算 (估值比率、盈利能力指標)。
   * **技術實現：**
     * 使用 `yfinance` 獲取實時股價和市值數據
     * 計算 P/E Ratio (本益比) = Market Cap / Net Income
     * 計算 Net Profit Margin (淨利率) = Net Income / Revenue
     * 簡單估值狀態判斷（基於 P/E 區間）
   * **特點：** 不使用 LLM，確保計算準確性。所有計算均為純 Python 數學運算。
   * **數據輸出：** 返回 `ValuationMetrics` Pydantic 對象，包含 market_cap, current_price, net_profit_margin, pe_ratio, valuation_status

3. **Node C: Researcher**
   * 職責：使用 Deep Research 模式搜索市場情緒、競爭格局。
   * **技術優勢：** 使用 Gemini 進行數據提取和深度定性分析。

4. **Node D: Writer**
   * 職責：匯總所有結構化與非結構化數據，生成 Markdown 報告。
   * **技術優勢：** 使用 Gemini 的大上下文窗口，可以一次性整合所有分析結果生成完整報告。

## 4. 全局狀態定義 (Agent State)

所有節點共享以下 `TypedDict` 結構，使用 **Pydantic 強類型對象** 確保數據契約：

```python
from src.models.financial import FinancialStatements
from src.models.valuation import ValuationMetrics

class AgentState(TypedDict):
    ticker: str                         # 目標股票代碼
    
    # --- 原始數據 ---
    sec_text_chunk: Optional[str]       # 財報原始文本 (支持人工注入)
    
    # --- 結構化業務數據 (使用 Pydantic Object) ---
    financial_data: Optional[FinancialStatements]      # 提取後的財務數據 (強類型)
    valuation_metrics: Optional[ValuationMetrics]     # 計算後的估值指標 (強類型)
    
    # 其他節點暫時用簡單類型
    qualitative_analysis: Optional[str] # 定性分析文本
    final_report: Optional[str]         # 最終報告
    
    # --- 控制信號 ---
    # 簡單字符串，與業務數據分離
    error: Optional[str]                # 錯誤控制標記
```

**設計優勢：**
* **類型安全：** 使用 Pydantic 模型確保數據結構正確性
* **錯誤分離：** `error` 字段獨立運作，不污染業務數據對象
* **IDE 支持：** 強類型提供完整的自動補全和類型檢查

## 5. 人機協作 (Human-in-the-Loop)

* **斷點 (Interrupts):** 系統在關鍵決策點（如數據獲取失敗時）會暫停。
* **數據注入 (Data Injection):** 允許用戶通過 `update_state` 機制上傳本地財報或修正分析假設。

## 6. 圖結構設計 (Graph Structure)

```
[START] 
  ↓
[Data Miner] → (成功) → [Calculator] → [Researcher] → [Writer] → [END]
  ↓ (失敗)
[Human Loop] → (修正) → [Data Miner]
```

## 7. 模組化設計原則 (Modular Node Design)

採用 **"High Cohesion, Low Coupling"** 的微服務式代碼組織風格，遵循 **Domain Model Pattern (領域模型模式)**：

### 7.1 分層架構

系統採用清晰的分層架構，實現單向依賴流動：

```
Models (獨立層，無依賴)
  ↓
State (依賴 Models)
  ↓
Nodes (依賴 State 和 Models)
```

### 7.2 目錄結構

* **領域模型層 (Domain Models):** `src/models/` 
  * 包含所有 Pydantic 數據模型（如 `FinancialStatements`, `ValuationMetrics`）
  * **完全獨立**，不依賴任何業務邏輯
  * 確保數據定義與業務邏輯分離，消除循環依賴

* **狀態管理:** `src/state.py` 
  * 定義全局狀態結構（`AgentState` TypedDict）
  * 引用 Models 層的 Pydantic 對象

* **圖編排:** `src/graph.py` 
  * 定義節點間的連接與路由邏輯
  * 實現條件路由和 Human-in-the-Loop 中斷

* **節點實現:** `src/nodes/` 
  * 每個節點為獨立包（Package），包含：
    * `node.py` - 節點主邏輯
    * `tools.py` - 節點專用工具（私有工具，僅該節點使用）
    * `__init__.py` - 暴露節點函數給圖編排層

* **共享工具:** `src/tools/` 
  * 提供跨節點共享的通用工具（如 Logging、日期處理）

### 7.3 設計優勢

* **無循環依賴：** Models 層獨立，確保清晰的依賴關係
* **高內聚低耦合：** 每個節點是自包含模組（Self-contained Module）
* **類型安全：** 使用 Pydantic 確保數據契約
* **易於擴展：** 新增模型只需在 `src/models/` 中添加，新增節點只需在 `src/nodes/` 中創建
* **領域驅動：** 符合 DDD (Domain-Driven Design) 原則

## 8. 錯誤處理策略

* 所有節點應捕獲異常並在 `AgentState.error` 中記錄錯誤信息
* 嚴重錯誤（如 API 失敗）觸發 Human-in-the-Loop 中斷
* 非致命錯誤（如數據缺失）記錄警告但繼續執行流程

## 9. 數據持久化

* SEC 財報原始文件緩存於 `data/sec_filings/` 目錄
* 中間計算結果可選擇性持久化（未來擴展）
* 最終報告以 Markdown 格式輸出

## 10. 領域模型設計 (Domain Model Design)

系統採用 **Domain Model Pattern**，將數據定義與業務邏輯徹底分離：

### 10.1 Models 層結構

所有 Pydantic 數據模型位於 `src/models/` 目錄：

* `src/models/financial.py` - `FinancialStatements` 模型
  * 定義財務報表數據結構
  * 包含：fiscal_year, total_revenue, net_income, source

* `src/models/valuation.py` - `ValuationMetrics` 模型
  * 定義估值指標數據結構
  * 包含：market_cap, current_price, net_profit_margin, pe_ratio, valuation_status

### 10.2 設計原則

* **單向依賴：** Models → State → Nodes，無循環依賴
* **數據契約：** 使用 Pydantic 確保類型安全和數據驗證
* **獨立性：** Models 層不依賴任何業務邏輯，可獨立測試和重用
* **可擴展性：** 新增領域模型只需在 `src/models/` 中添加新文件

### 10.3 使用示例

```python
# 在節點中使用強類型對象
from src.models.financial import FinancialStatements
from src.state import AgentState

def data_miner_node(state: AgentState) -> dict:
    # 返回強類型對象，而非字典
    return {
        "financial_data": FinancialStatements(
            fiscal_year="2024",
            total_revenue=10000.0,
            net_income=2000.0,
            source="Auto Download"
        )
    }

# 在其他節點中直接訪問屬性（類型安全）
def calculator_node(state: AgentState) -> dict:
    financial_data = state.get("financial_data")
    if financial_data:
        # IDE 提供完整的自動補全
        revenue = financial_data.total_revenue
        income = financial_data.net_income
```

## 11. 實現狀態 (Implementation Status)

### 11.1 已完成節點

* ✅ **Node A: Data Miner** (Sprint 2)
  * 真實 SEC 10-K 下載功能
  * **雙格式支持：** 自動處理 HTML 和 TXT (Full Submission) 格式
  * HTML/Markdown 轉換（支持混合格式解析）
  * Gemini 結構化提取
  * 返回強類型 `FinancialStatements` 對象

* ✅ **Node B: Calculator** (Sprint 3)
  * 使用 `yfinance` 獲取實時市場數據（股價、市值）
  * 純 Python 數學計算（P/E Ratio, Net Profit Margin）
  * 估值狀態判斷（基於 P/E 區間）
  * 返回強類型 `ValuationMetrics` 對象

### 11.2 待實現節點

* ⏳ **Node C: Researcher** - 深度市場研究（Tavily API + Gemini）
* ⏳ **Node D: Writer** - 報告生成（Gemini）
* ⏳ **Human Node** - 完整的人機交互流程

## 12. 擴展性考慮

* 支持多股票並行分析（未來 Phase）
* 支持自定義分析模板（報告格式可配置）
* 支持多種估值模型（DCF, P/E, P/B 等）
* 新增領域模型：在 `src/models/` 中添加新的 Pydantic 模型
* 新增節點：在 `src/nodes/` 中創建新的節點包
* 優化數據提取：支持更多財務報表類型（10-Q, 8-K 等）
* **文件格式兼容性：** 已支持 HTML 和 TXT (Full Submission) 格式，適應 `sec-edgar-downloader` 新版本行為

