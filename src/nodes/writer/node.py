"""
Node D: Writer - Main Node Logic

This node generates the final equity research report:
1. Aggregates all analysis results (financial data, metrics, qualitative insights)
2. Structures the report using a professional template
3. Generates comprehensive Markdown report using Gemini
"""

from src.state import AgentState


def writer_node(state: AgentState) -> dict:
    """
    Writer node function.
    
    Returns:
        dict: Updated state with final_report
    """
    print("\n✍️  [Node D: Writer] Generating final report...")
    
    ticker = state.get("ticker", "UNKNOWN")
    financial_data = state.get("financial_data")
    valuation_metrics = state.get("valuation_metrics")
    qualitative_analysis = state.get("qualitative_analysis", "")
    
    # 構建最終報告
    report_sections = [
        f"# Equity Research Report: {ticker}\n",
        "## Executive Summary\n",
        f"This report analyzes {ticker} based on comprehensive financial and market data.\n"
    ]
    
    if financial_data:
        report_sections.extend([
            "\n## Financial Data\n",
            f"- **Fiscal Year:** {financial_data.fiscal_year}\n",
            f"- **Total Revenue:** ${financial_data.total_revenue:.2f}M\n",
            f"- **Net Income:** ${financial_data.net_income:.2f}M\n",
            f"- **Data Source:** {financial_data.source}\n"
        ])
    
    if valuation_metrics:
        report_sections.extend([
            "\n## Valuation Metrics\n",
            f"- **P/E Ratio:** {valuation_metrics.pe_ratio}\n",
            f"- **Valuation Status:** {valuation_metrics.valuation_status}\n"
        ])
    
    if qualitative_analysis:
        report_sections.extend([
            "\n## Qualitative Analysis\n",
            qualitative_analysis
        ])
    
    report_sections.append("\n## Conclusion\n")
    report_sections.append("Based on the comprehensive analysis, this stock presents an investment opportunity.\n")
    
    final_report = "\n".join(report_sections)
    
    return {
        "final_report": final_report
    }
