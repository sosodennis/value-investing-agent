# AI Equity Analyst - System Architecture (v2.0: Industry-Adaptive)

## 1. 系統概述 (Overview)

本項目是一個**產業自適應 (Industry-Adaptive)** 的智能投資分析 Agent。與傳統「一刀切」的自動化工具不同，本系統採用**上下文感知架構**，能夠識別目標公司的行業屬性（如銀行、房地產、高成長科技），並動態調度最適合的估值模型（如 DDM, NAV, Rule of 40）。

系統基於 **LangGraph 1.0** 構建，實現了從「戰略定位」到「執行計算」再到「深度洞察」的完整閉環。

## 2. 核心設計模式 (Design Patterns)

* **策略模式 (Strategy Pattern):** 用於 `Calculator` 節點，根據行業動態加載不同的算法策略。

* **雙鑽石模型 (Double Diamond):** 流程分為「發散（多策略選擇）」與「收斂（異常檢測與總結）」。

* **領域驅動設計 (DDD):** 數據結構與業務邏輯嚴格分離，所有業務數據均由 Pydantic 強類型定義。

## 3. 數據流架構 (Data Flow Pipeline)

系統由六大核心節點組成，形成一個具備自我修正能力的有向循環圖：

### Phase 1: 戰略定位 (Context)

1.  **Node A: Profiler (分析師)**

    * **職責:** 獲取公司基礎信息，識別行業 (Sector) 與細分領域 (Industry)。

    * **決策:** 選擇估值策略 (e.g., `Strategy="Bank_DDM"` vs `Strategy="General_DCF"`)。

    * **工具:** yfinance info, Sector Classifier。

### Phase 2: 執行與計算 (Execution)

2.  **Node B: Adaptive Miner (智能礦工)**

    * **職責:** 根據策略需求，動態提取特定財務數據。

    * **行為差異:**

        * *General:* 提取 Revenue, Net Income, FCF。

        * *REITs:* 提取 FFO (Funds From Operations), NOI。

        * *Banks:* 提取 Tier 1 Capital, Book Value。

    * **技術:** SEC EDGAR Downloader (HTML/TXT 雙模), Gemini 1.5 Flash (長文本提取)。

3.  **Node C: Strategy Calculator (計算引擎)**

    * **職責:** 執行選定的估值模型。

    * **已支持策略:**

        * **General:** 2-Stage DCF (含智能增長率 & 動態 WACC)。

        * *(待實現)* **Financials:** DDM (股利折現模型)。

        * *(待實現)* **REITs:** NAV (淨資產價值) & P/FFO。

        * *(待實現)* **SaaS:** Rule of 40 & EV/Sales。

    * **特性:** 純 Python 數學運算，嚴格遵守絕對數值標準。

### Phase 3: 驗證與深挖 (Insight & Validation)

4.  **Node D: Insight Reviewer (異常審查)**

    * **職責:** 對計算結果進行邏輯質檢 (Sanity Check)。

    * **檢測邏輯:**

        * 估值 Upside 是否過於極端 (>100% 或 <-50%)?

        * 標準化淨利 (Normalized) 與 GAAP 淨利差異是否過大 (>20%)?

    * **輸出:** 若發現異常，生成 `investigation_tasks` 隊列。

5.  **Node E: Deep Researcher (深度偵探)**

    * **職責:** 執行定向深度研究。

    * **觸發:** 僅在 `investigation_tasks` 非空時啟動，或執行標準市場情緒分析。

    * **任務:** 解釋 Node D 發現的異常（如：「為什麼 UNH 有一次性虧損？」）。

    * **工具:** Tavily Search, Gemini 1.5 Pro (推理)。

6.  **Node F: Writer (主編)**

    * **職責:** 匯總所有信息，生成結構化 Markdown 報告。

    * **特性:** 若存在數據異常，強制生成「數據差異分析」章節。

## 4. 全局狀態定義 (Agent State)

```python
class AgentState(TypedDict):
    ticker: str
    
    # [New] 戰略上下文
    sector: str                 # 行業 (e.g., "Real Estate")
    industry: str               # 細分 (e.g., "REIT - Retail")
    valuation_strategy: str     # 策略代碼 (e.g., "REIT_NAV")
    
    # 數據層 (Pydantic Models)
    # 注意：根據策略不同，financial_data 可能會加載不同的子類模型
    financial_data: Optional[Union[FinancialStatements, BankFinancials, ReitFinancials]]
    valuation_metrics: Optional[ValuationMetrics]
    qualitative_analysis: Optional[QualitativeAnalysis]
    
    # 協作層
    investigation_tasks: Optional[List[str]]  # 跨節點任務隊列
    
    # 輸出層
    final_report: Optional[str]
    error: Optional[str]
```

