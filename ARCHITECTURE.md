# AI Equity Analyst - System Architecture

## 1. 系統概述 (Overview)

本項目是一個自主式投資分析 Agent，旨在自動化生成專業的權益研究報告（Equity Research Report）。

系統採用 **LangGraph 1.0** 構建，通過定義明確的狀態機（State Machine）來協調數據獲取、數學計算、定性分析與報告撰寫。

## 2. 技術棧 (Tech Stack)

* **Orchestration:** LangGraph (StateGraph)
* **LLM Framework:** LangChain 1.1+
* **LLM Provider:** Google Vertex AI / Gemini API
* **Extraction Model:** Gemini 1.5 Flash (低成本、快速，適合結構化數據提取)
* **Reasoning Model:** Gemini 1.5 Pro (超大上下文窗口，適合完整 10-K 分析)
* **Data Sources:** SEC EDGAR (10-K), Yahoo Finance (Price), Tavily (News)

### 2.1 為什麼選擇 Gemini？

* **超長 Context Window:** Gemini 1.5 Pro 擁有 **200萬 Token** 的上下文窗口，可以將整個 10-K 年報（50K-100K tokens）直接輸入，無需複雜的 RAG 或 Chunking 邏輯
* **成本效益:** Gemini 1.5 Flash 極其便宜，適合 Node A 的數據提取任務
* **全盤分析能力:** 無需切片，可以對整份財報進行全局語義理解

## 3. 數據流架構 (Data Flow)

系統採用**混合循環圖 (Hybrid Cyclic Graph)** 設計：

1. **Node A: Data Miner**
   * 職責：從 SEC 下載財報 HTML，清洗為 Markdown，提取結構化 JSON。
   * **技術優勢：** 利用 Gemini 1.5 Flash 的長上下文窗口，可以將整個 10-K 章節（如完整的 Item 7 MD&A）直接傳遞給 LLM，無需複雜的切片邏輯。
   * 異常處理：若下載失敗，觸發錯誤標記，路由至 Human Loop。

2. **Node B: Calculator**
   * 職責：執行純 Python 數學運算 (三表配平, 估值比率, DCF)。
   * 特點：不使用 LLM，確保計算準確性。

3. **Node C: Researcher**
   * 職責：使用 Deep Research 模式搜索市場情緒、競爭格局。
   * **技術優勢：** 使用 Gemini 1.5 Flash 進行數據提取，Gemini 1.5 Pro 進行深度定性分析。

4. **Node D: Writer**
   * 職責：匯總所有結構化與非結構化數據，生成 Markdown 報告。
   * **技術優勢：** 使用 Gemini 1.5 Pro 的大上下文窗口，可以一次性整合所有分析結果生成完整報告。

## 4. 全局狀態定義 (Agent State)

所有節點共享以下 `TypedDict` 結構：

```python
class AgentState(TypedDict):
    ticker: str                         # 目標股票代碼
    sec_text_chunk: Optional[str]       # 財報原始文本 (支持人工注入)
    financial_data: Optional[Dict]      # 提取後的財務數據 (JSON)
    valuation_metrics: Optional[Dict]   # 計算後的估值指標
    qualitative_analysis: Optional[str] # 定性分析文本
    final_report: Optional[str]         # 最終報告
    error: Optional[str]                # 錯誤控制標記
```

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

採用 **"High Cohesion, Low Coupling"** 的微服務式代碼組織風格：

* **狀態管理:** `src/state.py` 定義全局狀態結構
* **圖編排:** `src/graph.py` 定義節點間的連接與路由邏輯
* **節點實現:** `src/nodes/` 目錄下每個節點為獨立包（Package），包含：
  * `node.py` - 節點主邏輯
  * `tools.py` - 節點專用工具（私有工具，僅該節點使用）
  * `__init__.py` - 暴露節點函數給圖編排層
* **共享工具:** `src/tools/` 提供跨節點共享的通用工具（如 Logging、日期處理）
* **設計優勢:** 
  * 每個節點是自包含模組（Self-contained Module）
  * 節點專用工具與節點邏輯緊密耦合，提高內聚性
  * 便於未來擴展（如新增 TechnicalAnalysis Node）

## 8. 錯誤處理策略

* 所有節點應捕獲異常並在 `AgentState.error` 中記錄錯誤信息
* 嚴重錯誤（如 API 失敗）觸發 Human-in-the-Loop 中斷
* 非致命錯誤（如數據缺失）記錄警告但繼續執行流程

## 9. 數據持久化

* SEC 財報原始文件緩存於 `data/sec_filings/` 目錄
* 中間計算結果可選擇性持久化（未來擴展）
* 最終報告以 Markdown 格式輸出

## 10. 擴展性考慮

* 支持多股票並行分析（未來 Phase）
* 支持自定義分析模板（報告格式可配置）
* 支持多種估值模型（DCF, P/E, P/B 等）

