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

1. **Node A: Data Miner** ✅ (Sprint 2 + Sprint 5 已實現)
   * 職責：從 SEC 下載財報，清洗為 Markdown，提取結構化數據。
   * **技術實現：**
     * 使用 `sec-edgar-downloader` 從 SEC EDGAR 下載最新 10-K 文件
     * **雙格式支持：** 自動識別 HTML (Primary Document) 和 TXT (Full Submission) 格式
     * 使用 `beautifulsoup4` 解析混合格式（BeautifulSoup 可處理包含 XML/SGML 標頭的內容）
     * 使用 `markdownify` 將內容轉換為 Markdown（自動忽略非 HTML 標籤如 SEC-HEADER）
     * **擴展搜索範圍：** 智能定位損益表和現金流量表（"Consolidated Statements of Operations" 和 "Consolidated Statements of Cash Flows"）
     * 截取 80,000 字符確保覆蓋多個報表
     * 使用 Gemini 的 `with_structured_output()` 直接提取為 Pydantic 對象
   * **技術優勢：** 利用 Gemini 的長上下文窗口，可以將整個財務報表章節直接傳遞給 LLM，無需複雜的切片邏輯。
   * **異常處理：** 若下載失敗或提取失敗，觸發錯誤標記，路由至 Human Loop。
   * **數據輸出：** 返回 `FinancialStatements` Pydantic 對象，包含 fiscal_year, total_revenue, net_income, operating_cash_flow, capital_expenditures, source

2. **Node B: Calculator** ✅ (Sprint 3 + Sprint 5 + Sprint 6 已實現)
   * 職責：執行純 Python 數學運算 (估值比率、盈利能力指標、DCF 模型)。
   * **技術實現：**
     * 使用 `yfinance` 獲取實時股價、市值、流通股數、PEG Ratio、Beta、無風險利率 (^TNX)、TTM P/E、TTM FCF
     * **財務數據標準化：** 從 yfinance 財務報表提取 Normalized Income（排除非經常性項目），優先使用標準化淨利進行估值計算
     * **雙軌 P/E 驗證：**
       * FY P/E: 基於財報計算 (Market Cap / FY Net Income)
       * TTM P/E: 從 Yahoo Finance 獲取實時數據 (Trailing Twelve Months)
       * 趨勢洞察：對比兩者差異，判斷獲利趨勢（改善/穩定/衰退）
     * 計算 Net Profit Margin (淨利率) = Net Income / Revenue
     * **2-Stage DCF 模型（智能動態參數）：**
       * **FCF 數據源選擇（TTM vs FY）：**
         * 優先使用 TTM FCF (從 yfinance 獲取實時數據，過去12個月滾動)
         * 如果沒有 TTM 數據，回退使用財報 FY FCF
         * 消除「舊財報 vs 新股價」的時間錯配問題
       * **增長率校準機制：**
         * 如果 TTM FCF > FY FCF (說明過去一年已有顯著增長)
         * 自動降低未來增長率預期 (降低 25%)，避免雙重計算增長
       * **智能增長率推導：**
         * 策略 A: 透過 PEG Ratio 反推市場隱含增長率 (Growth = P/E / PEG / 100)
         * 策略 B: 基於 P/E 分層規則（P/E > 50 → 25%, P/E > 25 → 15%, 其他 → 10%）
       * **動態 WACC 計算（CAPM + Hurdle Rate 混合模型）：**
         * 無風險利率 (Rf): 從 `^TNX` (10年期國債收益率) 實時獲取
         * 市場風險溢價 (ERP): 設為 5% (歷史平均水平)
         * CAPM WACC = Rf + Beta × ERP
         * **保底折現率 (Hurdle Rate):** RoundUp(Rf) + 5.5% (防止低 Beta 導致折現率過低)
         * **最終 WACC:** Max(CAPM WACC, Hurdle Rate) - 取兩者之大者
         * 這確保低 Beta 公司（如 UNH）不會因折現率過低而產生估值泡沫
       * 預測未來 5 年現金流（基於動態增長率）
       * 計算終值 (Terminal Value)
       * 折現回現值 (NPV，使用動態 WACC)
       * 計算每股內在價值和上行/下行空間
     * 簡單估值狀態判斷（基於 P/E 區間）
   * **特點：** 不使用 LLM，確保計算準確性。所有計算均為純 Python 數學運算。智能適應成長股和價值股，同時具備市場情緒感知 (PEG Growth) 和風險感知 (CAPM WACC)。
   * **數據輸出：** 返回 `ValuationMetrics` Pydantic 對象，包含 market_cap, current_price, net_profit_margin, pe_ratio, pe_ratio_ttm, pe_ratio_fy, pe_trend_insight, eps_ttm, eps_normalized, is_normalized, valuation_status, dcf_value, dcf_upside