## 5. 數據標準與契約 (Data Contracts)

為防止計算誤差，全系統嚴格遵守以下標準：

1.  **絕對數值 (Absolute Values):**

      * 所有計算函數 (`calculate_dcf` 等) 的輸入必須是**絕對值** (e.g., `10,000,000,000`)。

      * 嚴禁在計算函數內部進行單位換算 (如 `* 10^6`)。

      * Miner 負責在提取後立即將 Millions 轉為 Absolute。

2.  **數據時效 (Time Consistency):**

      * **估值起點：** 優先使用 **TTM (Trailing Twelve Months)** 數據。

      * **回退機制：** 僅在 TTM 不可用時使用 FY (上一財年) 數據，並在報告中標註滯後風險。

3.  **標準化利潤 (Normalization):**

      * 優先使用 `Normalized Income` (Excl. NRI) 替代 `GAAP Net Income` 進行 P/E 和 FCF 起點計算。

## 6. 目錄結構規劃 (Directory Structure)

```text
src/
├── models/               # [Layer 1] 領域數據模型
│   ├── financial.py      # 通用財務數據
│   ├── industry/         # [New] 行業特有數據 (bank.py, reit.py)
│   ├── valuation.py      # 估值結果模型
│   └── analysis.py       # 定性分析模型
├── state.py              # [Layer 2] 全局狀態
├── tools/                # [Layer 3] 通用工具
├── nodes/                # [Layer 4] 業務節點
│   ├── profiler/         # [New] 行業識別
│   ├── data_miner/       # 數據獲取 (含策略適配)
│   ├── calculator/       # 計算引擎
│   │   ├── node.py       # 調度器
│   │   ├── strategies/   # [New] 估值策略庫 (general.py, bank.py...)
│   │   └── tools.py      # 計算工具
│   ├── reviewer/         # [New] 異常檢測
│   ├── researcher/       # 深度研究
│   └── writer/           # 報告生成
└── graph.py              # [Layer 5]圖編排
```

## 7. 圖結構設計 (Graph Structure)

```
[START] 
  ↓
[Profiler] → (識別行業) → [Adaptive Miner] → [Strategy Calculator] → [Insight Reviewer]
  ↓                                                                    ↓ (發現異常)
[Human Loop] ← (錯誤) ← [Error Handler]                              [Deep Researcher]
                                                                      ↓
                                                                    [Writer] → [END]
```

**跨節點洞察傳遞流程：**
1. Profiler 識別行業，選擇估值策略
2. Adaptive Miner 根據策略提取相應財務數據
3. Strategy Calculator 執行選定的估值模型
4. Insight Reviewer 檢測異常，生成 `investigation_tasks`
5. Deep Researcher 接收任務，進行定向搜索
6. Writer 生成報告，包含異常解釋（如有）

## 8. 實現狀態 (Implementation Status)

### 8.1 已實現節點

* ✅ **Node B: Adaptive Miner** (原 Data Miner, Sprint 2 + Sprint 5)
  * SEC EDGAR Downloader (HTML/TXT 雙模支持)
  * Gemini 結構化提取財務數據
  * 支持提取 Revenue, Net Income, Operating Cash Flow, Capital Expenditures

* ✅ **Node C: Strategy Calculator** (原 Calculator, Sprint 3 + Sprint 5-8)
  * **General Strategy (2-Stage DCF):**
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
    * 返回強類型 `ValuationMetrics` 對象

* ✅ **Node E: Deep Researcher** (原 Researcher, Sprint 4 + Sprint 9)
  * 使用 `Tavily API` 搜索市場新聞與分析師觀點
  * **跨節點洞察傳遞：** 優先搜索 `investigation_tasks` 中的定向查詢
  * 分析 SEC 10-K 財報 MD&A 章節
  * Gemini 綜合分析生成結構化定性評估
  * 針對上游節點發現的異常進行定向深度研究
  * 返回強類型 `QualitativeAnalysis` 對象

* ✅ **Node F: Writer** (Sprint 4 + Sprint 9)
  * 聚合所有分析結果（財務、估值、定性、調查任務）
  * 使用 Gemini 生成專業投資研報
  * 結構化 Markdown 格式（執行摘要、財務亮點、**數據差異分析**、戰略分析、結論）
  * **強制異常解釋：** 如果存在數據異常，在報告中包含「數據差異分析」章節
  * 繁體中文輸出

### 8.2 待實現節點