3. **Node C: Researcher** ✅ (Sprint 4 已實現)
   * 職責：結合外部新聞與內部財報，生成定性分析。
   * **技術實現：**
     * 使用 `Tavily API` 搜索最新市場新聞與分析師觀點
     * 分析 SEC 10-K 財報中的 MD&A 章節
     * 使用 Gemini 綜合新聞、財報和財務指標，生成結構化分析
   * **技術優勢：** 結合外部市場情緒與內部管理層展望，提供全面的定性評估。
   * **數據輸出：** 返回 `QualitativeAnalysis` Pydantic 對象，包含 market_sentiment, key_growth_drivers, top_risks, management_tone, summary

4. **Node D: Writer** ✅ (Sprint 4 已實現)
   * 職責：匯總所有結構化與非結構化數據，生成專業投資研報。
   * **技術實現：**
     * 聚合財務數據、估值指標、定性分析
     * 使用 Gemini 生成結構化的 Markdown 投資報告
     * 報告包含：執行摘要、財務亮點、戰略分析、結論
   * **技術優勢：** 使用 Gemini 的大上下文窗口，可以一次性整合所有分析結果生成完整報告。
   * **數據輸出：** 返回專業的繁體中文投資研究報告（Markdown 格式）

## 4. 全局狀態定義 (Agent State)

所有節點共享以下 `TypedDict` 結構，使用 **Pydantic 強類型對象** 確保數據契約：

```python
from src.models.financial import FinancialStatements
from src.models.valuation import ValuationMetrics
from src.models.analysis import QualitativeAnalysis

class AgentState(TypedDict):
    ticker: str                         # 目標股票代碼
    
    # --- 原始數據 ---
    sec_text_chunk: Optional[str]       # 財報原始文本 (支持人工注入)
    
    # --- 結構化業務數據 (使用 Pydantic Object) ---
    financial_data: Optional[FinancialStatements]      # 提取後的財務數據 (強類型)
    valuation_metrics: Optional[ValuationMetrics]     # 計算後的估值指標 (強類型)
    qualitative_analysis: Optional[QualitativeAnalysis]  # 定性分析結果 (強類型)
    
    # 其他節點
    final_report: Optional[str]         # 最終報告 (Markdown 格式)
    
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

## 8. 模組化設計原則 (Modular Node Design)

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

## 9. 錯誤處理策略

* 所有節點應捕獲異常並在 `AgentState.error` 中記錄錯誤信息
* 嚴重錯誤（如 API 失敗）觸發 Human-in-the-Loop 中斷
* 非致命錯誤（如數據缺失）記錄警告但繼續執行流程

## 10. 數據持久化

* SEC 財報原始文件緩存於 `data/sec_filings/` 目錄
* 中間計算結果可選擇性持久化（未來擴展）
* 最終報告以 Markdown 格式輸出

## 11. 領域模型設計 (Domain Model Design)

系統採用 **Domain Model Pattern**，將數據定義與業務邏輯徹底分離：

### 10.1 Models 層結構

所有 Pydantic 數據模型位於 `src/models/` 目錄：

* `src/models/financial.py` - `FinancialStatements` 模型
  * 定義財務報表數據結構
  * 包含：fiscal_year, total_revenue, net_income, operating_cash_flow, capital_expenditures, source

* `src/models/valuation.py` - `ValuationMetrics` 模型
  * 定義估值指標數據結構
  * 包含：market_cap, current_price, net_profit_margin, pe_ratio, pe_ratio_ttm, pe_ratio_fy, pe_trend_insight, eps_ttm, eps_normalized, is_normalized, valuation_status, dcf_value, dcf_upside

* `src/models/analysis.py` - `QualitativeAnalysis` 模型
  * 定義定性分析數據結構
  * 包含：market_sentiment, key_growth_drivers, top_risks, management_tone, summary

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

## 12. 實現狀態 (Implementation Status)

### 11.1 已完成節點

* ✅ **Node A: Data Miner** (Sprint 2 + Sprint 5)
  * 真實 SEC 10-K 下載功能
  * **雙格式支持：** 自動處理 HTML 和 TXT (Full Submission) 格式
  * HTML/Markdown 轉換（支持混合格式解析）
  * **擴展數據提取：** 提取損益表和現金流量表（Revenue, Net Income, Operating Cash Flow, Capital Expenditures）
  * Gemini 結構化提取
  * 返回強類型 `FinancialStatements` 對象（包含現金流數據）

* ✅ **Node B: Calculator** (Sprint 3 + Sprint 5 + Sprint 6 + Sprint 6.5 + Sprint 7 + Sprint 7.5 + Sprint 8)
  * 使用 `yfinance` 獲取實時市場數據（股價、市值、流通股數、PEG Ratio、Beta、無風險利率 ^TNX、TTM P/E、TTM FCF）
  * 純 Python 數學計算（P/E Ratio, Net Profit Margin）
  * **財務數據標準化：** 從 yfinance 財務報表提取 Normalized Income（排除非經常性項目），優先使用標準化淨利進行估值計算
  * **雙軌 P/E 驗證：** 對比 FY P/E 和 TTM P/E，判斷獲利趨勢（改善/穩定/衰退）
  * **2-Stage DCF 模型（智能動態參數 + TTM 實時化）：**
    * **FCF 數據源選擇：** 優先使用 TTM FCF (實時)，回退到 FY FCF (財報)，消除時間錯配
    * **增長率校準：** 如果 TTM FCF > FY FCF，自動降低未來增長率預期，避免雙重計算
    * **智能增長率：** 透過 PEG Ratio 反推市場隱含增長率，或基於 P/E 分層規則
    * **動態 WACC (Hybrid 模型)：** 
      * CAPM 計算：Rf + Beta × ERP
      * 保底折現率：RoundUp(Rf) + 5.5% (Hurdle Rate)
      * 最終 WACC：Max(CAPM, Hurdle Rate) - 防止低 Beta 公司估值泡沫
    * 預測未來現金流、計算終值、折現回現值
  * 計算每股內在價值和上行/下行空間
  * 估值狀態判斷（基於 P/E 區間）
  * 返回強類型 `ValuationMetrics` 對象（包含 DCF 結果、趨勢洞察和標準化利潤指標）

* ✅ **Node C: Researcher** (Sprint 4)
  * 使用 `Tavily API` 搜索市場新聞與分析師觀點
  * 分析 SEC 10-K 財報 MD&A 章節
  * Gemini 綜合分析生成結構化定性評估
  * 返回強類型 `QualitativeAnalysis` 對象

* ✅ **Node D: Writer** (Sprint 4)
  * 聚合所有分析結果（財務、估值、定性）
  * 使用 Gemini 生成專業投資研報
  * 結構化 Markdown 格式（執行摘要、財務亮點、戰略分析、結論）
  * 繁體中文輸出

### 11.2 待實現節點

* ⏳ **Human Node** - 完整的人機交互流程（目前為基礎實現）

## 13. 擴展性考慮

* 支持多股票並行分析（未來 Phase）
* 支持自定義分析模板（報告格式可配置）
* 支持多種估值模型（DCF, P/E, P/B 等）- 已實現 P/E、Margins 和 2-Stage DCF
* 新增領域模型：在 `src/models/` 中添加新的 Pydantic 模型
* 新增節點：在 `src/nodes/` 中創建新的節點包
* 優化數據提取：支持更多財務報表類型（10-Q, 8-K 等）
* **文件格式兼容性：** 已支持 HTML 和 TXT (Full Submission) 格式，適應 `sec-edgar-downloader` 新版本行為
* **DCF 模型：** 已實現 2-Stage DCF，支持預測未來現金流和計算內在價值，使 Agent 具備「預測未來」的能力
* **智能增長率：** 透過 PEG Ratio 反推市場隱含增長率，或基於 P/E 分層規則，使 DCF 模型能夠智能適應成長股和價值股
* **動態 WACC (Hybrid 模型)：** 使用 CAPM 模型實時計算折現率，從 `^TNX` 獲取無風險利率，結合 Beta 和市場風險溢價。引入 Hurdle Rate 保底機制（RoundUp(Rf) + 5.5%），確保低 Beta 公司不會因折現率過低而產生估值泡沫，使估值更符合實戰派標準
* **雙軌 P/E 驗證：** 對比財報 P/E 和實時 TTM P/E，通過差異分析判斷公司獲利趨勢，解決「舊財報 vs 新股價」的時間錯配問題
* **財務數據標準化：** 從 yfinance 提取 Normalized Income（排除非經常性項目），優先使用標準化淨利進行估值，避免一次性損益導致 P/E 和 DCF 失真
* **FCF 實時化：** 優先使用 TTM FCF (過去12個月滾動) 作為 DCF 起點，消除「舊財報 vs 新股價」的時間錯配，使估值與彭博終端 (Bloomberg Terminal) 同級別的數據新鮮度