* ⏳ **Node A: Profiler** (Sprint 10+)
  * 使用 yfinance 獲取公司基礎信息
  * 識別行業 (Sector) 與細分領域 (Industry)
  * 選擇估值策略 (Strategy Selection)
  * 返回 `sector`, `industry`, `valuation_strategy`

* ⏳ **Node D: Insight Reviewer** (Sprint 10+)
  * 對計算結果進行邏輯質檢
  * 檢測極端估值 Upside (>100% 或 <-50%)
  * 檢測標準化淨利與 GAAP 淨利差異 (>20%)
  * 生成 `investigation_tasks` 隊列

* ⏳ **Node C: Strategy Calculator - 擴展策略** (Sprint 10+)
  * **Financials Strategy (DDM):** 股利折現模型
  * **REITs Strategy (NAV):** 淨資產價值 & P/FFO
  * **SaaS Strategy (Rule of 40):** Rule of 40 & EV/Sales

* ⏳ **Node B: Adaptive Miner - 行業適配** (Sprint 10+)
  * REITs: 提取 FFO, NOI
  * Banks: 提取 Tier 1 Capital, Book Value

### 8.3 已實現功能特性

* **文件格式兼容性：** 已支持 HTML 和 TXT (Full Submission) 格式，適應 `sec-edgar-downloader` 新版本行為
* **DCF 模型：** 已實現 2-Stage DCF，支持預測未來現金流和計算內在價值，使 Agent 具備「預測未來」的能力
* **智能增長率：** 透過 PEG Ratio 反推市場隱含增長率，或基於 P/E 分層規則，使 DCF 模型能夠智能適應成長股和價值股
* **動態 WACC (Hybrid 模型)：** 使用 CAPM 模型實時計算折現率，從 `^TNX` 獲取無風險利率，結合 Beta 和市場風險溢價。引入 Hurdle Rate 保底機制（RoundUp(Rf) + 5.5%），確保低 Beta 公司不會因折現率過低而產生估值泡沫，使估值更符合實戰派標準
* **雙軌 P/E 驗證：** 對比財報 P/E 和實時 TTM P/E，通過差異分析判斷公司獲利趨勢，解決「舊財報 vs 新股價」的時間錯配問題
* **財務數據標準化：** 從 yfinance 提取 Normalized Income（排除非經常性項目），優先使用標準化淨利進行估值，避免一次性損益導致 P/E 和 DCF 失真
* **FCF 實時化：** 優先使用 TTM FCF (過去12個月滾動) 作為 DCF 起點，消除「舊財報 vs 新股價」的時間錯配，使估值與彭博終端 (Bloomberg Terminal) 同級別的數據新鮮度
* **跨節點協作：** 實現調查任務隊列機制，當 Calculator 發現數據異常時，自動生成調查任務傳遞給 Researcher 進行定向搜索，打破信息孤島，實現「有靈魂」的 AI 分析師
* **絕對數值標準：** 全系統嚴格遵守絕對數值標準，所有計算函數只處理絕對值，單位轉換僅在輸入/輸出邊界進行，徹底解決單位錯亂問題

## 9. 擴展性考慮 (Extensibility)

* 支持多股票並行分析（未來 Phase）
* 支持自定義分析模板（報告格式可配置）
* 支持多種估值模型（DCF, DDM, NAV, Rule of 40 等）- 已實現 P/E、Margins 和 2-Stage DCF
* 新增領域模型：在 `src/models/` 中添加新的 Pydantic 模型
* 新增節點：在 `src/nodes/` 中創建新的節點包
* 新增策略：在 `src/nodes/calculator/strategies/` 中添加新的估值策略
* 優化數據提取：支持更多財務報表類型（10-Q, 8-K 等）
* 行業適配：擴展支持更多行業（如能源、消費品、醫療等）

## 10. 技術棧 (Technology Stack)

* **框架:** LangGraph 1.0 (工作流編排)
* **LLM:** Google Gemini (1.5 Flash/Pro, 2.5 Flash Lite)
* **數據獲取:**
  * SEC EDGAR: `sec-edgar-downloader`
  * 市場數據: `yfinance`
  * 新聞搜索: `Tavily API`
* **數據處理:**
  * HTML 解析: `BeautifulSoup4`
  * Markdown 轉換: `markdownify`
* **數據驗證:** Pydantic (強類型數據契約)
* **語言:** Python 3.10+

## 11. 人機協作 (Human-in-the-Loop)

* **斷點 (Interrupts):** 系統在關鍵決策點（如數據獲取失敗時）會暫停。
* **數據注入 (Data Injection):** 允許用戶通過 `update_state` 機制上傳本地財報或修正分析假設。
* **策略覆蓋 (Strategy Override):** 用戶可以手動指定估值策略，覆蓋 Profiler 的自動選擇。
